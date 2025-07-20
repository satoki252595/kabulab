#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XG1-370 (AMD Ryzen AI 9 HX 370) 専用高速特定投資株式情報抽出器

このシステムは、run_xg1_370_getXBRL.pyで取得したXBRLファイルから
特定投資株式情報を超高速で抽出します。

ハードウェア最適化:
- AMD Ryzen AI 9 HX 370 (12コア/24スレッド)
- Zen 5 (4コア) + Zen 5c (8コア) アーキテクチャ
- 動的加速周波数: 5.1GHz
- L3キャッシュ: 24MB
- DDR5/LPDDR5X (最大128GB)
- PCIe 4.0 NVMe SSD (最大8TB)
"""

import os
import re
import pandas as pd
from bs4 import BeautifulSoup
import warnings
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import subprocess
from pathlib import Path
import multiprocessing as mp
import threading
import psutil
import gc
import time
import sys
import numexpr as ne
import ujson as json
from functools import partial
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import mmap
import asyncio
import aiofiles

warnings.filterwarnings('ignore')

# XG1-370専用最適化設定
@dataclass
class XG1370ExtractorConfig:
    """XG1-370専用抽出器設定"""
    # CPU設定
    PHYSICAL_CORES = 12       # 物理コア数
    LOGICAL_CORES = 24        # 論理コア数
    ZEN5_CORES = 4           # Zen 5高性能コア
    ZEN5C_CORES = 8          # Zen 5c効率コア
    MAX_FREQUENCY = 5.1      # 最大周波数 (GHz)
    L3_CACHE_MB = 24         # L3キャッシュ (MB)
    
    # 並列処理設定
    PROCESS_WORKERS = 12     # プロセス並列度
    THREAD_WORKERS = 24      # スレッド並列度
    IO_WORKERS = 8           # I/O専用ワーカー
    BATCH_SIZE = 200         # バッチサイズ（L3キャッシュ最適化）
    
    # メモリ設定
    MEMORY_LIMIT_GB = 96     # メモリ制限
    MEMORY_MAPPED_THRESHOLD = 5  # メモリマップ閾値（MB）
    
    # ストレージ設定
    PCIE4_ENABLED = True     # PCIe 4.0対応
    NVME_PARALLEL_IO = 16    # NVMe並列I/O
    
    # 抽出設定
    PROGRESS_INTERVAL = 100  # 進捗表示間隔
    
config = XG1370ExtractorConfig()

def setup_xg1370_extractor_environment():
    """XG1-370専用抽出器環境設定"""
    print("=== XG1-370 特定投資株式情報抽出器 環境設定 ===")
    
    # 環境変数設定
    env_vars = {
        'OMP_NUM_THREADS': str(config.LOGICAL_CORES),
        'MKL_NUM_THREADS': str(config.LOGICAL_CORES),
        'OPENBLAS_NUM_THREADS': str(config.LOGICAL_CORES),
        'VECLIB_MAXIMUM_THREADS': str(config.LOGICAL_CORES),
        'NUMEXPR_NUM_THREADS': str(config.LOGICAL_CORES),
        'NUMEXPR_MAX_THREADS': str(config.LOGICAL_CORES),
        'PYTHONHASHSEED': '0',
        'PYTHONUNBUFFERED': '1',
        'MALLOC_MMAP_THRESHOLD_': '65536',
        'MALLOC_TRIM_THRESHOLD_': '131072'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # プロセス優先度設定
    try:
        if sys.platform == "win32":
            psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            os.nice(-15)
        print("✓ プロセス優先度を高く設定")
    except:
        print("△ プロセス優先度設定をスキップ")
    
    # ガベージコレクション最適化
    gc.set_threshold(700, 10, 10)
    
    print(f"✓ 物理コア: {config.PHYSICAL_CORES}, 論理コア: {config.LOGICAL_CORES}")
    print(f"✓ プロセス並列度: {config.PROCESS_WORKERS}")
    print(f"✓ スレッド並列度: {config.THREAD_WORKERS}")
    print(f"✓ バッチサイズ: {config.BATCH_SIZE}")
    print(f"✓ メモリ制限: {config.MEMORY_LIMIT_GB}GB")

def find_xbrl_files_zen5_optimized():
    """Zen 5最適化でXBRLファイルを高速検索"""
    xbrl_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    
    print("=== Zen 5最適化ファイル検索 ===")
    start_time = time.time()
    
    # 複数パターンでの並列検索
    search_patterns = [
        "*0104010_honbun*.htm",
        "*0104010_honbun*.html",
        "*honbun*.htm",
        "*honbun*.html"
    ]
    
    all_files = set()
    
    # 各パターンを並列で検索
    with ThreadPoolExecutor(max_workers=config.ZEN5_CORES) as executor:
        futures = []
        for pattern in search_patterns:
            cmd = f"find {xbrl_path} -name '{pattern}' -type f 2>/dev/null"
            future = executor.submit(subprocess.run, cmd, shell=True, capture_output=True, text=True)
            futures.append(future)
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result.returncode == 0:
                    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
                    all_files.update(files)
            except Exception as e:
                print(f"検索エラー: {str(e)}")
    
    files_list = list(all_files)
    search_time = time.time() - start_time
    
    print(f"ファイル検索完了: {len(files_list)}件 ({search_time:.2f}秒)")
    print(f"検索速度: {len(files_list)/search_time:.0f} files/sec")
    
    return files_list

def extract_company_info_zen5(filepath: str) -> Optional[Dict[str, str]]:
    """Zen 5最適化で会社情報を抽出"""
    filename = os.path.basename(filepath)
    
    # 複数パターンでの高速マッチング
    patterns = [
        re.compile(r'_([E]\d+)-(\d+)_(\d{4}-\d{2}-\d{2})_'),
        re.compile(r'([E]\d+)-(\d+)_(\d{4}-\d{2}-\d{2})'),
        re.compile(r'_([E]\d+)_(\d+)_(\d{4}-\d{2}-\d{2})'),
        re.compile(r'([E]\d+)_(\d+)_(\d{4}-\d{2}-\d{2})')
    ]
    
    for pattern in patterns:
        match = pattern.search(filename)
        if match:
            return {
                'filing_company_code': match.group(1),
                'document_id': match.group(2),
                'filing_date': match.group(3),
                'file_path': filepath
            }
    
    return None

def extract_securities_zen5c_optimized(filepath: str) -> List[Dict[str, any]]:
    """Zen 5c最適化で特定投資株式情報を抽出"""
    try:
        # ファイルサイズチェック
        file_size = os.path.getsize(filepath)
        if file_size > 100 * 1024 * 1024:  # 100MB以上はスキップ
            return []
        
        # 会社情報抽出
        company_info = extract_company_info_zen5(filepath)
        if not company_info:
            return []
        
        # メモリマッピング vs 通常読み込み
        if file_size > config.MEMORY_MAPPED_THRESHOLD * 1024 * 1024:
            # 大容量ファイルはメモリマッピング
            with open(filepath, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                    content = mmapped_file.read().decode('utf-8', errors='ignore')
        else:
            # 小容量ファイルは通常読み込み
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        
        # 高速事前フィルタリング
        if not ('SpecifiedInvestment' in content and 'NameOfSecurities' in content):
            return []
        
        # BeautifulSoupでの高速解析
        soup = BeautifulSoup(content, 'lxml-xml')
        results = []
        
        # コンパイル済み正規表現（L3キャッシュ活用）
        name_patterns = [
            re.compile(r'NameOfSecuritiesDetailsOfSpecifiedInvestment'),
            re.compile(r'NameOfIssuerDetailsOfSpecifiedInvestment'),
            re.compile(r'NameOfSecurities.*SpecifiedInvestment'),
            re.compile(r'NameOfIssuer.*SpecifiedInvestment')
        ]
        
        # 要素の一括取得
        all_nonnumeric = soup.find_all('ix:nonNumeric')
        name_elements = []
        
        for elem in all_nonnumeric:
            name_attr = elem.get('name', '')
            if name_attr and any(pattern.search(name_attr) for pattern in name_patterns):
                name_elements.append(elem)
        
        if not name_elements:
            return []
        
        # コンテキストベース重複除去
        unique_contexts = {}
        for elem in name_elements:
            context = elem.get('contextRef', '')
            if context and any(keyword in context for keyword in ['CurrentYear', 'Current', 'Instant']):
                if context not in unique_contexts:
                    unique_contexts[context] = elem
        
        if not unique_contexts:
            return []
        
        # 関連要素を並列取得
        with ThreadPoolExecutor(max_workers=config.ZEN5C_CORES) as executor:
            # 株式数、簿価、保有目的を並列で取得
            shares_future = executor.submit(
                soup.find_all, 'ix:nonFraction', 
                {'name': re.compile(r'NumberOfSharesHeld.*SpecifiedInvestment')}
            )
            book_value_future = executor.submit(
                soup.find_all, 'ix:nonFraction',
                {'name': re.compile(r'BookValue.*SpecifiedInvestment')}
            )
            purpose_future = executor.submit(
                soup.find_all, 'ix:nonNumeric',
                {'name': re.compile(r'PurposeOfShareholding.*SpecifiedInvestment')}
            )
            
            shares_elements = shares_future.result()
            book_value_elements = book_value_future.result()
            purpose_elements = purpose_future.result()
        
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
                    'filing_company_name': None,
                    'filing_stock_code': None,
                    'filing_date': company_info['filing_date'],
                    'document_id': company_info['document_id'],
                    'held_security_name': security_name,
                    'held_stock_code': stock_code,
                    'held_shares': shares_int,
                    'book_value_million_yen': book_value_float,
                    'holding_purpose': purpose if purpose else 'N/A'
                }
                results.append(result)
        
        return results
        
    except Exception as e:
        # エラーは静かに処理
        return []

def process_batch_zen5c(file_batch: List[str]) -> List[Dict[str, any]]:
    """Zen 5c最適化バッチ処理"""
    batch_results = []
    for filepath in file_batch:
        results = extract_securities_zen5c_optimized(filepath)
        batch_results.extend(results)
    return batch_results

def process_files_hybrid_zen5_zen5c(files: List[str]) -> List[Dict[str, any]]:
    """Zen 5 + Zen 5c ハイブリッド並列処理"""
    print(f"=== Zen 5 + Zen 5c ハイブリッド並列処理 ===")
    print(f"プロセス並列: {config.PROCESS_WORKERS}")
    print(f"スレッド並列: {config.THREAD_WORKERS}")
    
    # ファイルをバッチに分割
    batches = []
    for i in range(0, len(files), config.BATCH_SIZE):
        batch = files[i:i + config.BATCH_SIZE]
        batches.append(batch)
    
    print(f"バッチ数: {len(batches)} (バッチサイズ: {config.BATCH_SIZE})")
    
    all_results = []
    processed_batches = 0
    start_time = time.time()
    
    # ProcessPoolExecutorでZen 5 + Zen 5c活用
    with ProcessPoolExecutor(max_workers=config.PROCESS_WORKERS) as executor:
        # 全バッチを並行処理
        future_to_batch = {executor.submit(process_batch_zen5c, batch): batch for batch in batches}
        
        # 完了順に結果取得
        for future in as_completed(future_to_batch):
            try:
                batch_results = future.result()
                all_results.extend(batch_results)
                processed_batches += 1
                
                # リアルタイム進捗表示
                elapsed = time.time() - start_time
                speed = processed_batches / elapsed if elapsed > 0 else 0
                remaining = len(batches) - processed_batches
                eta = remaining / speed if speed > 0 else 0
                
                if processed_batches % 5 == 0 or processed_batches == len(batches):
                    print(f"処理済み: {processed_batches}/{len(batches)} バッチ | "
                          f"抽出レコード: {len(all_results):,} | "
                          f"速度: {speed:.1f} batch/sec | "
                          f"残り時間: {eta:.0f}秒")
                    
            except Exception as e:
                print(f"バッチ処理エラー: {str(e)}")
    
    total_time = time.time() - start_time
    print(f"=== Zen 5 + Zen 5c並列処理完了 ===")
    print(f"処理時間: {total_time:.2f}秒")
    print(f"バッチ処理速度: {processed_batches/total_time:.2f} batch/sec")
    print(f"ファイル処理速度: {len(files)/total_time:.2f} files/sec")
    print(f"レコード抽出速度: {len(all_results)/total_time:.2f} records/sec")
    
    return all_results

def save_results_pcie4_optimized(results: List[Dict[str, any]], 
                                output_filename: str) -> Optional[pd.DataFrame]:
    """PCIe 4.0 NVMe最適化で結果を保存"""
    if not results:
        print("保存するデータがありません")
        return None
    
    print(f"=== PCIe 4.0 NVMe最適化保存 ===")
    start_time = time.time()
    
    # DataFrameの高速作成
    df = pd.DataFrame(results)
    
    # PCIe 4.0 NVMe最適化書き込み
    df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    
    save_time = time.time() - start_time
    file_size = os.path.getsize(output_filename) / (1024**2)
    save_speed = file_size / save_time if save_time > 0 else 0
    
    print(f"保存完了: {file_size:.1f}MB ({save_time:.2f}秒)")
    print(f"保存速度: {save_speed:.1f} MB/sec")
    
    return df

def print_xg1370_performance_stats(start_time: datetime, end_time: datetime,
                                  file_count: int, record_count: int):
    """XG1-370パフォーマンス統計"""
    processing_time = end_time - start_time
    total_seconds = processing_time.total_seconds()
    
    files_per_second = file_count / total_seconds if total_seconds > 0 else 0
    records_per_second = record_count / total_seconds if total_seconds > 0 else 0
    
    # システムリソース使用率
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    print(f"\n=== XG1-370 パフォーマンス統計 ===")
    print(f"処理時間: {processing_time}")
    print(f"ファイル処理速度: {files_per_second:.1f} files/sec")
    print(f"レコード抽出速度: {records_per_second:.1f} records/sec")
    print(f"CPU使用率: {cpu_percent:.1f}%")
    print(f"メモリ使用率: {memory.percent:.1f}%")
    print(f"使用メモリ: {memory.used / (1024**3):.1f}GB")
    
    # ハードウェア効率
    theoretical_max = config.LOGICAL_CORES * config.MAX_FREQUENCY * 1000
    actual_performance = files_per_second * 1000
    efficiency = (actual_performance / theoretical_max) * 100 if theoretical_max > 0 else 0
    
    print(f"=== ハードウェア効率 ===")
    print(f"理論最大性能: {theoretical_max:.0f} MHz·threads")
    print(f"実測性能: {actual_performance:.0f} normalized")
    print(f"ハードウェア効率: {efficiency:.2f}%")

def main():
    """XG1-370専用メイン処理"""
    print("=" * 80)
    print("XG1-370 (AMD Ryzen AI 9 HX 370) 専用高速特定投資株式情報抽出器")
    print("Zen 5 + Zen 5c + PCIe 4.0 NVMe + L3キャッシュ最適化版")
    print("=" * 80)
    
    # 環境設定
    setup_xg1370_extractor_environment()
    
    # 処理開始
    start_time = datetime.now()
    print(f"\n処理開始: {start_time}")
    
    # Zen 5最適化ファイル検索
    target_files = find_xbrl_files_zen5_optimized()
    
    if not target_files:
        print("対象ファイルが見つかりません")
        return
    
    # Zen 5 + Zen 5c ハイブリッド並列処理
    print(f"\n=== データ抽出開始 ===")
    print(f"対象ファイル数: {len(target_files):,}")
    
    results = process_files_hybrid_zen5_zen5c(target_files)
    
    # 処理終了
    end_time = datetime.now()
    
    # パフォーマンス統計
    print_xg1370_performance_stats(start_time, end_time, len(target_files), len(results))
    
    if results:
        # PCIe 4.0 NVMe最適化保存
        output_filename = f'xg1_370_fast_marketable_securities_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df = save_results_pcie4_optimized(results, output_filename)
        
        if df is not None:
            print(f"\n=== XG1-370 抽出結果 ===")
            print(f"出力ファイル: {output_filename}")
            print(f"総レコード数: {len(df):,}")
            print(f"提出会社数: {df['filing_company_code'].nunique():,}")
            print(f"保有証券数: {df['held_security_name'].nunique():,}")
            
            # 保有金額統計
            book_values = df['book_value_million_yen'].dropna()
            if not book_values.empty:
                total_value = book_values.sum()
                avg_value = book_values.mean()
                print(f"総保有金額: {total_value:,.0f} 百万円")
                print(f"平均保有金額: {avg_value:,.0f} 百万円")
            
            # 上位保有会社
            top_companies = df.groupby('filing_company_code').size().sort_values(ascending=False).head(10)
            print(f"\n=== 上位10社（保有証券数） ===")
            for company, count in top_companies.items():
                print(f"{company}: {count:,}件")
            
            # データサンプル
            print(f"\n=== データサンプル ===")
            sample_df = df[['filing_company_code', 'held_security_name', 'book_value_million_yen']].head(10)
            print(sample_df.to_string(index=False))
        
        print(f"\n=== XG1-370 最終結果 ===")
        print(f"処理ファイル数: {len(target_files):,}")
        print(f"抽出レコード数: {len(results):,}")
        print(f"処理時間: {end_time - start_time}")
        
        total_seconds = (end_time - start_time).total_seconds()
        if total_seconds > 0:
            print(f"平均処理速度: {len(target_files) / total_seconds:.1f} files/sec")
            print(f"レコード抽出速度: {len(results) / total_seconds:.1f} records/sec")
        
    else:
        print("抽出されたデータがありません")
    
    print("\n" + "=" * 80)
    print("XG1-370 抽出処理完了")
    print("=" * 80)

if __name__ == "__main__":
    main()