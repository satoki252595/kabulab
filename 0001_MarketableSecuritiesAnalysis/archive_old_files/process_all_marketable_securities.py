import os
import zipfile
import pandas as pd
import re
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')

class FullMarketableSecuritiesExtractor:
    def __init__(self, xbrl_folder_path):
        self.xbrl_folder_path = xbrl_folder_path
        self.results = []
        self.processed_folders = 0
        self.total_folders = 0
        
    def extract_company_info_from_xbrl(self, xbrl_content):
        """XBRLファイルから提出会社情報を抽出"""
        soup = BeautifulSoup(xbrl_content, 'lxml-xml')
        
        # 提出会社のEDINETコード
        edinet_code = None
        edinet_patterns = [
            r'EDINETCode',
            r'CompanyCode',
            r'FilerCode',
            r'SubmitterCode'
        ]
        
        for pattern in edinet_patterns:
            elements = soup.find_all('ix:nonNumeric', {'name': re.compile(pattern)})
            if elements:
                edinet_code = elements[0].get_text(strip=True)
                break
        
        # 提出会社名
        company_name = None
        company_patterns = [
            r'CompanyName',
            r'FilerName',
            r'SubmitterName',
            r'EntityName'
        ]
        
        for pattern in company_patterns:
            elements = soup.find_all('ix:nonNumeric', {'name': re.compile(pattern)})
            if elements:
                company_name = elements[0].get_text(strip=True)
                break
        
        # 証券コード
        stock_code = None
        stock_patterns = [
            r'SecurityCode',
            r'StockCode',
            r'ListingCode'
        ]
        
        for pattern in stock_patterns:
            elements = soup.find_all('ix:nonNumeric', {'name': re.compile(pattern)})
            if elements:
                stock_code = elements[0].get_text(strip=True)
                break
        
        # 期間終了日
        filing_date = None
        date_patterns = [
            r'CurrentPeriodEndDate',
            r'PeriodEndDate',
            r'FiscalPeriodEndDate'
        ]
        
        for pattern in date_patterns:
            elements = soup.find_all('ix:nonNumeric', {'name': re.compile(pattern)})
            if elements:
                filing_date = elements[0].get_text(strip=True)
                break
        
        return {
            'filing_company_code': edinet_code,
            'filing_company_name': company_name,
            'filing_stock_code': stock_code,
            'filing_date': filing_date
        }

    def extract_marketable_securities_data(self, xbrl_content):
        """XBRLファイルから特定投資株式情報を抽出"""
        soup = BeautifulSoup(xbrl_content, 'lxml-xml')
        securities_data = []
        
        # 特定投資株式名の検索パターン
        name_patterns = [
            r'NameOfSecuritiesDetailsOfSpecifiedInvestment',
            r'NameOfIssuerDetailsOfSpecifiedInvestment',
            r'NameOfSecurities.*SpecifiedInvestment',
            r'NameOfIssuer.*SpecifiedInvestment',
            r'NameOfSecuritiesDetailsOfShareholding',
            r'NameOfSecuritiesDetailsOfCrossShareholding'
        ]
        
        name_elements = []
        for pattern in name_patterns:
            elements = soup.find_all('ix:nonNumeric', {'name': re.compile(pattern)})
            name_elements.extend(elements)
        
        # 重複を除去
        unique_contexts = {}
        for elem in name_elements:
            context = elem.get('contextRef', '')
            if context not in unique_contexts:
                unique_contexts[context] = elem
        
        name_elements = list(unique_contexts.values())
        
        # 株式数の検索パターン
        shares_patterns = [
            r'NumberOfSharesHeldDetailsOfSpecifiedInvestment',
            r'NumberOfSharesHeld.*SpecifiedInvestment',
            r'NumberOfShares.*SpecifiedInvestment',
            r'NumberOfSharesHeldDetailsOfShareholding',
            r'NumberOfSharesHeldDetailsOfCrossShareholding'
        ]
        
        shares_elements = []
        for pattern in shares_patterns:
            elements = soup.find_all('ix:nonFraction', {'name': re.compile(pattern)})
            shares_elements.extend(elements)
        
        # 貸借対照表計上額の検索パターン
        book_value_patterns = [
            r'BookValueDetailsOfSpecifiedInvestment',
            r'BookValue.*SpecifiedInvestment',
            r'BookValueDetailsOfShareholding',
            r'BookValueDetailsOfCrossShareholding',
            r'AmountRecordedInBalanceSheet.*SpecifiedInvestment'
        ]
        
        book_value_elements = []
        for pattern in book_value_patterns:
            elements = soup.find_all('ix:nonFraction', {'name': re.compile(pattern)})
            book_value_elements.extend(elements)
        
        # 保有目的の検索パターン
        purpose_patterns = [
            r'PurposeOfShareholding.*SpecifiedInvestment',
            r'PurposeOfHolding.*SpecifiedInvestment',
            r'PurposeOfShareholding',
            r'ReasonForHolding.*SpecifiedInvestment'
        ]
        
        purpose_elements = []
        for pattern in purpose_patterns:
            elements = soup.find_all('ix:nonNumeric', {'name': re.compile(pattern)})
            purpose_elements.extend(elements)
        
        # データを整理
        for name_elem in name_elements:
            security_name = name_elem.get_text(strip=True)
            if security_name:
                contextRef = name_elem.get('contextRef', '')
                
                # 当事業年度のデータのみ抽出
                if any(keyword in contextRef for keyword in ['CurrentYear', 'Current', 'Instant']):
                    
                    # 対応する株式数を検索
                    current_shares = None
                    for shares_elem in shares_elements:
                        if self._contexts_match(contextRef, shares_elem.get('contextRef', '')):
                            current_shares = shares_elem.get_text(strip=True).replace(',', '')
                            break
                    
                    # 対応する貸借対照表計上額を検索
                    current_book_value = None
                    for book_elem in book_value_elements:
                        if self._contexts_match(contextRef, book_elem.get('contextRef', '')):
                            current_book_value = book_elem.get_text(strip=True).replace(',', '')
                            break
                    
                    # 保有目的を検索
                    purpose = None
                    for purpose_elem in purpose_elements:
                        if self._contexts_match(contextRef, purpose_elem.get('contextRef', '')):
                            purpose = purpose_elem.get_text(strip=True)
                            break
                    
                    # データが存在する場合のみ追加
                    if current_shares or current_book_value or purpose:
                        securities_data.append({
                            'held_security_name': security_name,
                            'held_stock_code': self._extract_stock_code(security_name),
                            'held_shares': self._safe_int(current_shares) if current_shares else None,
                            'book_value_million_yen': self._safe_float(current_book_value) if current_book_value else None,
                            'holding_purpose': purpose if purpose else 'N/A'
                        })
        
        return securities_data
    
    def _contexts_match(self, context1, context2):
        """コンテキストが一致するかを判定"""
        if context1 == context2:
            return True
        
        # Rowメンバーで一致を判定
        row1 = re.search(r'Row(\d+)Member', context1)
        row2 = re.search(r'Row(\d+)Member', context2)
        
        if row1 and row2:
            return row1.group(1) == row2.group(1)
        
        return False
    
    def _extract_stock_code(self, security_name):
        """証券名から証券コードを抽出"""
        # 証券コードのパターン（4桁の数字）
        code_match = re.search(r'(\d{4})', security_name)
        return code_match.group(1) if code_match else None
    
    def _safe_int(self, value):
        """安全に整数に変換"""
        if value is None:
            return None
        try:
            return int(value.replace(',', ''))
        except:
            return value
    
    def _safe_float(self, value):
        """安全に浮動小数点に変換"""
        if value is None:
            return None
        try:
            return float(value.replace(',', ''))
        except:
            return value

    def extract_company_info_from_filename(self, filename):
        """ファイル名から会社情報を抽出（フォールバック用）"""
        # 例: jpcrp030000-asr-001_E02840-000_2024-03-31_01_2024-06-27_ixbrl.htm
        pattern = r'_([E]\d+)-(\d+)_(\d{4}-\d{2}-\d{2})_'
        match = re.search(pattern, filename)
        if match:
            return {
                'filing_company_code': match.group(1),
                'document_id': match.group(2),
                'filing_date': match.group(3)
            }
        return None

    def process_xbrl_folder(self, folder_path):
        """個別のXBRLフォルダを処理"""
        zip_files = [f for f in os.listdir(folder_path) if f.endswith('.zip')]
        
        for zip_file in zip_files:
            zip_path = os.path.join(folder_path, zip_file)
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # XBRLファイルを検索
                    xbrl_files = [f for f in zip_ref.namelist() if f.endswith('_ixbrl.htm')]
                    
                    # 本文のXBRLファイルを優先的に選択
                    target_file = None
                    for xbrl_file in xbrl_files:
                        if '0104010_honbun' in xbrl_file:
                            target_file = xbrl_file
                            break
                    
                    # 本文ファイルが見つからない場合、他のファイルを試す
                    if not target_file and xbrl_files:
                        for xbrl_file in xbrl_files:
                            if 'honbun' in xbrl_file:
                                target_file = xbrl_file
                                break
                    
                    if not target_file and xbrl_files:
                        target_file = xbrl_files[0]
                    
                    if target_file:
                        # XBRLファイルを読み込み
                        with zip_ref.open(target_file) as f:
                            xbrl_content = f.read().decode('utf-8')
                        
                        # 提出会社情報を抽出
                        company_info = self.extract_company_info_from_xbrl(xbrl_content)
                        
                        # ファイル名からの情報でフォールバック
                        if not company_info.get('filing_company_code'):
                            file_info = self.extract_company_info_from_filename(target_file)
                            if file_info:
                                company_info.update(file_info)
                        
                        # 特定投資株式情報を抽出
                        securities_data = self.extract_marketable_securities_data(xbrl_content)
                        
                        # 結果をまとめる
                        for security in securities_data:
                            result = {
                                'filing_company_code': company_info.get('filing_company_code'),
                                'filing_company_name': company_info.get('filing_company_name'),
                                'filing_stock_code': company_info.get('filing_stock_code'),
                                'filing_date': company_info.get('filing_date'),
                                'document_id': zip_file.replace('.zip', ''),
                                **security
                            }
                            self.results.append(result)
                            
            except Exception as e:
                print(f"Error processing {zip_file}: {str(e)}")

    def process_all_folders(self):
        """すべてのXBRLフォルダを処理"""
        folders = [f for f in os.listdir(self.xbrl_folder_path) 
                  if os.path.isdir(os.path.join(self.xbrl_folder_path, f))
                  and not f.startswith('.')]
        
        self.total_folders = len(folders)
        print(f"Processing {self.total_folders} folders...")
        
        for i, folder in enumerate(folders):
            self.processed_folders = i + 1
            print(f"Processing folder {self.processed_folders}/{self.total_folders}: {folder}")
            folder_path = os.path.join(self.xbrl_folder_path, folder)
            self.process_xbrl_folder(folder_path)
            
            # 100フォルダごとに進捗を表示
            if self.processed_folders % 100 == 0:
                print(f"Processed {self.processed_folders} folders. Current results: {len(self.results)} records")

    def to_dataframe(self):
        """結果をDataFrameに変換"""
        if not self.results:
            print("No data extracted.")
            return pd.DataFrame()
        
        df = pd.DataFrame(self.results)
        return df

    def save_to_csv(self, filename='all_marketable_securities_analysis.csv'):
        """結果をCSVファイルに保存"""
        df = self.to_dataframe()
        if not df.empty:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"Data saved to {filename}")
            print(f"Total records: {len(df)}")
            print(f"Total unique filing companies: {df['filing_company_code'].nunique()}")
            print(f"Companies with data: {df['filing_company_code'].value_counts()}")
        else:
            print("No data to save.")

def main():
    # XBRLフォルダのパスを指定
    xbrl_folder_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    
    # 全銘柄対応特定投資株式情報抽出器を初期化
    extractor = FullMarketableSecuritiesExtractor(xbrl_folder_path)
    
    # すべてのフォルダを処理
    extractor.process_all_folders()
    
    # 結果をCSVに保存
    extractor.save_to_csv('all_marketable_securities_analysis.csv')

if __name__ == "__main__":
    main()