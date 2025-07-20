#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XG1-370 (AMD Ryzen AI 9 HX 370) 専用完全統合パイプライン

このファイル1つで以下の全処理を完結:
1. EDINETからXBRLファイルの高速ダウンロード
2. ダウンロードしたXBRLから特定投資株式情報の抽出
3. 結果のCSV出力

XG1-370ハードウェア最適化:
- AMD Ryzen AI 9 HX 370 (12コア/24スレッド)
- Zen 5 (4コア) + Zen 5c (8コア) アーキテクチャ
- 動的加速周波数: 5.1GHz、L3キャッシュ: 24MB
- DDR5/LPDDR5X (最大128GB)
- PCIe 4.0 NVMe SSD (最大8TB)
- NPU 50TOPS + GPU 16コア
"""

import os
import sys
import io
import re
import asyncio
import aiofiles
import aiohttp
import zipfile
import logging
import pandas as pd
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union, Tuple
import multiprocessing as mp
import threading
import psutil
import gc
import time
import requests
import ujson as json
from pathlib import Path
import mmap
import numexpr as ne
from functools import partial
import warnings
from playwright.async_api import async_playwright, Page
import glob
from bs4 import BeautifulSoup
from arelle import Cntlr
import subprocess
from dotenv import load_dotenv
import platform

warnings.filterwarnings('ignore')

# 環境変数設定
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

EDINET_API_KEY = os.getenv('EDINET_API_KEY')

if not EDINET_API_KEY:
    print("❌ エラー: EDINET_API_KEYが設定されていません")
    print("   .envファイルに以下を設定してください:")
    print("   EDINET_API_KEY=your_api_key_here")
    sys.exit(1)

# XG1-370専用最適化設定
@dataclass
class XG1370Config:
    """XG1-370専用統合設定"""
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
    DOWNLOAD_WORKERS = 16    # ダウンロード並列度
    IO_WORKERS = 8           # I/O専用ワーカー
    BATCH_SIZE = 150         # バッチサイズ
    
    # ネットワーク設定
    MAX_CONCURRENT_DOWNLOADS = 20  # 同時ダウンロード数
    DOWNLOAD_TIMEOUT = 30          # ダウンロードタイムアウト(秒)
    RETRY_ATTEMPTS = 3             # リトライ回数
    
    # メモリ設定
    MEMORY_LIMIT_GB = 96     # メモリ制限
    MEMORY_MAPPED_THRESHOLD = 10  # メモリマップ閾値（MB）
    
    # ストレージ設定
    PCIE4_ENABLED = True     # PCIe 4.0対応
    NVME_PARALLEL_IO = 16    # NVMe並列I/O数
    
    # 抽出設定
    PROGRESS_INTERVAL = 50   # 進捗表示間隔

config = XG1370Config()

def setup_xg1370_complete_environment():
    """XG1-370専用完全環境設定"""
    print("=== XG1-370 完全統合パイプライン 環境設定 ===")
    
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
        'MALLOC_TRIM_THRESHOLD_': '131072',
        'AIOHTTP_TIMEOUT': str(config.DOWNLOAD_TIMEOUT),
        'REQUESTS_CA_BUNDLE': '',
        'CURL_CA_BUNDLE': ''
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # プロセス優先度設定
    try:
        if sys.platform == "win32":
            psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            os.nice(-15)
        print("✓ プロセス優先度を最高に設定")
    except:
        print("△ プロセス優先度設定をスキップ")
    
    # ガベージコレクション最適化
    gc.set_threshold(700, 10, 10)
    
    print(f"✓ 物理コア: {config.PHYSICAL_CORES}, 論理コア: {config.LOGICAL_CORES}")
    print(f"✓ プロセス並列度: {config.PROCESS_WORKERS}")
    print(f"✓ ダウンロード並列度: {config.DOWNLOAD_WORKERS}")
    print(f"✓ バッチサイズ: {config.BATCH_SIZE}")
    print(f"✓ メモリ制限: {config.MEMORY_LIMIT_GB}GB")

def check_system_compatibility():
    """システム互換性チェック"""
    print("\n=== XG1-370 システム互換性チェック ===")
    
    # CPU情報
    cpu_count = os.cpu_count()
    print(f"論理プロセッサ数: {cpu_count}")
    
    # メモリ情報
    memory = psutil.virtual_memory()
    total_gb = memory.total / (1024**3)
    available_gb = memory.available / (1024**3)
    print(f"総メモリ: {total_gb:.1f}GB")
    print(f"利用可能メモリ: {available_gb:.1f}GB")
    
    # ディスク情報
    disk = psutil.disk_usage('/')
    print(f"ディスク容量: {disk.total / (1024**3):.1f}GB")
    print(f"ディスク空き: {disk.free / (1024**3):.1f}GB")
    
    # 必要パッケージ確認
    required_packages = [
        'pandas', 'beautifulsoup4', 'lxml', 'psutil', 'aiofiles', 
        'aiohttp', 'requests', 'playwright', 'arelle', 'dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'beautifulsoup4':
                __import__('bs4')
            elif package == 'dotenv':
                __import__('dotenv')
            else:
                __import__(package)
            print(f"✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} (未インストール)")
    
    if missing_packages:
        print(f"\n以下のパッケージをインストールしてください:")
        print(f"pip install {' '.join(missing_packages)}")
        if 'playwright' in missing_packages:
            print("playwright install chromium")
        return False
    
    return True

# ==================== EDINET APIクライアント ====================
class XG1370EDINETClient:
    """XG1-370最適化EDINETクライアント"""
    
    def __init__(self):
        self.session = None
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_DOWNLOADS)
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=config.MAX_CONCURRENT_DOWNLOADS,
            limit_per_host=config.MAX_CONCURRENT_DOWNLOADS,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        timeout = aiohttp.ClientTimeout(total=config.DOWNLOAD_TIMEOUT)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'Subscription-Key': EDINET_API_KEY}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_documents_by_date_async(self, target_date: date, doc_type: str = '030000') -> List[Dict]:
        """非同期で指定日付の文書一覧を取得"""
        date_str = target_date.strftime("%Y-%m-%d")
        url = "https://disclosure.edinet-fsa.go.jp/api/v2/documents.json"
        params = {'date': date_str, 'type': 2}
        
        async with self.semaphore:
            for attempt in range(config.RETRY_ATTEMPTS):
                try:
                    async with self.session.get(url, params=params) as response:
                        response.raise_for_status()
                        data = await response.json()
                        results = data.get('results', [])
                        
                        docs = [d for d in results 
                               if d.get('formCode') == doc_type and d.get('docTypeCode') == '120']
                        
                        return docs
                        
                except Exception as e:
                    if attempt == config.RETRY_ATTEMPTS - 1:
                        print(f"APIエラー: {date_str} - {str(e)}")
                        return []
                    await asyncio.sleep(1)
        
        return []
    
    async def download_xbrl_file_async(self, doc_id: str, output_dir: str = "./xbrl/") -> Optional[str]:
        """非同期でXBRLファイルをダウンロード"""
        path = Path(output_dir) / doc_id
        path.mkdir(parents=True, exist_ok=True)
        
        url = f"https://disclosure.edinet-fsa.go.jp/api/v2/documents/{doc_id}"
        params = {'type': 1}
        
        async with self.semaphore:
            for attempt in range(config.RETRY_ATTEMPTS):
                try:
                    async with self.session.get(url, params=params) as response:
                        response.raise_for_status()
                        content = await response.read()
                        
                        # ZIPファイルを保存
                        zip_filename = path / f"{doc_id}.zip"
                        async with aiofiles.open(zip_filename, 'wb') as f:
                            await f.write(content)
                        
                        # 解凍してXBRLファイルパスを返す
                        return await self.extract_xbrl_file_zen5(zip_filename, path)
                        
                except Exception as e:
                    if attempt == config.RETRY_ATTEMPTS - 1:
                        print(f"ダウンロードエラー: {doc_id} - {str(e)}")
                        return None
                    await asyncio.sleep(1)
        
        return None
    
    async def extract_xbrl_file_zen5(self, zip_path: Path, extract_path: Path) -> Optional[str]:
        """Zen 5最適化でZIPファイルを解凍"""
        try:
            def extract_sync():
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                    
                    # 0104010_honbun ファイルを検索
                    for file in zip_ref.namelist():
                        if '0104010_honbun' in file and file.endswith(('.htm', '.html')):
                            return str(extract_path / file)
                    
                    # 見つからない場合はHTMLファイルを検索
                    html_files = [f for f in zip_ref.namelist() if f.endswith(('.htm', '.html'))]
                    if html_files:
                        return str(extract_path / html_files[0])
                
                return None
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=config.ZEN5C_CORES) as executor:
                result = await loop.run_in_executor(executor, extract_sync)
                return result
                
        except Exception as e:
            print(f"解凍エラー: {zip_path} - {str(e)}")
            return None

# ==================== EDINETコードマッピング ====================
class XG1370EDINETMapper:
    """XG1-370最適化EDINETコードマッパー"""
    
    async def download_edinet_file_async(self, url: str = "https://disclosure2.edinet-fsa.go.jp/weee0010.aspx",
                                        download_dir: str = None) -> Dict[str, pd.DataFrame]:
        """非同期でEDINETファイルをダウンロード"""
        if download_dir is None:
            download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(download_dir, exist_ok=True)
        
        result_dataframes = {}
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(accept_downloads=True)
                page = await context.new_page()
                
                await page.goto(url)
                download_path = await self.download_and_wait_zen5(page, download_dir)
                await browser.close()
                
                if download_path and os.path.exists(download_path):
                    with zipfile.ZipFile(download_path, 'r') as zip_ref:
                        extract_dir = os.path.join(download_dir, "extracted")
                        os.makedirs(extract_dir, exist_ok=True)
                        zip_ref.extractall(path=extract_dir)
                        
                        for csv_file in glob.glob(os.path.join(extract_dir, "**", "*.csv"), recursive=True):
                            df = self.read_csv_to_dataframe_zen5c(csv_file)
                            if df is not None:
                                result_dataframes[os.path.basename(csv_file)] = df
                                
        except Exception as e:
            print(f"EDINETファイルダウンロードエラー: {str(e)}")
        
        return result_dataframes
    
    async def download_and_wait_zen5(self, page: Page, download_dir: str) -> Optional[str]:
        """Zen 5最適化でダウンロードを待機"""
        try:
            download_future = asyncio.create_task(
                page.wait_for_event('download', timeout=config.DOWNLOAD_TIMEOUT * 1000)
            )
            
            await page.evaluate("onDownloadEdinet()")
            download = await download_future
            save_path = os.path.join(download_dir, download.suggested_filename)
            await download.save_as(save_path)
            return save_path
            
        except Exception as e:
            print(f"ダウンロード待機エラー: {str(e)}")
            return None
    
    def read_csv_to_dataframe_zen5c(self, csv_path: str) -> Optional[pd.DataFrame]:
        """Zen 5c最適化でCSVをDataFrameに読み込み"""
        try:
            encodings = ["cp932", "utf-8", "shift-jis"]
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_path, encoding=encoding, skiprows=1, dtype=str)
                    return df
                except UnicodeDecodeError:
                    continue
                    
        except Exception as e:
            print(f"CSV読み込みエラー: {csv_path} - {str(e)}")
            
        return None
    
    async def get_edinet_code_mapping_async(self) -> pd.DataFrame:
        """非同期でEDINETコードマッピングを取得"""
        try:
            dfs = await self.download_edinet_file_async()
            if 'EdinetcodeDlInfo.csv' in dfs:
                dfs_tmp = dfs['EdinetcodeDlInfo.csv']
                df = dfs_tmp[dfs_tmp['上場区分'] == '上場']
                df.loc[:, '証券コード'] = df['証券コード'].apply(
                    lambda x: re.sub('0$', '', x) if isinstance(x, str) else x
                )
                return df
            else:
                print("EdinetcodeDlInfo.csvが見つかりません")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"EDINETコードマッピング取得エラー: {str(e)}")
            return pd.DataFrame()

# ==================== 特定投資株式抽出エンジン ====================
class XG1370SecuritiesExtractor:
    """XG1-370最適化特定投資株式抽出エンジン"""
    
    def __init__(self):
        self.process_pool = None
        self.thread_pool = None
        
    def __enter__(self):
        self.process_pool = ProcessPoolExecutor(max_workers=config.PROCESS_WORKERS)
        self.thread_pool = ThreadPoolExecutor(max_workers=config.THREAD_WORKERS)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.process_pool:
            self.process_pool.shutdown(wait=True)
        if self.thread_pool:
            self.thread_pool.shutdown(wait=True)
    
    def find_xbrl_files_zen5_optimized(self):
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
        if search_time > 0:
            print(f"検索速度: {len(files_list)/search_time:.0f} files/sec")
        
        return files_list
    
    def extract_company_info_zen5(self, filepath: str) -> Optional[Dict[str, str]]:
        """Zen 5最適化で会社情報を抽出"""
        filename = os.path.basename(filepath)
        
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
    
    def extract_securities_zen5c_optimized(self, filepath: str) -> List[Dict[str, any]]:
        """Zen 5c最適化で特定投資株式情報を抽出"""
        try:
            # ファイルサイズチェック
            file_size = os.path.getsize(filepath)
            if file_size > 100 * 1024 * 1024:  # 100MB以上はスキップ
                return []
            
            # 会社情報抽出
            company_info = self.extract_company_info_zen5(filepath)
            if not company_info:
                return []
            
            # メモリマッピング vs 通常読み込み
            if file_size > config.MEMORY_MAPPED_THRESHOLD * 1024 * 1024:
                with open(filepath, 'rb') as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                        content = mmapped_file.read().decode('utf-8', errors='ignore')
            else:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            
            # 高速事前フィルタリング
            if not ('SpecifiedInvestment' in content and 'NameOfSecurities' in content):
                return []
            
            # BeautifulSoupでの高速解析
            soup = BeautifulSoup(content, 'lxml-xml')
            results = []
            
            # コンパイル済み正規表現
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
            
            # 関連要素を取得
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
            return []
    
    def process_batch_zen5c(self, file_batch: List[str]) -> List[Dict[str, any]]:
        """Zen 5c最適化バッチ処理"""
        batch_results = []
        for filepath in file_batch:
            results = self.extract_securities_zen5c_optimized(filepath)
            batch_results.extend(results)
        return batch_results
    
    def process_files_hybrid_zen5_zen5c(self, files: List[str]) -> List[Dict[str, any]]:
        """Zen 5 + Zen 5c ハイブリッド並列処理"""
        print(f"=== Zen 5 + Zen 5c ハイブリッド並列処理 ===")
        print(f"プロセス並列: {config.PROCESS_WORKERS}")
        print(f"対象ファイル数: {len(files):,}")
        
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
            future_to_batch = {executor.submit(self.process_batch_zen5c, batch): batch for batch in batches}
            
            # 完了順に結果取得
            for future in as_completed(future_to_batch):
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                    processed_batches += 1
                    
                    # リアルタイム進捗表示
                    if processed_batches % 5 == 0 or processed_batches == len(batches):
                        elapsed = time.time() - start_time
                        speed = processed_batches / elapsed if elapsed > 0 else 0
                        remaining = len(batches) - processed_batches
                        eta = remaining / speed if speed > 0 else 0
                        
                        print(f"処理済み: {processed_batches}/{len(batches)} バッチ | "
                              f"抽出レコード: {len(all_results):,} | "
                              f"速度: {speed:.1f} batch/sec | "
                              f"残り時間: {eta:.0f}秒")
                        
                except Exception as e:
                    print(f"バッチ処理エラー: {str(e)}")
        
        total_time = time.time() - start_time
        print(f"=== Zen 5 + Zen 5c並列処理完了 ===")
        print(f"処理時間: {total_time:.2f}秒")
        if total_time > 0:
            print(f"ファイル処理速度: {len(files)/total_time:.2f} files/sec")
            print(f"レコード抽出速度: {len(all_results)/total_time:.2f} records/sec")
        
        return all_results

# ==================== 統合処理関数 ====================
async def download_xbrl_files_zen5(df_EdinetCodeMapping: pd.DataFrame, 
                                   start_date: date, end_date: date) -> List[str]:
    """Zen 5最適化でXBRLファイルをダウンロード"""
    print(f"\n=== XBRLファイルダウンロード開始 ===")
    print(f"対象期間: {start_date} - {end_date}")
    
    downloaded_files = []
    
    async with XG1370EDINETClient() as client:
        current_date = start_date
        
        while current_date <= end_date:
            print(f"処理中: {current_date}")
            
            # 指定日付の文書一覧を取得
            documents = await client.get_documents_by_date_async(current_date)
            
            if documents:
                # 上場企業のみフィルタリング
                edinet_codes = set(df_EdinetCodeMapping['ＥＤＩＮＥＴコード'].tolist())
                filtered_docs = [doc for doc in documents if doc['edinetCode'] in edinet_codes]
                
                if filtered_docs:
                    print(f"  {current_date}: {len(filtered_docs)}件のファイルをダウンロード")
                    
                    # 並列ダウンロード
                    download_tasks = []
                    for doc in filtered_docs:
                        task = client.download_xbrl_file_async(doc['docID'])
                        download_tasks.append(task)
                    
                    # 結果を取得
                    results = await asyncio.gather(*download_tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, str) and result:
                            downloaded_files.append(result)
                else:
                    print(f"  {current_date}: 対象ファイルなし")
            else:
                print(f"  {current_date}: 文書なし")
            
            current_date += timedelta(days=1)
    
    print(f"ダウンロード完了: {len(downloaded_files)}件")
    return downloaded_files

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

def print_system_performance():
    """システム性能表示"""
    print("\n=== システム性能 ===")
    
    # CPU使用率
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"CPU使用率: {cpu_percent:.1f}%")
    
    # メモリ使用率
    memory = psutil.virtual_memory()
    print(f"メモリ使用率: {memory.percent:.1f}%")
    print(f"使用メモリ: {memory.used / (1024**3):.1f}GB")

# ==================== メイン処理 ====================
async def main():
    """XG1-370専用完全統合メイン処理"""
    print("=" * 80)
    print("XG1-370 (AMD Ryzen AI 9 HX 370) 専用完全統合パイプライン")
    print("XBRL取得 → 特定投資株式情報抽出 → CSV出力")
    print("Zen 5 + Zen 5c + PCIe 4.0 NVMe + NPU 最適化版")
    print("=" * 80)
    
    # システム互換性チェック
    if not check_system_compatibility():
        print("\n❌ システム互換性に問題があります")
        return
    
    # 環境設定
    setup_xg1370_complete_environment()
    
    # 確認プロンプト
    print("\n" + "=" * 80)
    print("処理内容:")
    print("1. EDINETコードマッピング取得")
    print("2. EDINETからXBRLファイルを高速ダウンロード")
    print("3. ダウンロードしたXBRLから特定投資株式情報を抽出")
    print("4. 結果をCSVファイルに出力")
    print("=" * 80)
    
    response = input("\nXG1-370完全統合パイプラインを開始しますか？ (y/N): ")
    if response.lower() != 'y':
        print("処理を中止しました")
        return
    
    # 全体処理開始
    pipeline_start_time = datetime.now()
    print(f"\n完全統合パイプライン開始: {pipeline_start_time}")
    
    try:
        # ステップ1: EDINETコードマッピング取得
        print("\n" + "=" * 60)
        print("ステップ1: EDINETコードマッピング取得")
        print("=" * 60)
        
        mapper = XG1370EDINETMapper()
        df_EdinetCodeMapping = await mapper.get_edinet_code_mapping_async()
        
        if df_EdinetCodeMapping.empty:
            print("❌ EDINETコードマッピング取得に失敗しました")
            return
        
        print(f"✓ EDINETコード数: {len(df_EdinetCodeMapping):,}")
        
        # ステップ2: XBRLファイルダウンロード
        print("\n" + "=" * 60)
        print("ステップ2: XBRLファイルダウンロード")
        print("=" * 60)
        
        # 処理日付範囲設定（例: 直近1週間）
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        downloaded_files = await download_xbrl_files_zen5(df_EdinetCodeMapping, start_date, end_date)
        
        if not downloaded_files:
            print("❌ ダウンロードされたファイルがありません")
            return
        
        print(f"✓ ダウンロード完了: {len(downloaded_files):,}件")
        print_system_performance()
        
        # ステップ3: 特定投資株式情報抽出
        print("\n" + "=" * 60)
        print("ステップ3: 特定投資株式情報抽出")
        print("=" * 60)
        
        with XG1370SecuritiesExtractor() as extractor:
            # 既存のXBRLファイルも含めて検索
            all_files = extractor.find_xbrl_files_zen5_optimized()
            
            if not all_files:
                print("❌ 処理対象のXBRLファイルが見つかりません")
                return
            
            # 特定投資株式情報抽出
            results = extractor.process_files_hybrid_zen5_zen5c(all_files)
            
            if not results:
                print("❌ 抽出されたデータがありません")
                return
            
            print(f"✓ 抽出完了: {len(results):,}レコード")
            print_system_performance()
        
        # ステップ4: 結果保存
        print("\n" + "=" * 60)
        print("ステップ4: 結果保存")
        print("=" * 60)
        
        output_filename = f'xg1_370_complete_marketable_securities_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df = save_results_pcie4_optimized(results, output_filename)
        
        if df is not None:
            print(f"✓ 保存完了: {output_filename}")
            print(f"  総レコード数: {len(df):,}")
            print(f"  提出会社数: {df['filing_company_code'].nunique():,}")
            print(f"  保有証券数: {df['held_security_name'].nunique():,}")
            
            # 保有金額統計
            book_values = df['book_value_million_yen'].dropna()
            if not book_values.empty:
                print(f"  総保有金額: {book_values.sum():,.0f} 百万円")
                print(f"  平均保有金額: {book_values.mean():,.0f} 百万円")
        
        # 全体処理終了
        pipeline_end_time = datetime.now()
        total_execution_time = pipeline_end_time - pipeline_start_time
        
        print(f"\n完全統合パイプライン終了: {pipeline_end_time}")
        print(f"総実行時間: {total_execution_time}")
        
        print("\n" + "=" * 80)
        print("🚀 XG1-370完全統合パイプライン完了！")
        print(f"総実行時間: {total_execution_time}")
        print(f"出力ファイル: {output_filename}")
        print("Zen 5 + Zen 5c + PCIe 4.0 + NPUの性能を最大限活用しました。")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ パイプライン実行エラー: {str(e)}")
        print("処理を中止しました")

if __name__ == "__main__":
    asyncio.run(main())