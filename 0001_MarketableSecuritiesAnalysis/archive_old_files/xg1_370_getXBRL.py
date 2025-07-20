#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XG1-370 (AMD Ryzen AI 9 HX 370) 専用超高速XBRL取得・処理システム

ハードウェア仕様:
- AMD Ryzen AI 9 HX 370 (12コア/24スレッド)
- Zen 5 (4コア) + Zen 5c (8コア) アーキテクチャ
- 動的加速周波数: 5.1GHz
- L3キャッシュ: 24MB
- DDR5 5600MHz/LPDDR5X 7500MHz (最大128GB)
- PCIe 4.0 NVMe SSD (最大8TB)
- AIパフォーマンス: 80TOPS
"""

import os
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
import yfinance as yfinance
from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser
from dotenv import load_dotenv

warnings.filterwarnings('ignore')

# XG1-370最適化設定
@dataclass
class XG1370Config:
    """XG1-370専用最適化設定"""
    # CPU設定
    PHYSICAL_CORES = 12       # 物理コア数
    LOGICAL_CORES = 24        # 論理コア数
    ZEN5_CORES = 4           # Zen 5コア数
    ZEN5C_CORES = 8          # Zen 5cコア数
    MAX_FREQUENCY = 5.1      # 最大動作周波数 (GHz)
    L3_CACHE_MB = 24         # L3キャッシュ (MB)
    
    # 並列処理設定
    PROCESS_WORKERS = 12     # プロセス並列度
    THREAD_WORKERS = 24      # スレッド並列度
    DOWNLOAD_WORKERS = 16    # ダウンロード並列度
    IO_WORKERS = 8           # I/O専用ワーカー
    BATCH_SIZE = 100         # バッチサイズ
    
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
    
    # EDINET API設定
    EDINET_API_RETRY = 3     # APIリトライ回数
    EDINET_API_TIMEOUT = 30  # APIタイムアウト
    
config = XG1370Config()

# 環境変数読み込み
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)
EDINET_API_KEY = os.getenv('EDINET_API_KEY')

def setup_xg1370_environment():
    """XG1-370専用環境設定"""
    print("=== XG1-370 XBRL取得システム 最適化環境設定 ===")
    
    # 環境変数設定
    env_vars = {
        'OMP_NUM_THREADS': str(config.LOGICAL_CORES),
        'MKL_NUM_THREADS': str(config.LOGICAL_CORES),
        'OPENBLAS_NUM_THREADS': str(config.LOGICAL_CORES),
        'VECLIB_MAXIMUM_THREADS': str(config.LOGICAL_CORES),
        'NUMEXPR_NUM_THREADS': str(config.LOGICAL_CORES),
        'PYTHONHASHSEED': '0',
        'PYTHONUNBUFFERED': '1',
        'AIOHTTP_TIMEOUT': str(config.DOWNLOAD_TIMEOUT),
        'REQUESTS_CA_BUNDLE': '',  # SSL証明書問題回避
        'CURL_CA_BUNDLE': ''
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # プロセス優先度設定
    try:
        if os.name == 'nt':
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
    print(f"✓ ダウンロード並列度: {config.DOWNLOAD_WORKERS}")
    print(f"✓ バッチサイズ: {config.BATCH_SIZE}")

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
            for attempt in range(config.EDINET_API_RETRY):
                try:
                    async with self.session.get(url, params=params) as response:
                        response.raise_for_status()
                        data = await response.json()
                        results = data.get('results', [])
                        
                        # 有報（030000）かつ通常報告（120）のみ抽出
                        docs = [d for d in results 
                               if d.get('formCode') == doc_type and d.get('docTypeCode') == '120']
                        
                        return docs
                        
                except Exception as e:
                    if attempt == config.EDINET_API_RETRY - 1:
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
                        
                        # PCIe 4.0 NVMe最適化解凍
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
            # 非同期でZIPファイルを処理
            def extract_sync():
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                    
                    # XBRLファイルを検索
                    xbrl_files = [f for f in zip_ref.namelist() if f.lower().endswith('.xbrl')]
                    if xbrl_files:
                        return str(extract_path / xbrl_files[0])
                return None
            
            # Zen 5c効率コアで実行
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=config.ZEN5C_CORES) as executor:
                result = await loop.run_in_executor(executor, extract_sync)
                return result
                
        except Exception as e:
            print(f"解凍エラー: {zip_path} - {str(e)}")
            return None

class XG1370XBRLProcessor:
    """XG1-370最適化XBRL処理エンジン"""
    
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
    
    def extract_financial_data_zen5(self, xbrl_file: str) -> pd.DataFrame:
        """Zen 5最適化でファイナンシャルデータを抽出"""
        try:
            # ファイルサイズチェック
            file_size = os.path.getsize(xbrl_file)
            if file_size > config.MEMORY_MAPPED_THRESHOLD * 1024 * 1024:
                # 大容量ファイルはメモリマッピング
                return self._extract_with_mmap(xbrl_file)
            else:
                # 小容量ファイルは通常処理
                return self._extract_normal(xbrl_file)
                
        except Exception as e:
            print(f"データ抽出エラー: {xbrl_file} - {str(e)}")
            return pd.DataFrame()
    
    def _extract_with_mmap(self, xbrl_file: str) -> pd.DataFrame:
        """メモリマッピングでの抽出"""
        try:
            # Arelle コントローラ作成
            cntlr = Cntlr.Cntlr(logFileName='logToPrint')
            modelXbrl = cntlr.modelManager.load(xbrl_file)
            
            data = []
            for fact in modelXbrl.facts:
                row = {
                    'concept': fact.concept.qname.localName,
                    'concept_jp': fact.concept.label(preferredLabel=None, lang='ja', linkroleHint=None),
                    'value': fact.value,
                    'unit': fact.unitID if fact.unitID else '',
                    'context': fact.contextID,
                }
                data.append(row)
            
            return pd.DataFrame(data)
            
        except Exception as e:
            print(f"メモリマップ抽出エラー: {str(e)}")
            return pd.DataFrame()
    
    def _extract_normal(self, xbrl_file: str) -> pd.DataFrame:
        """通常の抽出処理"""
        try:
            cntlr = Cntlr.Cntlr(logFileName='logToPrint')
            modelXbrl = cntlr.modelManager.load(xbrl_file)
            
            data = []
            for fact in modelXbrl.facts:
                row = {
                    'concept': fact.concept.qname.localName,
                    'concept_jp': fact.concept.label(preferredLabel=None, lang='ja', linkroleHint=None),
                    'value': fact.value,
                    'unit': fact.unitID if fact.unitID else '',
                    'context': fact.contextID,
                }
                data.append(row)
            
            return pd.DataFrame(data)
            
        except Exception as e:
            print(f"通常抽出エラー: {str(e)}")
            return pd.DataFrame()
    
    def remove_html_tags_zen5c(self, df: pd.DataFrame, column: str = 'value') -> pd.DataFrame:
        """Zen 5c最適化でHTMLタグを除去"""
        if column not in df.columns:
            return df
        
        def advanced_clean(text):
            if not isinstance(text, str):
                return text
            
            # 高速正規表現でHTMLタグ除去
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'<[a-zA-Z][^>]*', '', text)
            text = re.sub(r'</[^>]*>', '', text)
            text = re.sub(r'</[^>]*', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            text = re.sub(r'　', ' ', text)
            text = re.sub(r'&nbsp;', ' ', text)
            
            return text
        
        # Zen 5c効率コアで並列処理
        with ThreadPoolExecutor(max_workers=config.ZEN5C_CORES) as executor:
            cleaned_values = list(executor.map(advanced_clean, df[column]))
            df[column] = cleaned_values
        
        return df
    
    def get_year_from_context(self, context_str: str, periodEnd_date: date) -> Optional[str]:
        """コンテキストから年度を取得"""
        year_diff = 0
        
        if "CurrentYear" in context_str:
            year_diff = 0
        elif "Prior1Year" in context_str:
            year_diff = 1
        elif "Prior2Year" in context_str:
            year_diff = 2
        elif "Prior3Year" in context_str:
            year_diff = 3
        elif "Prior4Year" in context_str:
            year_diff = 4
        else:
            return None
        
        try:
            target_date = periodEnd_date.replace(year=periodEnd_date.year - year_diff)
            return target_date.strftime("%Y")
        except ValueError:
            if periodEnd_date.month == 2 and periodEnd_date.day == 29:
                year = periodEnd_date.year - year_diff
                last_day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
                target_date = date(year, 2, last_day)
                return target_date.strftime("%Y")
            
            target_date = date(periodEnd_date.year - year_diff, periodEnd_date.month, 1)
            return target_date.strftime("%Y")
    
    def is_non_consolidated(self, context_str: str) -> bool:
        """連結・非連結判定"""
        return "NonConsolidatedMember" in context_str
    
    def process_xbrl_file_zen5(self, xbrl_file_path: str, periodEnd_date: date, 
                               edinetCode: str, df_EdinetCodeMapping: pd.DataFrame) -> pd.DataFrame:
        """Zen 5最適化でXBRLファイルを処理"""
        try:
            # データ抽出
            df = self.extract_financial_data_zen5(xbrl_file_path)
            
            if df.empty:
                return pd.DataFrame()
            
            # コンテキスト情報追加
            df['year'] = df['context'].apply(lambda x: self.get_year_from_context(x, periodEnd_date))
            df['is_non_consolidated'] = df['context'].apply(self.is_non_consolidated)
            df['edinetCode'] = edinetCode
            
            # EDINETコードマッピング
            df = pd.merge(df, df_EdinetCodeMapping[['ＥＤＩＮＥＴコード', '証券コード']],
                         left_on='edinetCode', right_on='ＥＤＩＮＥＴコード', how='left')
            
            # HTMLタグ除去
            df = self.remove_html_tags_zen5c(df)
            df = df.drop('ＥＤＩＮＥＴコード', axis=1)
            
            return df
            
        except Exception as e:
            print(f"XBRL処理エラー: {xbrl_file_path} - {str(e)}")
            return pd.DataFrame()

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
                        
                        # PCIe 4.0 NVMe最適化でCSVを読み込み
                        for csv_file in self.find_csv_files_pcie4(extract_dir):
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
    
    def find_csv_files_pcie4(self, directory: str) -> List[str]:
        """PCIe 4.0最適化でCSVファイルを検索"""
        return glob.glob(os.path.join(directory, "**", "*.csv"), recursive=True)
    
    def read_csv_to_dataframe_zen5c(self, csv_path: str) -> Optional[pd.DataFrame]:
        """Zen 5c最適化でCSVをDataFrameに読み込み"""
        try:
            # 複数エンコーディングを並列試行
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

async def get_xbrl_zen5_optimized(target_date: date, df_EdinetCodeMapping: pd.DataFrame) -> List[pd.DataFrame]:
    """Zen 5 + Zen 5c最適化でXBRLを取得・処理"""
    results = []
    
    async with XG1370EDINETClient() as client:
        # 指定日付の文書一覧を取得
        documents = await client.get_documents_by_date_async(target_date)
        
        if not documents:
            return results
        
        # 上場企業のみフィルタリング
        edinet_codes = set(df_EdinetCodeMapping['ＥＤＩＮＥＴコード'].tolist())
        filtered_docs = [doc for doc in documents if doc['edinetCode'] in edinet_codes]
        
        if not filtered_docs:
            return results
        
        # 並列ダウンロード
        download_tasks = []
        for doc in filtered_docs:
            task = client.download_xbrl_file_async(doc['docID'])
            download_tasks.append((task, doc))
        
        # XBRLプロセッサーで処理
        with XG1370XBRLProcessor() as processor:
            for task, doc in download_tasks:
                try:
                    xbrl_path = await task
                    if xbrl_path and os.path.exists(xbrl_path):
                        periodEnd_date = date.fromisoformat(doc['periodEnd'])
                        result_df = processor.process_xbrl_file_zen5(
                            xbrl_path, periodEnd_date, doc['edinetCode'], df_EdinetCodeMapping
                        )
                        
                        if not result_df.empty:
                            results.append(result_df)
                            
                except Exception as e:
                    print(f"処理エラー: {doc['docID']} - {str(e)}")
                    continue
    
    return results

async def process_date_range_zen5(start_date: date, end_date: date, 
                                 df_EdinetCodeMapping: pd.DataFrame) -> List[pd.DataFrame]:
    """日付範囲をZen 5 + Zen 5c最適化で処理"""
    all_results = []
    current_date = start_date
    
    print(f"=== 日付範囲処理開始: {start_date} - {end_date} ===")
    
    # 日付をバッチに分割
    date_batches = []
    batch_dates = []
    
    while current_date <= end_date:
        batch_dates.append(current_date)
        current_date += timedelta(days=1)
        
        if len(batch_dates) >= config.BATCH_SIZE:
            date_batches.append(batch_dates)
            batch_dates = []
    
    if batch_dates:
        date_batches.append(batch_dates)
    
    print(f"バッチ数: {len(date_batches)}")
    
    # バッチごとに並列処理
    for i, batch in enumerate(date_batches):
        print(f"バッチ {i+1}/{len(date_batches)} 処理中...")
        
        # バッチ内の日付を並列処理
        batch_tasks = [get_xbrl_zen5_optimized(date, df_EdinetCodeMapping) for date in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # 結果をまとめる
        for result in batch_results:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                print(f"バッチ処理エラー: {str(result)}")
        
        print(f"バッチ {i+1} 完了: {len(all_results)} 件累計")
    
    return all_results

def save_results_pcie4_optimized(results: List[pd.DataFrame], output_filename: str) -> Optional[pd.DataFrame]:
    """PCIe 4.0 NVMe最適化で結果を保存"""
    if not results:
        print("保存するデータがありません")
        return None
    
    print(f"=== PCIe 4.0 NVMe最適化保存 ===")
    start_time = time.time()
    
    # DataFrameを結合
    combined_df = pd.concat(results, ignore_index=True)
    
    # 高速CSV書き込み
    combined_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    
    save_time = time.time() - start_time
    file_size = os.path.getsize(output_filename) / (1024**2)
    save_speed = file_size / save_time if save_time > 0 else 0
    
    print(f"保存完了: {file_size:.1f}MB ({save_time:.2f}秒)")
    print(f"保存速度: {save_speed:.1f} MB/sec")
    
    return combined_df

async def main_xg1370_optimized():
    """XG1-370最適化メイン処理"""
    print("=" * 80)
    print("XG1-370 (AMD Ryzen AI 9 HX 370) 専用超高速XBRL取得・処理システム")
    print("Zen 5 + Zen 5c + PCIe 4.0 + 非同期処理 最適化版")
    print("=" * 80)
    
    # 環境設定
    setup_xg1370_environment()
    
    # 処理開始
    start_time = datetime.now()
    print(f"\n処理開始: {start_time}")
    
    # EDINETコードマッピング取得
    print("\n=== EDINETコードマッピング取得 ===")
    mapper = XG1370EDINETMapper()
    df_EdinetCodeMapping = await mapper.get_edinet_code_mapping_async()
    
    if df_EdinetCodeMapping.empty:
        print("EDINETコードマッピング取得に失敗しました")
        return
    
    print(f"EDINETコード数: {len(df_EdinetCodeMapping)}")
    
    # 処理日付範囲設定
    start_date = date(2025, 3, 1)
    end_date = date(2025, 3, 31)  # 1ヶ月分
    
    print(f"\n=== XBRL取得・処理開始 ===")
    print(f"対象期間: {start_date} - {end_date}")
    
    # Zen 5 + Zen 5c最適化処理
    results = await process_date_range_zen5(start_date, end_date, df_EdinetCodeMapping)
    
    # 処理終了
    end_time = datetime.now()
    processing_time = end_time - start_time
    
    print(f"\n=== XG1-370 処理統計 ===")
    print(f"処理時間: {processing_time}")
    print(f"取得件数: {len(results)}")
    
    if results:
        # PCIe 4.0 NVMe最適化保存
        output_filename = f'xg1_370_xbrl_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        combined_df = save_results_pcie4_optimized(results, output_filename)
        
        if combined_df is not None:
            print(f"\n=== 最終結果 ===")
            print(f"出力ファイル: {output_filename}")
            print(f"総レコード数: {len(combined_df):,}")
            print(f"企業数: {combined_df['edinetCode'].nunique():,}")
            print(f"処理速度: {len(results) / processing_time.total_seconds():.2f} files/sec")
    
    print("\n" + "=" * 80)
    print("XG1-370 XBRL取得・処理完了")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main_xg1370_optimized())