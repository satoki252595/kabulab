import os
import sys
from extract_marketable_securities import MarketableSecuritiesExtractor

def test_single_folder():
    """単一のフォルダでテストを実行"""
    xbrl_folder_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    
    # テスト対象のフォルダを選択
    test_folder = "S100TA5Q"  # 先ほど確認したフォルダ
    
    extractor = MarketableSecuritiesExtractor(xbrl_folder_path)
    
    print(f"Testing extraction for folder: {test_folder}")
    
    # 単一フォルダを処理
    folder_path = os.path.join(xbrl_folder_path, test_folder)
    if os.path.exists(folder_path):
        extractor.process_xbrl_folder(folder_path)
        
        # 結果を確認
        if extractor.results:
            df = extractor.to_dataframe()
            print(f"\nExtracted {len(df)} records")
            print("\nSample data:")
            print(df.head())
            
            # 保存
            extractor.save_to_csv('test_marketable_securities.csv')
        else:
            print("No data extracted")
    else:
        print(f"Folder {test_folder} not found")

def test_multiple_folders():
    """複数のフォルダでテストを実行"""
    xbrl_folder_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    
    # 最初の5つのフォルダでテスト
    folders = [f for f in os.listdir(xbrl_folder_path) 
              if os.path.isdir(os.path.join(xbrl_folder_path, f))
              and not f.startswith('.')][:5]
    
    extractor = MarketableSecuritiesExtractor(xbrl_folder_path)
    
    print(f"Testing extraction for {len(folders)} folders: {folders}")
    
    for folder in folders:
        folder_path = os.path.join(xbrl_folder_path, folder)
        print(f"Processing: {folder}")
        extractor.process_xbrl_folder(folder_path)
    
    # 結果を確認
    if extractor.results:
        df = extractor.to_dataframe()
        print(f"\nExtracted {len(df)} records from {len(folders)} folders")
        print("\nSample data:")
        print(df.head())
        
        # 統計情報
        print(f"\nUnique filing companies: {df['filing_company_code'].nunique()}")
        print(f"Unique held securities: {df['held_security_name'].nunique()}")
        
        # 保存
        extractor.save_to_csv('test_multiple_marketable_securities.csv')
    else:
        print("No data extracted")

if __name__ == "__main__":
    print("=== Testing Single Folder ===")
    test_single_folder()
    
    print("\n=== Testing Multiple Folders ===")
    test_multiple_folders()