#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前年データ機能のテスト
"""

from xbrl_financial_analyzer import XBRLFinancialAnalyzer
import pandas as pd

def test_prior_data():
    analyzer = XBRLFinancialAnalyzer()
    
    # EDINETマッピング読み込み
    if not analyzer.load_edinet_mapping():
        print("Error: Could not load EDINET mapping")
        return
    
    # 少数の企業でテスト
    xbrl_files = analyzer.find_xbrl_files()[:10]  # 最初の10社のみ
    
    results = []
    for file_path in xbrl_files:
        result = analyzer.process_single_file(file_path)
        if result:
            results.append(result)
    
    if results:
        df = pd.DataFrame(results)
        print(f"\n=== 前年データ機能テスト結果 ({len(results)}社) ===")
        
        # 新しい列が追加されたかチェック
        expected_columns = ['bs_securities_assets_prior', 'pl_dividend_income_prior']
        for col in expected_columns:
            if col in df.columns:
                print(f"✓ {col} 列が追加されました")
            else:
                print(f"✗ {col} 列が見つかりません")
        
        # 前年データを持つ企業の統計
        prior_securities = df[df['bs_securities_assets_prior'] > 0]
        prior_dividends = df[df['pl_dividend_income_prior'] > 0]
        
        print(f"\n=== 前年データ統計 ===")
        print(f"前年投資有価証券データ保有企業: {len(prior_securities)}社")
        print(f"前年配当金データ保有企業: {len(prior_dividends)}社")
        
        if len(prior_securities) > 0:
            print(f"\n=== 前年投資有価証券比較 ===")
            for _, row in prior_securities.head(5).iterrows():
                ratio = row['bs_securities_assets'] / row['bs_securities_assets_prior'] if row['bs_securities_assets_prior'] > 0 else 0
                print(f"{row['stock_code']} {row['company_name']}: {ratio:.2f}倍 ({row['bs_securities_assets_prior']:,.0f} → {row['bs_securities_assets']:,.0f})")
        
        if len(prior_dividends) > 0:
            print(f"\n=== 前年配当金比較 ===")
            for _, row in prior_dividends.head(5).iterrows():
                ratio = row['pl_dividend_income'] / row['pl_dividend_income_prior'] if row['pl_dividend_income_prior'] > 0 else 0
                print(f"{row['stock_code']} {row['company_name']}: {ratio:.2f}倍 ({row['pl_dividend_income_prior']:,.0f} → {row['pl_dividend_income']:,.0f})")
        
        # CSV形式で一部を表示
        print(f"\n=== CSV形式サンプル ===")
        sample_columns = ['stock_code', 'company_name', 'bs_securities_assets', 'bs_securities_assets_prior', 
                         'pl_dividend_income', 'pl_dividend_income_prior']
        print(df[sample_columns].head(3).to_string(index=False))
    
    else:
        print("テスト結果が得られませんでした")

if __name__ == "__main__":
    test_prior_data()