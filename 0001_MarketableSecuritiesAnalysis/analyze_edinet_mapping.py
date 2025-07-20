#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EDINET マッピングデータ分析ツール
"""

import pandas as pd
import re

def analyze_edinet_mapping():
    """EDINET マッピングデータを分析して構造を理解する"""
    
    # CSVファイルを読み込み（複数エンコーディングを試行）
    csv_path = "downloads/extracted/EdinetcodeDlInfo.csv"
    encodings = ['cp932', 'shift_jis', 'utf-8', 'euc-jp']
    
    df = None
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=encoding, skiprows=1)
            print(f"✓ CSVファイル読み込み成功 (エンコーディング: {encoding})")
            break
        except UnicodeDecodeError:
            continue
    
    if df is None:
        print("✗ CSVファイルの読み込みに失敗")
        return
    
    print(f"\n=== データ概要 ===")
    print(f"総レコード数: {len(df)}")
    print(f"列数: {len(df.columns)}")
    
    print(f"\n=== 列名 ===")
    for i, col in enumerate(df.columns):
        print(f"{i+1:2d}. {col}")
    
    # 最初の5行を表示
    print(f"\n=== サンプルデータ (最初の5行) ===")
    print(df.head().to_string())
    
    # EDINETコードの構造分析
    if len(df.columns) >= 1:
        edinet_col = df.columns[0]  # EDINETコード列
        print(f"\n=== EDINETコード分析 ===")
        print(f"EDINETコード列: {edinet_col}")
        edinet_samples = df[edinet_col].head(10).tolist()
        print(f"サンプル: {edinet_samples}")
    
    # 証券コードの構造分析
    if len(df.columns) >= 12:  # 証券コードは12列目付近
        sec_code_col = df.columns[11]  # 証券コード列
        print(f"\n=== 証券コード分析 ===")
        print(f"証券コード列: {sec_code_col}")
        
        # 証券コードの分布
        sec_codes = df[sec_code_col].dropna()
        print(f"有効な証券コード数: {len(sec_codes)}")
        
        # 証券コードのパターン分析
        patterns = {}
        for code in sec_codes.head(100):  # 最初の100件をサンプル
            code_str = str(code)
            length = len(code_str)
            if length not in patterns:
                patterns[length] = []
            patterns[length].append(code_str)
        
        print(f"\n=== 証券コードパターン ===")
        for length, codes in patterns.items():
            print(f"{length}桁: {len(codes)}件, 例: {codes[:5]}")
    
    # 業種分析
    if len(df.columns) >= 11:  # 業種は11列目付近
        industry_col = df.columns[10]  # 業種列
        print(f"\n=== 業種分析 ===")
        print(f"業種列: {industry_col}")
        
        industry_counts = df[industry_col].value_counts()
        print(f"\n主要業種 (上位10業種):")
        for industry, count in industry_counts.head(10).items():
            print(f"  {industry}: {count}社")
        
        # 銀行業と卸売業の分析
        banks = df[df[industry_col].str.contains('銀行', na=False)]
        trading = df[df[industry_col].str.contains('卸売', na=False)]
        print(f"\n特定業種:")
        print(f"  銀行業関連: {len(banks)}社")
        print(f"  卸売業関連: {len(trading)}社")
        
        if len(banks) > 0:
            print(f"  銀行業サンプル:")
            for i, row in banks.head(3).iterrows():
                edinet = row[edinet_col] if len(df.columns) >= 1 else 'N/A'
                sec_code = row[sec_code_col] if len(df.columns) >= 12 else 'N/A'
                company = row[df.columns[6]] if len(df.columns) >= 7 else 'N/A'
                print(f"    {edinet} -> {sec_code} ({company})")
        
        if len(trading) > 0:
            print(f"  卸売業サンプル:")
            for i, row in trading.head(3).iterrows():
                edinet = row[edinet_col] if len(df.columns) >= 1 else 'N/A'
                sec_code = row[sec_code_col] if len(df.columns) >= 12 else 'N/A'
                company = row[df.columns[6]] if len(df.columns) >= 7 else 'N/A'
                print(f"    {edinet} -> {sec_code} ({company})")

def clean_stock_code(sec_code):
    """証券コードから末尾の0を削除して4桁にする"""
    if pd.isna(sec_code):
        return None
    
    code_str = str(int(sec_code)) if isinstance(sec_code, float) else str(sec_code)
    
    # 末尾の0を削除（ただし、全て0になることは避ける）
    while len(code_str) > 1 and code_str.endswith('0'):
        code_str = code_str[:-1]
    
    return code_str

def test_stock_code_cleaning():
    """証券コード清浄化のテスト"""
    print(f"\n=== 証券コード清浄化テスト ===")
    
    test_cases = [
        13760, 13500, 100, 5500, 452, 421, 50074, 7527,
        '13760', '13500', '0100', '5500', '0452', '0421', '50074', '7527'
    ]
    
    for case in test_cases:
        cleaned = clean_stock_code(case)
        print(f"{case} -> {cleaned}")

if __name__ == "__main__":
    analyze_edinet_mapping()
    test_stock_code_cleaning()