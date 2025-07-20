#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特定企業のXBRL抽出結果をテスト
"""

from xbrl_financial_analyzer import XBRLFinancialAnalyzer

def test_specific_company():
    analyzer = XBRLFinancialAnalyzer()
    
    # EDINETマッピング読み込み
    if not analyzer.load_edinet_mapping():
        print("Error: Could not load EDINET mapping")
        return
    
    # 北海道電力のファイルをテスト（E04500）
    file_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl/S100W0BE/XBRL/PublicDoc/jpcrp030000-asr-001_E04500-000_2025-03-31_01_2025-06-24.xbrl"
    
    print("=== テスト: 北海道電力 (9509) ===")
    
    # EDINETコード抽出
    edinet_code = analyzer.extract_edinet_code(file_path)
    print(f"EDINETコード: {edinet_code}")
    
    # 企業情報取得
    company_info = analyzer.get_company_info(edinet_code)
    if company_info:
        stock_code, company_name = company_info
        print(f"企業情報: {stock_code} - {company_name}")
    
    # 財務データ抽出
    financial_data = analyzer.extract_financial_data(file_path)
    print(f"\n=== 抽出された財務データ ===")
    for key, value in financial_data.items():
        if value is not None:
            print(f"{key}: {value:,.0f}")
        else:
            print(f"{key}: None")
    
    # 前年データの確認
    print(f"\n=== 前年データ比較 ===")
    if financial_data.get('investment_securities') and financial_data.get('prior_investment_securities'):
        current_sec = financial_data['investment_securities']
        prior_sec = financial_data['prior_investment_securities']
        print(f"投資有価証券 前年比: {current_sec / prior_sec:.2f}倍 ({prior_sec:,.0f} → {current_sec:,.0f})")
    
    if financial_data.get('dividend_income') and financial_data.get('prior_dividend_income'):
        current_div = financial_data['dividend_income']
        prior_div = financial_data['prior_dividend_income']
        print(f"配当金収入 前年比: {current_div / prior_div:.2f}倍 ({prior_div:,.0f} → {current_div:,.0f})")
    
    # 期待値と比較
    print(f"\n=== 期待値との比較 ===")
    print(f"期待投資有価証券: 91,904百万円")
    print(f"期待配当金収入: 712百万円")
    
    # CSVの実際の値と比較
    print(f"\n=== CSV内の記録値 ===")
    import pandas as pd
    df = pd.read_csv('/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl_financial_analysis_20250717_162218.csv')
    row = df[df['stock_code'] == '9509']
    if not row.empty:
        row = row.iloc[0]
        print(f"CSV投資有価証券: {row['bs_securities_assets']:,.0f}円 ({row['bs_securities_assets']/1000000:.0f}百万円)")
        print(f"CSV配当金収入: {row['pl_dividend_income']:,.0f}円 ({row['pl_dividend_income']/1000000:.0f}百万円)")
        print(f"配当比率: {row['dividend_ratio']:.2f}")

if __name__ == "__main__":
    test_specific_company()