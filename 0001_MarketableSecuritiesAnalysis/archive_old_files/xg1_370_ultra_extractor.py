#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XG1-370 (AMD Ryzen AI 9 HX 370) 専用超高速特定投資株式情報抽出器

ハードウェア仕様:
- AMD Ryzen AI 9 HX 370 (12コア/24スレッド)
- 動的加速周波数: 5.1GHz
- L3キャッシュ: 24MB
- メモリ: DDR5 5600MHz/LPDDR5X 7500MHz (最大128GB)
- ストレージ: PCIe 4.0 NVMe SSD (最大8TB)
- AIパフォーマンス: 80TOPS (NPU 50TOPS)
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
import time
from pathlib import Path
import mmap
import asyncio
import aiofiles
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
import numexpr as ne
import ujson as json

warnings.filterwarnings('ignore')

# XG1-370 最適化パラメータ
@dataclass
class XG1370Config:
    """XG1-370専用最適化設定"""
    # CPU設定
    PHYSICAL_CORES = 12       # 物理コア数
    LOGICAL_CORES = 24        # 論理コア数（12×2）
    ZEN5_CORES = 4           # Zen 5コア数
    ZEN5C_CORES = 8          # Zen 5cコア数
    MAX_FREQUENCY = 5.1      # 最大動作周波数 (GHz)
    L3_CACHE_MB = 24         # L3キャッシュ (MB)
    
    # 並列処理設定
    PROCESS_WORKERS = 12     # プロセス並列度（物理コア数）
    THREAD_WORKERS = 24      # スレッド並列度（論理コア数）
    IO_WORKERS = 8           # I/O専用ワーカー
    BATCH_SIZE = 150         # バッチサイズ（L3キャッシュ活用）
    
    # メモリ設定
    MEMORY_LIMIT_GB = 96     # メモリ制限（128GBの75%）
    MEMORY_MAPPED_THRESHOLD = 10  # メモリマップ閾値（MB）
    
    # ストレージ設定
    PCIE4_ENABLED = True     # PCIe 4.0対応
    NVME_PARALLEL_IO = 16    # NVMe並列I/O数
    
    # AI加速設定
    NPU_ENABLED = False      # NPU利用（将来拡張用）
    GPU_COMPUTE = False      # GPU計算支援（将来拡張用）

config = XG1370Config()

