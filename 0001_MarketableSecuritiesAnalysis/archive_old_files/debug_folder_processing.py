import os
import zipfile
import re
from bs4 import BeautifulSoup
import pandas as pd

def debug_folder_processing():
    """フォルダ処理をデバッグ"""
    xbrl_folder_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    
    # フォルダ一覧
    folders = [f for f in os.listdir(xbrl_folder_path) 
              if os.path.isdir(os.path.join(xbrl_folder_path, f))
              and not f.startswith('.')]
    
    print(f"総フォルダ数: {len(folders)}")
    
    # 最初の20フォルダを詳細確認
    success_count = 0
    error_count = 0
    no_zip_count = 0
    no_xbrl_count = 0
    no_data_count = 0
    
    for i, folder in enumerate(folders[:50]):  # 最初の50フォルダを確認
        folder_path = os.path.join(xbrl_folder_path, folder)
        print(f"\n=== フォルダ {i+1}: {folder} ===")
        
        # ZIPファイルの確認
        zip_files = [f for f in os.listdir(folder_path) if f.endswith('.zip')]
        if not zip_files:
            print(f"  ZIPファイルなし")
            no_zip_count += 1
            continue
            
        print(f"  ZIPファイル: {zip_files[0]}")
        
        # ZIPファイルを解凍
        zip_path = os.path.join(folder_path, zip_files[0])
        extract_path = os.path.join(folder_path, 'debug_temp')
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            # 0104010_honbun ファイルを探す
            target_files = []
            for root, dirs, files in os.walk(extract_path):
                for file in files:
                    if file.endswith('_ixbrl.htm') and '0104010_honbun' in file:
                        target_files.append(os.path.join(root, file))
            
            if not target_files:
                print(f"  0104010_honbun ファイルなし")
                no_xbrl_count += 1
                
                # 他のファイルを確認
                all_files = []
                for root, dirs, files in os.walk(extract_path):
                    for file in files:
                        if file.endswith('_ixbrl.htm'):
                            all_files.append(file)
                print(f"  利用可能なXBRLファイル: {all_files[:3]}...")
                
                # 解凍ファイルを削除
                import shutil
                shutil.rmtree(extract_path)
                continue
            
            # ファイル名から会社情報を抽出
            target_file = target_files[0]
            filename = os.path.basename(target_file)
            
            pattern = r'_([A-Z0-9]+)-(\\d+)_(\\d{4}-\\d{2}-\\d{2})_'
            match = re.search(pattern, filename)
            
            if match:
                company_code = match.group(1)
                print(f"  会社コード: {company_code}")
            else:
                print(f"  会社コード抽出失敗: {filename}")
            
            # XBRLファイルから特定投資株式情報を抽出
            try:
                with open(target_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                soup = BeautifulSoup(content, 'lxml-xml')
                
                # 特定投資株式関連の要素を検索
                name_elements = soup.find_all('ix:nonNumeric', {'name': re.compile(r'NameOfSecuritiesDetailsOfSpecifiedInvestment.*')})
                
                if name_elements:
                    print(f"  特定投資株式データ: {len(name_elements)} 件")
                    print(f"  サンプル: {name_elements[0].get_text(strip=True)}")
                    success_count += 1
                else:
                    print(f"  特定投資株式データなし")
                    no_data_count += 1
                    
                    # 他の投資関連要素を確認
                    all_investment_elements = soup.find_all(['ix:nonNumeric', 'ix:nonFraction'])
                    investment_related = [elem for elem in all_investment_elements 
                                        if 'Investment' in elem.get('name', '') or 
                                           'Securities' in elem.get('name', '')]
                    
                    if investment_related:
                        print(f"  その他投資関連要素: {len(investment_related)} 件")
                        print(f"  サンプル: {investment_related[0].get('name', '')}")
                    else:
                        print(f"  投資関連要素なし")
                
            except Exception as e:
                print(f"  XBRLファイル解析エラー: {e}")
                error_count += 1
            
            # 解凍ファイルを削除
            import shutil
            shutil.rmtree(extract_path)
            
        except Exception as e:
            print(f"  ZIP解凍エラー: {e}")
            error_count += 1
    
    print(f"\n=== 結果サマリー ===")
    print(f"成功: {success_count}")
    print(f"ZIPファイルなし: {no_zip_count}")
    print(f"XBRLファイルなし: {no_xbrl_count}")
    print(f"特定投資株式データなし: {no_data_count}")
    print(f"エラー: {error_count}")
    print(f"成功率: {success_count/50*100:.1f}%")

if __name__ == "__main__":
    debug_folder_processing()