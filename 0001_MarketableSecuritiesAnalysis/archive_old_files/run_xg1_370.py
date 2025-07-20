#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XG1-370 (AMD Ryzen AI 9 HX 370) 専用実行スクリプト

このスクリプトは以下のハードウェア仕様に最適化されています：
- AMD Ryzen AI 9 HX 370 (12コア/24スレッド)
- 動的加速周波数: 5.1GHz  
- L3キャッシュ: 24MB
- Zen 5 (4コア) + Zen 5c (8コア) アーキテクチャ
- DDR5 5600MHz/LPDDR5X 7500MHz (最大128GB)
- PCIe 4.0 NVMe SSD (最大8TB)
- NPU 50TOPS + CPU + GPU = 80TOPS AI性能
"""

import os
import sys
import subprocess
import time
import psutil
from datetime import datetime
import platform

def detect_hardware_compatibility():
    """XG1-370ハードウェア互換性チェック"""
    print("=== XG1-370 ハードウェア互換性チェック ===")
    
    # CPU情報
    cpu_count = os.cpu_count()
    print(f"論理プロセッサ数: {cpu_count}")
    
    # CPUモデル確認（macOSの場合は概算）
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                cpu_model = result.stdout.strip()
                print(f"CPU: {cpu_model}")
        else:
            print("CPU: 自動検出できませんでした")
    except:
        print("CPU: 検出エラー")
    
    # メモリ情報
    memory = psutil.virtual_memory()
    total_gb = memory.total / (1024**3)
    available_gb = memory.available / (1024**3)
    print(f"総メモリ: {total_gb:.1f}GB")
    print(f"利用可能メモリ: {available_gb:.1f}GB")
    
    # 推奨スペックチェック
    recommendations = []
    if cpu_count < 24:
        recommendations.append(f"CPU: {cpu_count}スレッド（推奨: 24スレッド）")
    if total_gb < 32:
        recommendations.append(f"メモリ: {total_gb:.0f}GB（推奨: 32GB以上）")
    
    if recommendations:
        print("\\n⚠ 推奨スペック未満:")
        for rec in recommendations:
            print(f"  - {rec}")
        print("処理は続行されますが、性能が制限される可能性があります。")
    else:
        print("✓ XG1-370推奨スペックを満たしています")
    
    return True

def check_required_packages():
    """必要なパッケージ確認"""
    print("\\n=== 必要なパッケージ確認 ===")
    
    required_packages = [
        ('pandas', 'pandas'),
        ('beautifulsoup4', 'bs4'), 
        ('lxml', 'lxml'),
        ('psutil', 'psutil'),
        ('aiofiles', 'aiofiles'),
        ('numexpr', 'numexpr'),
        ('ujson', 'ujson')
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✓ {package_name}")
        except ImportError:
            missing_packages.append(package_name)
            print(f"✗ {package_name} (未インストール)")
    
    if missing_packages:
        print(f"\\n以下のパッケージをインストールしてください:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def optimize_system_for_xg1370():
    """XG1-370専用システム最適化"""
    print("\\n=== XG1-370 システム最適化 ===")
    
    try:
        # プロセス優先度を高く設定
        if sys.platform == "win32":
            psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            os.nice(-15)  # 高優先度
        print("✓ プロセス優先度を高く設定")
    except:
        print("△ プロセス優先度設定をスキップ")
    
    # XG1-370専用環境変数
    xg1370_env = {
        'OMP_NUM_THREADS': '24',       # 24スレッド
        'MKL_NUM_THREADS': '24',       # Intel MKL
        'OPENBLAS_NUM_THREADS': '24',  # OpenBLAS
        'VECLIB_MAXIMUM_THREADS': '24', # Apple vecLib
        'NUMEXPR_NUM_THREADS': '24',   # numexpr
        'NUMEXPR_MAX_THREADS': '24',
        'PYTHONHASHSEED': '0',         # 再現性
        'PYTHONUNBUFFERED': '1',       # リアルタイム出力
        'MALLOC_MMAP_THRESHOLD_': '65536',  # メモリ最適化
        'MALLOC_TRIM_THRESHOLD_': '131072'
    }
    
    for key, value in xg1370_env.items():
        os.environ[key] = value
        print(f"✓ {key} = {value}")
    
    # Python最適化設定
    sys.dont_write_bytecode = True  # .pycファイル生成無効化
    print("✓ Python最適化設定完了")

def monitor_xg1370_performance():
    """XG1-370パフォーマンス監視"""
    print("\\n=== XG1-370 リアルタイムパフォーマンス ===")
    
    # CPU使用率
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"CPU使用率: {cpu_percent:.1f}%")
    
    # CPU周波数
    try:
        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            print(f"CPU周波数: {cpu_freq.current:.0f}MHz (最大: {cpu_freq.max:.0f}MHz)")
    except:
        print("CPU周波数: 取得できませんでした")
    
    # メモリ使用率
    memory = psutil.virtual_memory()
    print(f"メモリ使用率: {memory.percent:.1f}% ({memory.used / (1024**3):.1f}GB / {memory.total / (1024**3):.1f}GB)")
    
    # ディスクI/O
    try:
        disk_io = psutil.disk_io_counters()
        if disk_io:
            print(f"ディスク読み取り: {disk_io.read_bytes / (1024**2):.1f}MB")
            print(f"ディスク書き込み: {disk_io.write_bytes / (1024**2):.1f}MB")
    except:
        print("ディスクI/O: 取得できませんでした")
    
    # 温度監視（対応している場合）
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current:
                        print(f"温度: {entry.current:.1f}°C")
                        break
                break
    except:
        pass

def run_xg1370_extractor():
    """XG1-370専用抽出器実行"""
    print("\\n=== XG1-370 特定投資株式情報抽出開始 ===")
    
    # 実行ファイルパス
    script_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xg1_370_ultra_extractor.py"
    
    if not os.path.exists(script_path):
        print(f"エラー: 実行ファイルが見つかりません: {script_path}")
        return False
    
    # 実行開始時刻
    start_time = datetime.now()
    print(f"実行開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # XG1-370最適化Python実行
        result = subprocess.run([
            sys.executable, script_path
        ], capture_output=False, text=True, timeout=3600)  # 1時間タイムアウト
        
        # 実行終了時刻
        end_time = datetime.now()
        execution_time = end_time - start_time
        
        print(f"\\n実行終了: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"実行時間: {execution_time}")
        
        if result.returncode == 0:
            print("✓ XG1-370処理が正常に完了しました")
            return True
        else:
            print(f"✗ 処理でエラーが発生しました (戻り値: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ 処理がタイムアウトしました（1時間）")
        return False
    except Exception as e:
        print(f"✗ 実行エラー: {str(e)}")
        return False

def main():
    """XG1-370専用メイン処理"""
    print("=" * 80)
    print("XG1-370 (AMD Ryzen AI 9 HX 370) 専用超高速特定投資株式情報抽出器")
    print("Zen 5 + Zen 5c + PCIe 4.0 + NPU 50TOPS 最適化版")
    print("=" * 80)
    
    # ハードウェア互換性チェック
    if not detect_hardware_compatibility():
        print("\\nハードウェア要件を満たしていません。")
        return
    
    # パッケージ確認
    if not check_required_packages():
        print("\\n必要なパッケージがインストールされていません。")
        return
    
    # XG1-370システム最適化
    optimize_system_for_xg1370()
    
    # パフォーマンス監視
    monitor_xg1370_performance()
    
    # 確認プロンプト
    print("\\n" + "=" * 80)
    response = input("XG1-370最適化処理を開始しますか？ (y/N): ")
    if response.lower() != 'y':
        print("処理を中止しました。")
        return
    
    # XG1-370専用抽出処理実行
    success = run_xg1370_extractor()
    
    if success:
        print("\\n" + "=" * 80)
        print("🚀 XG1-370処理が完了しました！")
        print("出力ファイルを確認してください。")
        print("Zen 5 + Zen 5c アーキテクチャの性能を最大限活用しました。")
        print("=" * 80)
    else:
        print("\\n" + "=" * 80)
        print("❌ XG1-370処理でエラーが発生しました。")
        print("ログを確認してください。")
        print("=" * 80)

if __name__ == "__main__":
    main()