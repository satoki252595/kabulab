import os
import zipfile
import pandas as pd
import re
from bs4 import BeautifulSoup
from extract_marketable_securities import MarketableSecuritiesExtractor

def debug_single_folder():
    """単一フォルダの詳細デバッグ"""
    xbrl_folder_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    test_folder = "S100TA5Q"
    
    folder_path = os.path.join(xbrl_folder_path, test_folder)
    print(f"Debug folder: {folder_path}")
    
    # フォルダの中身を確認
    if os.path.exists(folder_path):
        files = os.listdir(folder_path)
        print(f"Files in folder: {files}")
        
        # ZIPファイルを探す
        zip_files = [f for f in files if f.endswith('.zip')]
        print(f"ZIP files: {zip_files}")
        
        if zip_files:
            zip_path = os.path.join(folder_path, zip_files[0])
            extract_path = os.path.join(folder_path, 'debug_extracted')
            
            print(f"Extracting: {zip_path}")
            
            try:
                # ZIPファイルを解凍
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                
                # 解凍されたファイルを確認
                print("Extracted files:")
                for root, dirs, files in os.walk(extract_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        print(f"  {file_path}")
                        
                        # 0104010_honbun を含むファイルを詳細確認
                        if file.endswith('_ixbrl.htm') and '0104010_honbun' in file:
                            print(f"\n=== Processing: {file} ===")
                            
                            # ファイルサイズを確認
                            size = os.path.getsize(file_path)
                            print(f"File size: {size} bytes")
                            
                            # ファイルの最初の部分を読み込み
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read(1000)  # 最初の1000文字
                                print(f"Content preview: {content[:500]}...")
                            
                            # 特定投資株式の情報を検索
                            debug_xbrl_content(file_path)
                
                # 解凍フォルダを削除
                import shutil
                if os.path.exists(extract_path):
                    shutil.rmtree(extract_path)
                    
            except Exception as e:
                print(f"Error: {e}")
    else:
        print(f"Folder not found: {folder_path}")

def debug_xbrl_content(file_path):
    """XBRLファイルの内容をデバッグ"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # 特定投資株式関連の要素を検索
        print("\n--- Searching for securities data ---")
        
        # 銘柄名を検索
        name_elements = soup.find_all('ix:nonNumeric', {'name': re.compile(r'NameOfSecurities.*SpecifiedInvestment.*')})
        print(f"Found {len(name_elements)} name elements")
        
        for i, elem in enumerate(name_elements[:3]):  # 最初の3つを表示
            print(f"  Name {i+1}: {elem.get_text(strip=True)}")
            print(f"    contextRef: {elem.get('contextRef')}")
        
        # 株式数を検索
        shares_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'NumberOfSharesHeld.*SpecifiedInvestment.*')})
        print(f"Found {len(shares_elements)} shares elements")
        
        for i, elem in enumerate(shares_elements[:3]):  # 最初の3つを表示
            print(f"  Shares {i+1}: {elem.get_text(strip=True)}")
            print(f"    contextRef: {elem.get('contextRef')}")
        
        # 貸借対照表計上額を検索
        book_value_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'BookValue.*SpecifiedInvestment.*')})
        print(f"Found {len(book_value_elements)} book value elements")
        
        for i, elem in enumerate(book_value_elements[:3]):  # 最初の3つを表示
            print(f"  Book Value {i+1}: {elem.get_text(strip=True)}")
            print(f"    contextRef: {elem.get('contextRef')}")
        
        # 特定投資株式関連のテキストを検索
        if "特定投資株式" in content:
            print("\n'特定投資株式' found in content")
        
        # より広範囲の要素を検索
        all_ix_elements = soup.find_all(['ix:nonNumeric', 'ix:nonFraction'])
        print(f"\nTotal ix elements: {len(all_ix_elements)}")
        
        # 特定投資株式関連の要素を抽出
        investment_elements = [elem for elem in all_ix_elements 
                              if 'SpecifiedInvestment' in elem.get('name', '')]
        print(f"SpecifiedInvestment elements: {len(investment_elements)}")
        
        if investment_elements:
            print("\nSpecifiedInvestment elements:")
            for i, elem in enumerate(investment_elements[:5]):
                print(f"  {i+1}. Name: {elem.get('name')}")
                print(f"      Content: {elem.get_text(strip=True)}")
                print(f"      contextRef: {elem.get('contextRef')}")
                
    except Exception as e:
        print(f"Error processing content: {e}")

if __name__ == "__main__":
    debug_single_folder()