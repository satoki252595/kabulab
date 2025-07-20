#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XG1-370 (AMD Ryzen AI 9 HX 370) 専用統合パイプライン実行スクリプト

このスクリプトは以下の処理を順次実行します：
1. run_xg1_370_getXBRL.py - XBRLファイルの取得
2. xg1_370_fast_extractor.py - 特定投資株式情報の抽出

XG1-370ハードウェア最適化:
- AMD Ryzen AI 9 HX 370 (12コア/24スレッド)
- Zen 5 + Zen 5c ハイブリッド並列処理
- PCIe 4.0 NVMe SSD最適化
- DDR5/LPDDR5X高速メモリ活用
"""

import os
import sys
import subprocess
import time
import psutil
from datetime import datetime
import platform
import shutil

def check_system_requirements():
    """システム要件チェック"""
    print("=== XG1-370 システム要件チェック ===")
    
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
    
    # 要件チェック
    requirements_met = True
    
    if cpu_count < 8:
        print("⚠ CPU: 8コア以上を推奨")
        requirements_met = False
    
    if total_gb < 16:
        print("⚠ メモリ: 16GB以上を推奨")
        requirements_met = False
    
    if disk.free / (1024**3) < 50:
        print("⚠ ディスク空き: 50GB以上を推奨")
        requirements_met = False
    
    if requirements_met:
        print("✓ システム要件を満たしています")
    
    return requirements_met

def check_required_files():
    """必要なファイルの存在確認"""
    print("\n=== 必要ファイル確認 ===")
    
    base_dir = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis"
    required_files = [
        "run_xg1_370_getXBRL.py",
        "xg1_370_getXBRL.py",
        "xg1_370_fast_extractor.py",
        "install_requirements.py"
    ]
    
    missing_files = []
    for file in required_files:
        file_path = os.path.join(base_dir, file)
        if os.path.exists(file_path):
            print(f"✓ {file}")
        else:
            print(f"✗ {file} (見つかりません)")
            missing_files.append(file)
    
    # .envファイルの確認
    env_path = os.path.join(os.path.dirname(base_dir), '.env')
    if os.path.exists(env_path):
        print("✓ .env")
    else:
        print("✗ .env (見つかりません)")
        missing_files.append(".env")
    
    return len(missing_files) == 0

def setup_environment():
    """環境設定"""
    print("\n=== 環境設定 ===")
    
    # XG1-370専用環境変数
    env_vars = {
        'OMP_NUM_THREADS': '24',
        'MKL_NUM_THREADS': '24',
        'OPENBLAS_NUM_THREADS': '24',
        'VECLIB_MAXIMUM_THREADS': '24',
        'NUMEXPR_NUM_THREADS': '24',
        'PYTHONHASHSEED': '0',
        'PYTHONUNBUFFERED': '1'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✓ {key} = {value}")
    
    # プロセス優先度設定
    try:
        if sys.platform == "win32":
            psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            os.nice(-10)
        print("✓ プロセス優先度を高く設定")
    except:
        print("△ プロセス優先度設定をスキップ")

def run_xbrl_download():
    """XBRLダウンロード処理実行"""
    print("\n" + "=" * 60)
    print("ステップ1: XBRLファイルダウンロード")
    print("=" * 60)
    
    script_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/run_xg1_370_getXBRL.py"
    
    if not os.path.exists(script_path):
        print(f"エラー: {script_path} が見つかりません")
        return False
    
    start_time = datetime.now()
    print(f"開始時刻: {start_time}")
    
    try:
        # XBRLダウンロード実行
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=False, text=True)
        
        end_time = datetime.now()
        execution_time = end_time - start_time
        
        print(f"終了時刻: {end_time}")
        print(f"実行時間: {execution_time}")
        
        if result.returncode == 0:
            print("✓ XBRLダウンロード完了")
            return True
        else:
            print(f"✗ XBRLダウンロードエラー (戻り値: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"✗ XBRLダウンロード実行エラー: {str(e)}")
        return False

def run_securities_extraction():
    """特定投資株式情報抽出処理実行"""
    print("\n" + "=" * 60)
    print("ステップ2: 特定投資株式情報抽出")
    print("=" * 60)
    
    script_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xg1_370_fast_extractor.py"
    
    if not os.path.exists(script_path):
        print(f"エラー: {script_path} が見つかりません")
        return False
    
    start_time = datetime.now()
    print(f"開始時刻: {start_time}")
    
    try:
        # 特定投資株式情報抽出実行
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=False, text=True)
        
        end_time = datetime.now()
        execution_time = end_time - start_time
        
        print(f"終了時刻: {end_time}")
        print(f"実行時間: {execution_time}")
        
        if result.returncode == 0:
            print("✓ 特定投資株式情報抽出完了")
            return True
        else:
            print(f"✗ 特定投資株式情報抽出エラー (戻り値: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"✗ 特定投資株式情報抽出実行エラー: {str(e)}")
        return False

def check_output_files():
    """出力ファイルの確認"""
    print("\n=== 出力ファイル確認 ===")
    
    base_dir = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis"
    
    # XBRLデータファイル
    xbrl_pattern = "xg1_370_xbrl_data_*.csv"
    
    # 特定投資株式データファイル
    securities_pattern = "xg1_370_fast_marketable_securities_*.csv"
    
    import glob
    
    xbrl_files = glob.glob(os.path.join(base_dir, xbrl_pattern))
    securities_files = glob.glob(os.path.join(base_dir, securities_pattern))
    
    print(f"XBRLデータファイル: {len(xbrl_files)}件")
    for file in sorted(xbrl_files)[-3:]:  # 最新3件
        file_size = os.path.getsize(file) / (1024**2)
        print(f"  - {os.path.basename(file)} ({file_size:.1f}MB)")
    
    print(f"特定投資株式データファイル: {len(securities_files)}件")
    for file in sorted(securities_files)[-3:]:  # 最新3件
        file_size = os.path.getsize(file) / (1024**2)
        print(f"  - {os.path.basename(file)} ({file_size:.1f}MB)")
    
    return len(xbrl_files) > 0 and len(securities_files) > 0

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
    
    # ディスク使用率
    disk = psutil.disk_usage('/')
    print(f"ディスク使用率: {(disk.used / disk.total) * 100:.1f}%")

def main():
    """メイン処理"""
    print("=" * 80)
    print("XG1-370 (AMD Ryzen AI 9 HX 370) 専用統合パイプライン")
    print("XBRL取得 → 特定投資株式情報抽出")
    print("Zen 5 + Zen 5c + PCIe 4.0 NVMe 最適化版")
    print("=" * 80)
    
    # システム要件チェック
    if not check_system_requirements():
        print("\n⚠ システム要件を満たしていない項目があります")
        response = input("続行しますか？ (y/N): ")
        if response.lower() != 'y':
            print("処理を中止しました")
            return
    
    # 必要ファイル確認
    if not check_required_files():
        print("\n✗ 必要なファイルが不足しています")
        return
    
    # 環境設定
    setup_environment()
    
    # 処理開始確認
    print("\n" + "=" * 80)
    print("処理内容:")
    print("1. EDINETからXBRLファイルを高速ダウンロード")
    print("2. ダウンロードしたXBRLから特定投資株式情報を抽出")
    print("3. 結果をCSVファイルに出力")
    print("=" * 80)
    
    response = input("\nXG1-370統合パイプラインを開始しますか？ (y/N): ")
    if response.lower() != 'y':
        print("処理を中止しました")
        return
    
    # 全体処理開始
    pipeline_start_time = datetime.now()
    print(f"\n統合パイプライン開始: {pipeline_start_time}")
    
    success_count = 0
    
    # ステップ1: XBRLダウンロード
    if run_xbrl_download():
        success_count += 1
        print_system_performance()
    else:
        print("❌ XBRLダウンロードに失敗しました")
        return
    
    # 少し待機（システムリソース回復）
    print("\nシステムリソース回復のため5秒待機...")
    time.sleep(5)
    
    # ステップ2: 特定投資株式情報抽出
    if run_securities_extraction():
        success_count += 1
        print_system_performance()
    else:
        print("❌ 特定投資株式情報抽出に失敗しました")
        return
    
    # 全体処理終了
    pipeline_end_time = datetime.now()
    total_execution_time = pipeline_end_time - pipeline_start_time
    
    print(f"\n統合パイプライン終了: {pipeline_end_time}")
    print(f"総実行時間: {total_execution_time}")
    
    # 出力ファイル確認
    if check_output_files():
        print("\n" + "=" * 80)
        print("🚀 XG1-370統合パイプライン完了！")
        print(f"成功したステップ: {success_count}/2")
        print(f"総実行時間: {total_execution_time}")
        print("出力ファイルを確認してください。")
        print("Zen 5 + Zen 5c + PCIe 4.0の性能を最大限活用しました。")
        print("=" * 80)
    else:
        print("\n❌ 出力ファイルの生成に問題があります")
        print("ログを確認してください")

if __name__ == "__main__":
    main()