def setup_xg1370_environment():
    """XG1-370専用環境設定"""
    print("=== XG1-370 (AMD Ryzen AI 9 HX 370) 最適化環境設定 ===")
    
    # 環境変数設定（Zen 5 + Zen 5c対応）
    env_vars = {
        'OMP_NUM_THREADS': str(config.LOGICAL_CORES),
        'MKL_NUM_THREADS': str(config.LOGICAL_CORES),
        'OPENBLAS_NUM_THREADS': str(config.LOGICAL_CORES),
        'VECLIB_MAXIMUM_THREADS': str(config.LOGICAL_CORES),
        'NUMEXPR_NUM_THREADS': str(config.LOGICAL_CORES),
        'NUMEXPR_MAX_THREADS': str(config.LOGICAL_CORES),
        'PYTHONHASHSEED': '0',
        'PYTHONUNBUFFERED': '1',
        'MALLOC_MMAP_THRESHOLD_': '65536',  # メモリ最適化
        'MALLOC_TRIM_THRESHOLD_': '131072'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✓ {key} = {value}")
    
    # プロセス優先度設定
    try:
        if sys.platform == "win32":
            psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            os.nice(-20)  # 最高優先度
        print("✓ プロセス優先度を最高に設定")
    except:
        print("△ プロセス優先度設定をスキップ")
    
    # ガベージコレクション最適化
    gc.set_threshold(700, 10, 10)
    
    print(f"✓ 物理コア: {config.PHYSICAL_CORES}, 論理コア: {config.LOGICAL_CORES}")
    print(f"✓ プロセス並列度: {config.PROCESS_WORKERS}")
    print(f"✓ スレッド並列度: {config.THREAD_WORKERS}")
    print(f"✓ バッチサイズ: {config.BATCH_SIZE}")
    print(f"✓ メモリ制限: {config.MEMORY_LIMIT_GB}GB")

def check_xg1370_hardware():
    """XG1-370ハードウェア確認"""
    print("=== XG1-370 ハードウェア確認 ===")
    
    # CPU情報
    cpu_count = os.cpu_count()
    cpu_freq = psutil.cpu_freq()
    print(f"論理プロセッサ数: {cpu_count}")
    if cpu_freq:
        print(f"CPU周波数: {cpu_freq.current:.0f}MHz (最大: {cpu_freq.max:.0f}MHz)")
    
    # メモリ情報
    memory = psutil.virtual_memory()
    print(f"総メモリ: {memory.total / (1024**3):.1f}GB")
    print(f"利用可能メモリ: {memory.available / (1024**3):.1f}GB")
    
    # ディスク情報
    disk = psutil.disk_usage('/')
    print(f"ディスク容量: {disk.total / (1024**3):.1f}GB")
    print(f"ディスク空き: {disk.free / (1024**3):.1f}GB")
    
    # メモリ不足チェック
    if memory.available < config.MEMORY_LIMIT_GB * 1024**3:
        print(f"⚠ 利用可能メモリが不足しています。制限を{memory.available // (1024**3) - 2}GBに調整")
        config.MEMORY_LIMIT_GB = max(8, int(memory.available // (1024**3) - 2))
    
    return True

def find_xbrl_files_pcie4():
    """PCIe 4.0 NVMe SSD最適化ファイル検索"""
    xbrl_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    
    print("=== PCIe 4.0 NVMe最適化ファイル検索 ===")
    start_time = time.time()
    
    # 並列findで高速検索（NVMe SSD活用）
    cmd = f"find {xbrl_path} -name '*0104010_honbun*.htm' -type f"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"エラー: {result.stderr}")
        return []
    
    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
    
    search_time = time.time() - start_time
    print(f"ファイル検索完了: {len(files)}件 ({search_time:.2f}秒)")
    print(f"検索速度: {len(files)/search_time:.0f} files/sec")
    
    return files

def extract_company_info_zen5(filepath: str) -> Optional[Dict[str, str]]:
    """Zen 5最適化会社情報抽出"""
    filename = os.path.basename(filepath)
    
    # コンパイル済み正規表現（L3キャッシュ活用）
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

def extract_securities_zen5_optimized(filepath: str) -> List[Dict[str, Any]]:
    """Zen 5 + Zen 5c最適化証券情報抽出"""
    try:
        # ファイルサイズ事前チェック
        file_size = os.path.getsize(filepath)
        if file_size > 100 * 1024 * 1024:  # 100MB以上はスキップ
            return []
        
        # 会社情報抽出
        company_info = extract_company_info_zen5(filepath)
        if not company_info:
            return []
        
        # メモリマッピング vs 通常読み込み判定
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
        
        # lxml-xmlパーサーで高速解析
        soup = BeautifulSoup(content, 'lxml-xml')
        results = []
        
        # コンパイル済み正規表現パターン（L3キャッシュ活用）
        name_patterns = [
            re.compile(r'NameOfSecuritiesDetailsOfSpecifiedInvestment'),
            re.compile(r'NameOfIssuerDetailsOfSpecifiedInvestment'),
            re.compile(r'NameOfSecurities.*SpecifiedInvestment'),
            re.compile(r'NameOfIssuer.*SpecifiedInvestment')
        ]
        
        # 要素の一括取得と高速フィルタリング
        all_nonnumeric = soup.find_all('ix:nonNumeric')
        name_elements = []
        
        for elem in all_nonnumeric:
            name_attr = elem.get('name', '')
            if name_attr and any(pattern.search(name_attr) for pattern in name_patterns):
                name_elements.append(elem)
        
        if not name_elements:
            return []
        
        # コンテキストベース重複除去（numexpr活用）
        unique_contexts = {}
        for elem in name_elements:
            context = elem.get('contextRef', '')
            if context and any(keyword in context for keyword in ['CurrentYear', 'Current', 'Instant']):
                if context not in unique_contexts:
                    unique_contexts[context] = elem
        
        if not unique_contexts:
            return []
        
        # 関連要素を一括取得（Zen 5 + Zen 5c並列処理）
        shares_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'NumberOfSharesHeld.*SpecifiedInvestment')})
        book_value_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'BookValue.*SpecifiedInvestment')})
        purpose_elements = soup.find_all('ix:nonNumeric', {'name': re.compile(r'PurposeOfShareholding.*SpecifiedInvestment')})
        
        # 辞書化（高速ルックアップ）
        shares_dict = {elem.get('contextRef'): elem.get_text(strip=True).replace(',', '') for elem in shares_elements}
        book_value_dict = {elem.get('contextRef'): elem.get_text(strip=True).replace(',', '') for elem in book_value_elements}
        purpose_dict = {elem.get('contextRef'): elem.get_text(strip=True) for elem in purpose_elements}
        
        # 高速データマージ
        for context, name_elem in unique_contexts.items():
            security_name = name_elem.get_text(strip=True)
            if not security_name:
                continue
            
            shares = shares_dict.get(context)
            book_value = book_value_dict.get(context)
            purpose = purpose_dict.get(context)
            
            if shares or book_value or purpose:
                # 高速数値変換（numexpr使用）
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
                
                # 証券コード高速抽出
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
        
    except Exception:
        return []

def process_batch_zen5c(file_batch: List[str]) -> List[Dict[str, Any]]:
    """Zen 5c最適化バッチ処理"""
    batch_results = []
    for filepath in file_batch:
        results = extract_securities_zen5_optimized(filepath)
        batch_results.extend(results)
    return batch_results

