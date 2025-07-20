import os
import pandas as pd
from fixed_extraction_corrected import FixedMarketableSecuritiesExtractor
import time

def process_in_batches(batch_size=500, start_batch=0):
    """バッチ処理で全データを処理"""
    
    # パス設定
    xbrl_folder_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    downloads_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/downloads"
    
    # 抽出器を初期化
    extractor = FixedMarketableSecuritiesExtractor(xbrl_folder_path, downloads_path)
    
    # 全フォルダを取得
    all_folders = [f for f in os.listdir(xbrl_folder_path) 
                   if os.path.isdir(os.path.join(xbrl_folder_path, f))
                   and not f.startswith('.')]
    
    total_folders = len(all_folders)
    print(f"総フォルダ数: {total_folders}")
    
    # バッチ処理
    all_results = []
    total_success = 0
    total_no_data = 0
    total_error = 0
    
    batch_num = start_batch
    
    while batch_num * batch_size < total_folders:
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, total_folders)
        
        batch_folders = all_folders[start_idx:end_idx]
        
        print(f"\n=== バッチ {batch_num + 1} 処理開始 ===")
        print(f"フォルダ {start_idx + 1} - {end_idx} を処理")
        
        # 新しい抽出器でバッチ処理
        batch_extractor = FixedMarketableSecuritiesExtractor(xbrl_folder_path, downloads_path)
        
        # バッチ内のフォルダを処理
        for i, folder in enumerate(batch_folders):
            if (i + 1) % 50 == 0:
                print(f"  バッチ内進捗: {i + 1}/{len(batch_folders)}")
            
            folder_path = os.path.join(xbrl_folder_path, folder)
            batch_extractor.process_xbrl_folder(folder_path)
        
        # バッチ結果を記録
        batch_results = batch_extractor.results
        all_results.extend(batch_results)
        
        total_success += batch_extractor.success_count
        total_no_data += batch_extractor.no_data_count
        total_error += batch_extractor.error_count
        
        print(f"バッチ {batch_num + 1} 完了:")
        print(f"  成功: {batch_extractor.success_count}")
        print(f"  データなし: {batch_extractor.no_data_count}")
        print(f"  エラー: {batch_extractor.error_count}")
        print(f"  抽出データ件数: {len(batch_results)}")
        
        # 中間結果を保存
        if all_results:
            df = pd.DataFrame(all_results)
            intermediate_filename = f"batch_results_through_{batch_num + 1}.csv"
            df.to_csv(intermediate_filename, index=False, encoding='utf-8-sig')
            print(f"  中間結果保存: {intermediate_filename}")
        
        # 累積結果を表示
        print(f"累積結果 (バッチ {batch_num + 1}まで):")
        print(f"  総成功: {total_success}")
        print(f"  総データなし: {total_no_data}")
        print(f"  総エラー: {total_error}")
        print(f"  総抽出データ件数: {len(all_results)}")
        
        batch_num += 1
        
        # メモリ管理のため少し待機
        time.sleep(2)
    
    # 最終結果を保存
    print(f"\n=== 全処理完了 ===")
    print(f"総フォルダ数: {total_folders}")
    print(f"総成功企業数: {total_success}")
    print(f"総データなし企業数: {total_no_data}")
    print(f"総エラー企業数: {total_error}")
    print(f"総抽出データ件数: {len(all_results)}")
    
    if all_results:
        final_df = pd.DataFrame(all_results)
        final_filename = "final_all_companies_marketable_securities.csv"
        final_df.to_csv(final_filename, index=False, encoding='utf-8-sig')
        
        print(f"\n最終結果統計:")
        print(f"提出企業数: {final_df['filing_company_code'].nunique()}")
        print(f"保有銘柄数: {final_df['held_security_name'].nunique()}")
        print(f"株式コード取得済み: {final_df['held_stock_code'].notna().sum()}")
        print(f"最終結果保存: {final_filename}")
        
        return final_df
    
    return None

if __name__ == "__main__":
    # バッチサイズ500で処理開始
    result_df = process_in_batches(batch_size=500)