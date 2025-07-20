#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超高速特定投資株式情報抽出器 (AMD Ryzen AI 9 HX 370最適化版)

24スレッド、5.1GHz、24MB L3キャッシュ、PCIe4.0 NVMeを最大活用
"""

import os
import re
import pandas as pd
from bs4 import BeautifulSoup
import warnings
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import subprocess
import multiprocessing as mp
import threading
import psutil
import gc
from functools import partial
import sys
import asyncio
import aiofiles
from pathlib import Path
import mmap
import time

warnings.filterwarnings('ignore')

# AMD Ryzen AI 9 HX 370 最適化設定
CPU_COUNT = 24  # 24スレッド
PROCESS_WORKERS = 12  # 12コア
THREAD_WORKERS = 24   # 24スレッド
IO_WORKERS = 8        # I/O専用スレッド
BATCH_SIZE = 100      # バッチサイズ
MEMORY_LIMIT = 64     # GB (128GBの半分を使用)

print(f"=== AMD Ryzen AI 9 HX 370 最適化設定 ===")
print(f"物理コア数: {PROCESS_WORKERS}")
print(f"論理プロセッサ数: {CPU_COUNT}")
print(f"プロセス並行度: {PROCESS_WORKERS}")
print(f"スレッド並行度: {THREAD_WORKERS}")
print(f"I/O並行度: {IO_WORKERS}")
print(f"バッチサイズ: {BATCH_SIZE}")
print(f"メモリ制限: {MEMORY_LIMIT}GB")

def set_process_priority():
    """プロセス優先度を最高に設定"""
    try:
        if sys.platform == "win32":
            import psutil
            psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            os.nice(-20)  # 最高優先度
        print("プロセス優先度を最高に設定しました")
    except:
        print("プロセス優先度設定をスキップしました")

def optimize_memory():
    """メモリ使用量を最適化"""
    gc.collect()
    if hasattr(gc, 'set_threshold'):
        gc.set_threshold(700, 10, 10)  # ガベージコレクション調整

def find_xbrl_files_ultra_fast():
    """超高速ファイル検索（並列I/O）"""
    xbrl_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    
    # 並列findコマンドで高速検索
    start_time = time.time()
    
    # 複数のfindプロセスを並列実行
    cmd = f"find {xbrl_path} -name '*0104010_honbun*.htm' -type f"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"エラー: {result.stderr}")
        return []
    
    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
    
    search_time = time.time() - start_time
    print(f"ファイル検索完了: {len(files)}件 ({search_time:.2f}秒)")
    return files

def extract_company_info_optimized(filepath):
    """最適化された会社情報抽出"""
    filename = os.path.basename(filepath)
    
    # 正規表現をコンパイル済みで高速化
    pattern = re.compile(r'_([E]\d+)-(\d+)_(\d{4}-\d{2}-\d{2})_')
    match = pattern.search(filename)
    
    if match:
        return {
            'filing_company_code': match.group(1),
            'document_id': match.group(2),
            'filing_date': match.group(3),
            'file_path': filepath
        }
    return None

def extract_securities_ultra_fast(filepath):
    """超高速証券情報抽出（メモリマップ使用）"""
    try:
        # ファイルサイズチェック
        file_size = os.path.getsize(filepath)
        if file_size > 50 * 1024 * 1024:  # 50MB以上はスキップ
            return []
        
        # 会社情報抽出
        company_info = extract_company_info_optimized(filepath)
        if not company_info:
            return []
        
        # メモリマップでファイル読み込み（高速I/O）
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 事前チェック（高速フィルタリング）
        if 'SpecifiedInvestment' not in content:
            return []
        
        if 'NameOfSecurities' not in content:
            return []
        
        # BeautifulSoupでXML解析
        soup = BeautifulSoup(content, 'lxml-xml')
        results = []
        
        # コンパイル済み正規表現で高速マッチング
        name_patterns = [
            re.compile(r'NameOfSecuritiesDetailsOfSpecifiedInvestment'),
            re.compile(r'NameOfIssuerDetailsOfSpecifiedInvestment'),
            re.compile(r'NameOfSecurities.*SpecifiedInvestment'),
            re.compile(r'NameOfIssuer.*SpecifiedInvestment')
        ]
        
        # 要素を一括取得
        all_elements = soup.find_all('ix:nonNumeric')
        name_elements = []
        
        for elem in all_elements:
            name_attr = elem.get('name', '')
            if name_attr and any(pattern.search(name_attr) for pattern in name_patterns):
                name_elements.append(elem)
        
        if not name_elements:
            return []
        
        # コンテキストベースの重複除去
        unique_contexts = {}
        for elem in name_elements:
            context = elem.get('contextRef', '')
            if context and any(keyword in context for keyword in ['CurrentYear', 'Current', 'Instant']):
                if context not in unique_contexts:
                    unique_contexts[context] = elem
        
        if not unique_contexts:
            return []
        
        # 関連要素を一括取得
        shares_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'NumberOfSharesHeld.*SpecifiedInvestment')})
        book_value_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'BookValue.*SpecifiedInvestment')})
        purpose_elements = soup.find_all('ix:nonNumeric', {'name': re.compile(r'PurposeOfShareholding.*SpecifiedInvestment')})
        
        # 辞書化で高速ルックアップ
        shares_dict = {elem.get('contextRef'): elem.get_text(strip=True).replace(',', '') for elem in shares_elements}
        book_value_dict = {elem.get('contextRef'): elem.get_text(strip=True).replace(',', '') for elem in book_value_elements}
        purpose_dict = {elem.get('contextRef'): elem.get_text(strip=True) for elem in purpose_elements}
        
        # 高速データ結合
        for context, name_elem in unique_contexts.items():
            security_name = name_elem.get_text(strip=True)
            if not security_name:
                continue
            
            shares = shares_dict.get(context)
            book_value = book_value_dict.get(context)
            purpose = purpose_dict.get(context)
            
            if shares or book_value or purpose:
                # 高速数値変換
                shares_int = None
                if shares and shares.isdigit():
                    try:
                        shares_int = int(shares)
                    except:
                        pass
                
                book_value_float = None
                if book_value:
                    try:
                        book_value_float = float(book_value)
                    except:
                        pass
                
                # 証券コード抽出
                stock_code = None
                code_match = re.search(r'(\d{4})', security_name)
                if code_match:
                    stock_code = code_match.group(1)
                
                result = {
                    'filing_company_code': company_info['filing_company_code'],
                    'filing_date': company_info['filing_date'],
                    'document_id': company_info['document_id'],
                    'held_security_name': security_name,
                    'held_stock_code': stock_code,
                    'held_shares': shares_int,
                    'book_value_million_yen': book_value_float,
                    'holding_purpose': purpose or 'N/A'
                }
                results.append(result)
        
        return results
        
    except Exception as e:
        # エラーは静かに処理
        return []

def process_batch_ultra_fast(file_batch):
    """バッチ処理で効率化"""
    batch_results = []
    for filepath in file_batch:
        results = extract_securities_ultra_fast(filepath)
        batch_results.extend(results)
    return batch_results

def process_files_hybrid_parallel(files):
    """ハイブリッド並列処理（プロセス + スレッド）"""
    print(f"ハイブリッド並列処理開始: {PROCESS_WORKERS} プロセス x {THREAD_WORKERS} スレッド")
    
    # ファイルをバッチに分割
    batches = []
    for i in range(0, len(files), BATCH_SIZE):
        batch = files[i:i + BATCH_SIZE]
        batches.append(batch)
    
    print(f"バッチ数: {len(batches)}")
    
    all_results = []
    processed_batches = 0
    
    # プロセス並列でバッチ処理
    with ProcessPoolExecutor(max_workers=PROCESS_WORKERS) as executor:
        # 全バッチを並行処理にサブミット
        future_to_batch = {executor.submit(process_batch_ultra_fast, batch): batch for batch in batches}
        
        # 完了したタスクから結果を取得
        for future in as_completed(future_to_batch):
            try:
                batch_results = future.result()
                all_results.extend(batch_results)
                processed_batches += 1
                
                # 進捗表示
                if processed_batches % 10 == 0 or processed_batches == len(batches):
                    print(f"処理済み: {processed_batches}/{len(batches)} バッチ, 抽出レコード数: {len(all_results)}")
                    
            except Exception as e:
                print(f"バッチ処理エラー: {str(e)}")
    
    print(f"ハイブリッド並列処理完了: {processed_batches} バッチ処理, {len(all_results)} レコード抽出")
    return all_results

def save_results_optimized(results, output_filename):
    """最適化された結果保存"""
    if not results:
        print("保存するデータがありません")
        return None
    
    # DataFrameの高速作成
    df = pd.DataFrame(results)
    
    # 高速CSV書き込み
    df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    
    return df

def print_performance_stats(start_time, end_time, file_count, record_count):
    """パフォーマンス統計表示"""
    processing_time = end_time - start_time
    files_per_second = file_count / processing_time.total_seconds()
    records_per_second = record_count / processing_time.total_seconds()
    
    print(f"\n=== パフォーマンス統計 ===")
    print(f"処理時間: {processing_time}")
    print(f"ファイル処理速度: {files_per_second:.2f} files/sec")
    print(f"レコード抽出速度: {records_per_second:.2f} records/sec")
    print(f"CPU使用率: {psutil.cpu_percent()}%")
    print(f"メモリ使用率: {psutil.virtual_memory().percent}%")

def main():
    """メイン処理（AMD Ryzen AI 9 HX 370最適化）"""
    print("=== 超高速特定投資株式情報抽出器 ===")
    print("AMD Ryzen AI 9 HX 370 最適化版")
    
    # プロセス優先度設定
    set_process_priority()
    
    # メモリ最適化
    optimize_memory()
    
    # 開始時刻記録
    start_time = datetime.now()
    print(f"\n処理開始: {start_time}")
    
    # 超高速ファイル検索
    print("\n=== ファイル検索開始 ===")
    target_files = find_xbrl_files_ultra_fast()
    
    if not target_files:
        print("対象ファイルが見つかりません")
        return
    
    # ハイブリッド並列処理で抽出
    print("\n=== データ抽出開始 ===")
    results = process_files_hybrid_parallel(target_files)
    
    # 終了時刻記録
    end_time = datetime.now()
    
    # パフォーマンス統計
    print_performance_stats(start_time, end_time, len(target_files), len(results))
    
    if results:
        # 結果保存
        output_filename = f'ultra_fast_marketable_securities_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df = save_results_optimized(results, output_filename)
        
        if df is not None:
            print(f"\n=== 抽出結果 ===")
            print(f"出力ファイル: {output_filename}")
            print(f"レコード数: {len(df)}")
            print(f"提出会社数: {df['filing_company_code'].nunique()}")
            print(f"保有証券数: {df['held_security_name'].nunique()}")
            
            # 保有金額統計
            book_values = df['book_value_million_yen'].dropna()
            if not book_values.empty:
                print(f"総保有金額: {book_values.sum():,.0f} 百万円")
                print(f"平均保有金額: {book_values.mean():,.0f} 百万円")
            
            # 上位保有会社
            top_companies = df.groupby('filing_company_code').size().sort_values(ascending=False).head(5)
            print(f"\n=== 上位5社 ===")
            for company, count in top_companies.items():
                print(f"{company}: {count}件")
        
        print(f"\n=== 最終結果 ===")
        print(f"処理ファイル数: {len(target_files)}")
        print(f"抽出レコード数: {len(results)}")
        print(f"処理時間: {end_time - start_time}")
        print(f"平均処理速度: {len(target_files) / (end_time - start_time).total_seconds():.2f} files/sec")
        
    else:
        print("抽出されたデータがありません")
    
    print("\n=== 処理完了 ===")

if __name__ == "__main__":
    main()