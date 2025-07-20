import os
import zipfile
import pandas as pd
import re
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

class MarketableSecuritiesExtractor:
    def __init__(self, xbrl_folder_path):
        self.xbrl_folder_path = xbrl_folder_path
        self.results = []
        
    def extract_company_info_from_filename(self, filename):
        """ファイル名から会社情報を抽出"""
        pattern = r'_([A-Z0-9]+)-(\d+)_(\d{4}-\d{2}-\d{2})_'
        match = re.search(pattern, filename)
        if match:
            return {
                'company_code': match.group(1),
                'document_id': match.group(2),
                'filing_date': match.group(3)
            }
        return None

    def extract_xbrl_data(self, xbrl_file_path):
        """XBRLファイルから特定投資株式情報を抽出"""
        try:
            with open(xbrl_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            soup = BeautifulSoup(content, 'lxml-xml')
            
            # 特定投資株式の情報を抽出
            securities_data = []
            
            # 銘柄名を抽出
            name_elements = soup.find_all('ix:nonNumeric', {'name': re.compile(r'NameOfSecuritiesDetailsOfSpecifiedInvestment.*')})
            
            # 株式数を抽出
            shares_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'NumberOfSharesHeldDetailsOfSpecifiedInvestment.*')})
            
            # 貸借対照表計上額を抽出
            book_value_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'BookValueDetailsOfSpecifiedInvestment.*')})
            
            # 保有目的を抽出
            purpose_elements = soup.find_all('ix:nonNumeric', {'name': re.compile(r'PurposeOfShareholding.*SpecifiedInvestment.*')})
            
            # データを整理
            for i, name_elem in enumerate(name_elements):
                if name_elem.get_text(strip=True):
                    contextRef = name_elem.get('contextRef', '')
                    
                    # 当事業年度のデータのみ抽出
                    if 'CurrentYearInstant' in contextRef:
                        # Rowメンバーを抽出
                        row_match = re.search(r'Row(\d+)Member', contextRef)
                        if row_match:
                            row_num = row_match.group(1)
                            
                            # 対応する株式数と貸借対照表計上額を検索
                            current_shares = None
                            current_book_value = None
                            purpose = None
                            
                            # 当事業年度の株式数
                            for shares_elem in shares_elements:
                                if f'CurrentYearInstant_Row{row_num}Member' in shares_elem.get('contextRef', ''):
                                    current_shares = shares_elem.get_text(strip=True).replace(',', '')
                                    break
                            
                            # 当事業年度の貸借対照表計上額
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
                                securities_data.append({
                                    'security_name': name_elem.get_text(strip=True),
                                    'shares': int(current_shares) if current_shares.isdigit() else current_shares,
                                    'book_value_million_yen': float(current_book_value) if current_book_value.replace('.', '').isdigit() else current_book_value,
                                    'purpose': purpose if purpose else 'N/A'
                                })
            
            return securities_data
            
        except Exception as e:
            print(f"Error processing {xbrl_file_path}: {str(e)}")
            return []

    def extract_company_fundamentals(self, company_code, company_name):
        """Yahoo Finance APIを使用してファンダメンタルズ情報を取得"""
        try:
            # 日本株の場合、コードの後に.Tを付ける
            if company_code and company_code.replace('-', '').isdigit():
                ticker = f"{company_code.replace('-', '')}.T"
            else:
                # 会社名から検索を試みる
                ticker = company_name
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 現在の株価情報を取得
            hist = stock.history(period="1d")
            current_price = hist['Close'].iloc[-1] if not hist.empty else None
            
            return {
                'ticker': ticker,
                'current_price': current_price,
                'market_cap': info.get('marketCap'),
                'enterprise_value': info.get('enterpriseValue'),
                'trailing_pe': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'price_to_book': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'country': info.get('country'),
                'website': info.get('website')
            }
        except Exception as e:
            print(f"Error getting fundamentals for {company_code}: {str(e)}")
            return {}

    def process_xbrl_folder(self, folder_path):
        """個別のXBRLフォルダを処理"""
        zip_files = [f for f in os.listdir(folder_path) if f.endswith('.zip')]
        
        for zip_file in zip_files:
            zip_path = os.path.join(folder_path, zip_file)
            extract_path = os.path.join(folder_path, 'extracted')
            
            try:
                # ZIPファイルを解凍
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                
                # 解凍されたファイルから情報を抽出
                for root, dirs, files in os.walk(extract_path):
                    for file in files:
                        if file.endswith('_ixbrl.htm') and '0104010_honbun' in file:
                            file_path = os.path.join(root, file)
                            
                            # ファイル名から会社情報を抽出
                            company_info = self.extract_company_info_from_filename(file)
                            
                            if company_info:
                                # XBRLから特定投資株式情報を抽出
                                securities_data = self.extract_xbrl_data(file_path)
                                
                                for security in securities_data:
                                    # ファンダメンタルズ情報を取得
                                    fundamentals = self.extract_company_fundamentals(
                                        company_info['company_code'], 
                                        company_info['company_code']
                                    )
                                    
                                    result = {
                                        'filing_company_code': company_info['company_code'],
                                        'filing_date': company_info['filing_date'],
                                        'document_id': company_info['document_id'],
                                        'held_security_name': security['security_name'],
                                        'held_shares': security['shares'],
                                        'book_value_million_yen': security['book_value_million_yen'],
                                        'holding_purpose': security['purpose'],
                                        **fundamentals
                                    }
                                    
                                    self.results.append(result)
                
                # 解凍されたファイルを削除
                import shutil
                if os.path.exists(extract_path):
                    shutil.rmtree(extract_path)
                    
            except Exception as e:
                print(f"Error processing {zip_file}: {str(e)}")

    def process_all_folders(self):
        """すべてのXBRLフォルダを処理"""
        folders = [f for f in os.listdir(self.xbrl_folder_path) 
                  if os.path.isdir(os.path.join(self.xbrl_folder_path, f))
                  and not f.startswith('.')]
        
        print(f"Processing {len(folders)} folders...")
        
        for i, folder in enumerate(folders):
            print(f"Processing folder {i+1}/{len(folders)}: {folder}")
            folder_path = os.path.join(self.xbrl_folder_path, folder)
            self.process_xbrl_folder(folder_path)
            
            # 適度な間隔でAPI制限を回避
            if i > 0 and i % 10 == 0:
                print(f"Processed {i} folders. Pausing briefly...")
                import time
                time.sleep(2)

    def to_dataframe(self):
        """結果をDataFrameに変換"""
        if not self.results:
            print("No data extracted. Please run process_all_folders() first.")
            return pd.DataFrame()
        
        df = pd.DataFrame(self.results)
        return df

    def save_to_csv(self, filename='marketable_securities_data.csv'):
        """結果をCSVファイルに保存"""
        df = self.to_dataframe()
        if not df.empty:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"Data saved to {filename}")
            print(f"Total records: {len(df)}")
        else:
            print("No data to save.")

def main():
    # XBRLフォルダのパスを指定
    xbrl_folder_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    
    # 特定投資株式情報抽出器を初期化
    extractor = MarketableSecuritiesExtractor(xbrl_folder_path)
    
    # すべてのフォルダを処理
    extractor.process_all_folders()
    
    # 結果をCSVに保存
    extractor.save_to_csv('marketable_securities_analysis.csv')
    
    # 結果を表示
    df = extractor.to_dataframe()
    if not df.empty:
        print("\nSample data:")
        print(df.head())
        print(f"\nTotal unique filing companies: {df['filing_company_code'].nunique()}")
        print(f"Total held securities: {len(df)}")

if __name__ == "__main__":
    main()