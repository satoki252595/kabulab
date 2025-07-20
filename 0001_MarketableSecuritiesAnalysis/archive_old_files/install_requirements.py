#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
必要なライブラリのインストールスクリプト
AMD Ryzen AI 9 HX 370 最適化版
"""

import subprocess
import sys
import os

def install_package(package):
    """パッケージインストール"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def install_optimized_packages():
    """最適化されたパッケージインストール"""
    print("=== 必要なライブラリのインストール ===")
    
    # 基本パッケージ
    basic_packages = [
        "pandas",
        "beautifulsoup4", 
        "lxml",
        "psutil",
        "aiofiles",
        "numpy",
        "openpyxl"
    ]
    
    # 高速化パッケージ
    performance_packages = [
        "numexpr",  # 数値計算高速化
        "bottleneck",  # pandas高速化
        "cython",  # C拡張
        "ujson",  # 高速JSON処理
        "pyarrow",  # 高速データ処理
    ]
    
    # AMD最適化パッケージ（可能な場合）
    amd_packages = [
        "mkl",  # Intel Math Kernel Library
        "blas",  # Basic Linear Algebra Subprograms
    ]
    
    all_packages = basic_packages + performance_packages
    
    success_count = 0
    failed_packages = []
    
    for package in all_packages:
        print(f"インストール中: {package}")
        if install_package(package):
            print(f"✓ {package} インストール成功")
            success_count += 1
        else:
            print(f"✗ {package} インストール失敗")
            failed_packages.append(package)
    
    print(f"\n=== インストール結果 ===")
    print(f"成功: {success_count}/{len(all_packages)} パッケージ")
    
    if failed_packages:
        print(f"失敗: {failed_packages}")
        print("手動でインストールしてください:")
        print(f"pip install {' '.join(failed_packages)}")
    
    return len(failed_packages) == 0

def optimize_pip():
    """pip最適化"""
    print("\n=== pip最適化 ===")
    
    try:
        # pip自体を最新化
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        print("✓ pip を最新版に更新")
        
        # 並列ダウンロード有効化
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip-tools"])
        print("✓ pip-tools インストール")
        
        return True
    except:
        print("△ pip最適化をスキップ")
        return False

def setup_environment():
    """環境設定"""
    print("\n=== 環境設定 ===")
    
    # 環境変数設定
    env_vars = {
        'OMP_NUM_THREADS': '24',
        'MKL_NUM_THREADS': '24',
        'OPENBLAS_NUM_THREADS': '24',
        'VECLIB_MAXIMUM_THREADS': '24',
        'NUMEXPR_NUM_THREADS': '24',
        'PYTHONHASHSEED': '0',  # 再現性のため
        'PYTHONUNBUFFERED': '1',  # 出力バッファリング無効
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✓ {key} = {value}")
    
    print("✓ 環境変数設定完了")

def main():
    """メイン処理"""
    print("="*60)
    print("AMD Ryzen AI 9 HX 370 最適化ライブラリインストール")
    print("="*60)
    
    # pip最適化
    optimize_pip()
    
    # パッケージインストール
    success = install_optimized_packages()
    
    # 環境設定
    setup_environment()
    
    print("\n" + "="*60)
    if success:
        print("✓ すべてのライブラリのインストールが完了しました")
        print("ultra_fast_marketable_securities_extractor.py を実行できます")
    else:
        print("△ 一部のライブラリでエラーが発生しました")
        print("エラーメッセージを確認して手動でインストールしてください")
    print("="*60)

if __name__ == "__main__":
    main()