#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XG1-370 (AMD Ryzen AI 9 HX 370) 最適化実行スクリプト

このスクリプトは以下のハードウェア仕様に最適化されています：
- AMD Ryzen AI 9 HX 370 (12コア/24スレッド)
- 5.1GHz動的加速周波数
- 24MB L3キャッシュ
- DDR5 5600MHz/LPDDR5X 7500MHz
- PCIe 4.0 NVMe SSD
- 4nm FinFET製造プロセス
"""

import os
import sys
import subprocess
import time
import psutil
from datetime import datetime

def check_system_requirements():
    """システム要件チェック"""
    print("=== システム要件チェック ===")
    
    # CPU情報
    cpu_count = os.cpu_count()
    print(f"論理プロセッサ数: {cpu_count}")
    
    # メモリ情報
    memory = psutil.virtual_memory()
    print(f"総メモリ: {memory.total / (1024**3):.1f} GB")
    print(f"利用可能メモリ: {memory.available / (1024**3):.1f} GB")
    
    # ディスク情報
    disk = psutil.disk_usage('/')
    print(f"ディスク容量: {disk.total / (1024**3):.1f} GB")
    print(f"ディスク空き: {disk.free / (1024**3):.1f} GB")
    
    # 必要なライブラリチェック
    required_packages = [
        'pandas', 'beautifulsoup4', 'lxml', 'psutil'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} (未インストール)")
    
    if missing_packages:
        print(f"\n以下のパッケージをインストールしてください:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def optimize_system():
    """システム最適化"""
    print("\n=== システム最適化 ===")
    
    try:
        # プロセス優先度を高く設定
        if sys.platform == "win32":
            psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            os.nice(-10)  # 高優先度
        print("✓ プロセス優先度を高く設定")
    except:
        print("△ プロセス優先度設定をスキップ")
    
    # 環境変数設定
    os.environ['OMP_NUM_THREADS'] = '24'
    os.environ['MKL_NUM_THREADS'] = '24'
    os.environ['OPENBLAS_NUM_THREADS'] = '24'
    os.environ['VECLIB_MAXIMUM_THREADS'] = '24'
    os.environ['NUMEXPR_NUM_THREADS'] = '24'
    print("✓ 並列処理環境変数を設定")
    
    # Python最適化設定
    sys.dont_write_bytecode = True  # .pycファイル生成を無効化
    print("✓ Python最適化設定")

def monitor_performance():
    """パフォーマンス監視"""
    print("\n=== リアルタイムパフォーマンス監視 ===")
    
    # CPU温度（可能な場合）
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                for entry in entries:
                    print(f"CPU温度: {entry.current}°C")
                    break
                break
    except:
        pass
    
    # CPU使用率
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"CPU使用率: {cpu_percent}%")
    
    # メモリ使用率
    memory_percent = psutil.virtual_memory().percent
    print(f"メモリ使用率: {memory_percent}%")
    
    # ディスクI/O
    disk_io = psutil.disk_io_counters()
    if disk_io:
        print(f"ディスク読み取り: {disk_io.read_bytes / (1024**2):.1f} MB")
        print(f"ディスク書き込み: {disk_io.write_bytes / (1024**2):.1f} MB")

def run_extraction():
    """抽出処理実行"""
    print("\n=== 特定投資株式情報抽出開始 ===")
    
    # 実行ファイルパス
    script_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/ultra_fast_marketable_securities_extractor.py"
    
    if not os.path.exists(script_path):
        print(f"エラー: 実行ファイルが見つかりません: {script_path}")
        return False
    
    # 実行開始時刻
    start_time = datetime.now()
    print(f"実行開始: {start_time}")
    
    try:
        # Python実行
        result = subprocess.run([
            sys.executable, script_path
        ], capture_output=False, text=True)
        
        # 実行終了時刻
        end_time = datetime.now()
        execution_time = end_time - start_time
        
        print(f"\n実行終了: {end_time}")
        print(f"実行時間: {execution_time}")
        
        if result.returncode == 0:
            print("✓ 処理が正常に完了しました")
            return True
        else:
            print(f"✗ 処理でエラーが発生しました (戻り値: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"✗ 実行エラー: {str(e)}")
        return False

def main():
    """メイン処理"""
    print("="*60)
    print("超高速特定投資株式情報抽出器")
    print("XG1-370 (AMD Ryzen AI 9 HX 370) 最適化版")
    print("="*60)
    
    # システム要件チェック
    if not check_system_requirements():
        print("\nシステム要件を満たしていません。")
        return
    
    # システム最適化
    optimize_system()
    
    # パフォーマンス監視
    monitor_performance()
    
    # 確認プロンプト
    print("\n" + "="*60)
    response = input("処理を開始しますか？ (y/N): ")
    if response.lower() != 'y':
        print("処理を中止しました。")
        return
    
    # 抽出処理実行
    success = run_extraction()
    
    if success:
        print("\n" + "="*60)
        print("処理が完了しました！")
        print("出力ファイルを確認してください。")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("処理でエラーが発生しました。")
        print("ログを確認してください。")
        print("="*60)

if __name__ == "__main__":
    main()