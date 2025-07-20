import os
import zipfile
import pandas as pd
import re
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import yfinance as yf
import warnings
import time
import shutil
warnings.filterwarnings('ignore')

class FixedMarketableSecuritiesExtractor:
    def __init__(self, xbrl_folder_path, downloads_path=None):
        self.xbrl_folder_path = xbrl_folder_path
        self.downloads_path = downloads_path
        self.results = []
        self.edinet_code_map = None
        self.processed_count = 0
        self.error_count = 0
        self.no_data_count = 0
        self.success_count = 0
        
        if downloads_path:
            self.load_edinet_code_map()
        
    def load_edinet_code_map(self):
        """EDINETコードマップを読み込み"""
        try:
            extracted_path = os.path.join(self.downloads_path, 'extracted')
            
            if os.path.exists(extracted_path):
                csv_files = [f for f in os.listdir(extracted_path) if f.endswith('.csv')]
                if csv_files:
                    csv_path = os.path.join(extracted_path, csv_files[0])
                    
                    # 複数のエンコーディングを試す
                    encodings = ['cp932', 'shift_jis', 'utf-8', 'euc-jp']
                    for encoding in encodings:
                        try:
                            # Skip the first row which contains metadata
                            self.edinet_code_map = pd.read_csv(csv_path, encoding=encoding, skiprows=1)
                            print(f"EDINETコードマップを読み込みました: {len(self.edinet_code_map)} 企業")
                            break
                        except (UnicodeDecodeError, Exception):
                            continue
                            
        except Exception as e:
            print(f"EDINETコードマップの読み込みに失敗: {e}")
            
    def extract_company_info_from_filename(self, filename):
        """ファイル名から会社情報を抽出（修正版）"""
        # 正規表現パターンを修正
        pattern = r'_([A-Z0-9]+)-(\d+)_(\d{4}-\d{2}-\d{2})_'
        match = re.search(pattern, filename)
        if match:
            return {
                'company_code': match.group(1),
                'document_id': match.group(2),
                'filing_date': match.group(3)
            }
        return None

    def get_company_info_from_edinet(self, edinet_code):
        """EDINETコードから会社情報を取得"""
        if self.edinet_code_map is not None:
            try:
                # 実際のデータから正しい列名を取得
                edinet_col = None
                for col in self.edinet_code_map.columns:
                    if 'EDINET' in col or 'ＥＤＩＮＥＴコード' in col:
                        edinet_col = col
                        break
                
                if edinet_col:
                    match = self.edinet_code_map[self.edinet_code_map[edinet_col] == edinet_code]
                    if not match.empty:
                        row = match.iloc[0]
                        return {
                            'company_name': row.get('提出者名', ''),
                            'stock_code': str(row.get('証券コード', '')).strip() if pd.notna(row.get('証券コード')) else None
                        }
            except Exception as e:
                print(f"EDINETコード {edinet_code} の情報取得エラー: {e}")
        return {'company_name': None, 'stock_code': None}

    def extract_stock_code_from_name(self, security_name):
        """銘柄名から株式コードを抽出"""
        if not security_name:
            return None
            
        # 銘柄名の中の数字を抽出（通常は4桁の証券コード）
        code_pattern = r'[（(]?(\d{4})[）)]?'
        match = re.search(code_pattern, security_name)
        if match:
            return match.group(1)
        
        # EDINETコードマップから検索
        if self.edinet_code_map is not None:
            try:
                clean_name = security_name.replace('㈱', '').replace('株式会社', '').replace('(株)', '')
                clean_name = clean_name.replace('（', '').replace('）', '').replace('(', '').replace(')', '')
                
                matches = self.edinet_code_map[self.edinet_code_map['提出者名'].str.contains(clean_name, na=False)]
                if not matches.empty:
                    stock_code = matches.iloc[0]['証券コード']
                    if pd.notna(stock_code) and str(stock_code).strip() != '':
                        return str(stock_code).strip()
            except Exception:
                pass
        
        return None

    def extract_xbrl_data(self, xbrl_file_path):
        """XBRLファイルから特定投資株式情報を抽出"""
        try:
            with open(xbrl_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            soup = BeautifulSoup(content, 'lxml-xml')
            
            # 特定投資株式の情報を抽出
            securities_data = []
            
            # 各種要素を抽出
            name_elements = soup.find_all('ix:nonNumeric', {'name': re.compile(r'NameOfSecuritiesDetailsOfSpecifiedInvestment.*')})
            shares_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'NumberOfSharesHeldDetailsOfSpecifiedInvestment.*')})
            book_value_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'BookValueDetailsOfSpecifiedInvestment.*')})
            purpose_elements = soup.find_all('ix:nonNumeric', {'name': re.compile(r'PurposeOfShareholding.*SpecifiedInvestment.*')})
            
            # データを整理
            for name_elem in name_elements:
                if name_elem.get_text(strip=True):
                    contextRef = name_elem.get('contextRef', '')
                    
                    # 当事業年度のデータのみ抽出
                    if 'CurrentYearInstant' in contextRef:
                        row_match = re.search(r'Row(\d+)Member', contextRef)
                        if row_match:
                            row_num = row_match.group(1)
                            
                            # 対応するデータを検索
                            current_shares = None
                            current_book_value = None
                            purpose = None
                            
                            # 株式数
                            for shares_elem in shares_elements:
                                if f'CurrentYearInstant_Row{row_num}Member' in shares_elem.get('contextRef', ''):
                                    current_shares = shares_elem.get_text(strip=True).replace(',', '')
                                    break
                            
                            # 貸借対照表計上額
                            for book_elem in book_value_elements:
                                if f'CurrentYearInstant_Row{row_num}Member' in book_elem.get('contextRef', ''):
                                    current_book_value = book_elem.get_text(strip=True).replace(',', '')
                                    break
                            
                            # 保有目的
                            for purpose_elem in purpose_elements:
                                if f'CurrentYearInstant_Row{row_num}Member' in purpose_elem.get('contextRef', ''):
                                    purpose = purpose_elem.get_text(strip=True)
                                    break
                            
                            if current_shares and current_book_value:
                                try:
                                    shares_val = int(current_shares) if current_shares.isdigit() else current_shares
                                    book_val = float(current_book_value) if current_book_value.replace('.', '').isdigit() else current_book_value
                                    
                                    securities_data.append({
                                        'security_name': name_elem.get_text(strip=True),
                                        'shares': shares_val,
                                        'book_value_million_yen': book_val,
                                        'purpose': purpose if purpose else 'N/A'
                                    })
                                except ValueError:
                                    # 数値変換エラーの場合はスキップ
                                    continue
            
            return securities_data
            
        except Exception as e:
            print(f"XBRLファイル処理エラー {xbrl_file_path}: {str(e)}")
            return []

    def extract_company_fundamentals(self, security_name, max_retries=2):
        """Yahoo Finance APIを使用してファンダメンタルズ情報を取得（簡素化版）"""
        try:
            # 株式コードを取得
            stock_code = self.extract_stock_code_from_name(security_name)
            
            if stock_code:
                ticker = f"{stock_code}.T"
                
                for attempt in range(max_retries):
                    try:
                        stock = yf.Ticker(ticker)
                        info = stock.info
                        
                        # 現在の株価情報を取得
                        hist = stock.history(period="1d")
                        current_price = hist['Close'].iloc[-1] if not hist.empty else None
                        
                        return {
                            'ticker': ticker,
                            'stock_code': stock_code,
                            'current_price': current_price,
                            'market_cap': info.get('marketCap'),
                            'sector': info.get('sector'),
                            'industry': info.get('industry')
                        }
                        
                    except Exception:
                        if attempt < max_retries - 1:
                            time.sleep(0.5)
                            continue
                        else:
                            break
                            
            return {'ticker': None, 'stock_code': stock_code}
            
        except Exception:
            return {'ticker': None, 'stock_code': None}

    def process_xbrl_folder(self, folder_path):
        """個別のXBRLフォルダを処理"""
        try:
            zip_files = [f for f in os.listdir(folder_path) if f.endswith('.zip')]
            
            if not zip_files:
                return
                
            for zip_file in zip_files:
                zip_path = os.path.join(folder_path, zip_file)
                extract_path = os.path.join(folder_path, 'temp_extracted')
                
                try:
                    # ZIPファイルを解凍
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_path)
                    
                    # 0104010_honbun ファイルを探す
                    target_files = []
                    for root, dirs, files in os.walk(extract_path):
                        for file in files:
                            if file.endswith('_ixbrl.htm') and '0104010_honbun' in file:
                                target_files.append(os.path.join(root, file))
                    
                    if not target_files:
                        self.no_data_count += 1
                        if os.path.exists(extract_path):
                            shutil.rmtree(extract_path)
                        continue
                    
                    # 解凍されたファイルから情報を抽出
                    for target_file in target_files:
                        filename = os.path.basename(target_file)
                        
                        # ファイル名から会社情報を抽出
                        company_info = self.extract_company_info_from_filename(filename)
                        
                        if company_info:
                            # 会社情報を取得
                            edinet_info = self.get_company_info_from_edinet(company_info['company_code'])
                            
                            # XBRLから特定投資株式情報を抽出
                            securities_data = self.extract_xbrl_data(target_file)
                            
                            if securities_data:
                                self.success_count += 1
                                
                                for security in securities_data:
                                    # ファンダメンタルズ情報を取得
                                    fundamentals = self.extract_company_fundamentals(security['security_name'])
                                    
                                    result = {
                                        'filing_company_code': company_info['company_code'],
                                        'filing_company_name': edinet_info['company_name'],
                                        'filing_stock_code': edinet_info['stock_code'],
                                        'filing_date': company_info['filing_date'],
                                        'document_id': company_info['document_id'],
                                        'held_security_name': security['security_name'],
                                        'held_stock_code': fundamentals.get('stock_code'),
                                        'held_shares': security['shares'],
                                        'book_value_million_yen': security['book_value_million_yen'],
                                        'holding_purpose': security['purpose'],
                                        **fundamentals
                                    }
                                    
                                    self.results.append(result)
                            else:
                                self.no_data_count += 1
                    
                    # 一時ファイルを削除
                    if os.path.exists(extract_path):
                        shutil.rmtree(extract_path)
                        
                    self.processed_count += 1
                        
                except Exception as e:
                    print(f"ZIPファイル処理エラー {zip_file}: {str(e)}")
                    self.error_count += 1
                    if os.path.exists(extract_path):
                        shutil.rmtree(extract_path)
                        
        except Exception as e:
            print(f"フォルダ処理エラー {folder_path}: {str(e)}")
            self.error_count += 1

    def process_all_folders(self, limit=None):
        """すべてのXBRLフォルダを処理"""
        folders = [f for f in os.listdir(self.xbrl_folder_path) 
                  if os.path.isdir(os.path.join(self.xbrl_folder_path, f))
                  and not f.startswith('.')]
        
        if limit:
            folders = folders[:limit]
        
        print(f"処理対象フォルダ数: {len(folders)}")
        
        for i, folder in enumerate(folders):
            if i % 100 == 0:
                print(f"進捗: {i}/{len(folders)} - 成功: {self.success_count}, データなし: {self.no_data_count}, エラー: {self.error_count}")
            
            folder_path = os.path.join(self.xbrl_folder_path, folder)
            self.process_xbrl_folder(folder_path)
            
            # 適度な間隔でAPI制限を回避
            if i > 0 and i % 50 == 0:
                time.sleep(3)
        
        print(f"\n処理完了: {len(folders)} フォルダ")
        print(f"成功: {self.success_count} 企業")
        print(f"特定投資株式データなし: {self.no_data_count} 企業")
        print(f"エラー: {self.error_count} 企業")
        print(f"抽出データ件数: {len(self.results)}")

    def to_dataframe(self):
        """結果をDataFrameに変換"""
        if not self.results:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.results)
        return df

    def save_to_csv(self, filename):
        """結果をCSVファイルに保存"""
        df = self.to_dataframe()
        if not df.empty:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"データを保存しました: {filename}")
            print(f"総レコード数: {len(df)}")
            print(f"提出企業数: {df['filing_company_code'].nunique()}")
            return True
        else:
            print("保存するデータがありません。")
            return False

def main():
    # XBRLフォルダのパスを指定
    xbrl_folder_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    downloads_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/downloads"
    
    # 修正版抽出器を初期化
    extractor = FixedMarketableSecuritiesExtractor(xbrl_folder_path, downloads_path)
    
    # 全フォルダを処理（制限なし）
    print("全上場企業のXBRLファイルを処理開始...")
    extractor.process_all_folders(limit=None)
    
    # 結果をCSVに保存
    extractor.save_to_csv('all_companies_marketable_securities_analysis.csv')
    
    # 結果を表示
    df = extractor.to_dataframe()
    if not df.empty:
        print("\n=== 結果サマリー ===")
        print(df.head())
        print(f"\n提出企業数: {df['filing_company_code'].nunique()}")
        print(f"保有銘柄数: {df['held_security_name'].nunique()}")
        print(f"株式コード取得済み: {df['held_stock_code'].notna().sum()}")

if __name__ == "__main__":
    main()