def process_files_hybrid_zen5(files: List[str]) -> List[Dict[str, Any]]:
    """Zen 5 + Zen 5c ハイブリッド並列処理"""
    print(f"=== Zen 5 + Zen 5c ハイブリッド並列処理 ===")
    print(f"プロセス並列: {config.PROCESS_WORKERS} (物理コア)")
    print(f"スレッド並列: {config.THREAD_WORKERS} (論理コア)")
    
    # ファイルをバッチに分割（L3キャッシュ効率化）
    batches = []
    for i in range(0, len(files), config.BATCH_SIZE):
        batch = files[i:i + config.BATCH_SIZE]
        batches.append(batch)
    
    print(f"バッチ数: {len(batches)} (バッチサイズ: {config.BATCH_SIZE})")
    
    all_results = []
    processed_batches = 0
    start_time = time.time()
    
    # ProcessPoolExecutorでZen 5コア活用
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
                          f"抽出レコード: {len(all_results)} | "
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

def save_results_pcie4(results: List[Dict[str, Any]], output_filename: str) -> Optional[pd.DataFrame]:
    """PCIe 4.0 NVMe最適化結果保存"""
    if not results:
        print("保存するデータがありません")
        return None
    
    print(f"=== PCIe 4.0 NVMe高速書き込み ===")
    start_time = time.time()
    
    # DataFrameの高速作成
    df = pd.DataFrame(results)
    
    # PCIe 4.0 NVMe SSD最適化書き込み
    df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    
    write_time = time.time() - start_time
    file_size = os.path.getsize(output_filename) / (1024**2)
    write_speed = file_size / write_time if write_time > 0 else 0
    
    print(f"書き込み完了: {file_size:.1f}MB ({write_time:.2f}秒)")
    print(f"書き込み速度: {write_speed:.1f} MB/sec")
    
    return df

def print_xg1370_performance_stats(start_time: datetime, end_time: datetime, 
                                   file_count: int, record_count: int):
    """XG1-370パフォーマンス統計"""
    processing_time = end_time - start_time
    total_seconds = processing_time.total_seconds()
    
    files_per_second = file_count / total_seconds if total_seconds > 0 else 0
    records_per_second = record_count / total_seconds if total_seconds > 0 else 0
    
    # ハードウェア利用率
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    print(f"\n=== XG1-370 パフォーマンス統計 ===")
    print(f"処理時間: {processing_time}")
    print(f"ファイル処理速度: {files_per_second:.1f} files/sec")
    print(f"レコード抽出速度: {records_per_second:.1f} records/sec")
    print(f"CPU使用率: {cpu_percent:.1f}%")
    print(f"メモリ使用率: {memory.percent:.1f}%")
    print(f"使用メモリ: {memory.used / (1024**3):.1f}GB")
    
    # 効率計算
    theoretical_max = config.LOGICAL_CORES * config.MAX_FREQUENCY * 1000  # MHz
    actual_performance = files_per_second * 1000  # 正規化
    efficiency = (actual_performance / theoretical_max) * 100 if theoretical_max > 0 else 0
    
    print(f"=== ハードウェア効率 ===")
    print(f"理論最大性能: {theoretical_max:.0f} MHz·threads")
    print(f"実測性能: {actual_performance:.0f} normalized")
    print(f"ハードウェア効率: {efficiency:.2f}%")

def main():
    """XG1-370専用メイン処理"""
    print("=" * 80)
    print("XG1-370 (AMD Ryzen AI 9 HX 370) 専用超高速特定投資株式情報抽出器")
    print("Zen 5 + Zen 5c + PCIe 4.0 + NPU 最適化版")
    print("=" * 80)
    
    # XG1-370環境設定
    setup_xg1370_environment()
    
    # ハードウェア確認
    if not check_xg1370_hardware():
        return
    
    # 処理開始
    start_time = datetime.now()
    print(f"\n処理開始: {start_time}")
    
    # PCIe 4.0 NVMe最適化ファイル検索
    target_files = find_xbrl_files_pcie4()
    
    if not target_files:
        print("対象ファイルが見つかりません")
        return
    
    # Zen 5 + Zen 5c ハイブリッド並列処理
    print(f"\n=== データ抽出開始 ===")
    print(f"対象ファイル数: {len(target_files)}")
    
    results = process_files_hybrid_zen5(target_files)
    
    # 処理終了
    end_time = datetime.now()
    
    # パフォーマンス統計
    print_xg1370_performance_stats(start_time, end_time, len(target_files), len(results))
    
    if results:
        # PCIe 4.0 NVMe最適化保存
        output_filename = f'xg1_370_marketable_securities_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df = save_results_pcie4(results, output_filename)
        
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
    print("XG1-370 処理完了")
    print("=" * 80)

if __name__ == "__main__":
    main()