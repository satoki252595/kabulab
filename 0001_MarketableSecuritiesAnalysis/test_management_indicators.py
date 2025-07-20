#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
連結経営指標抽出機能のテスト
"""

from xbrl_financial_analyzer import XBRLFinancialAnalyzer

def test_management_indicators():
    """連結経営指標抽出のテスト"""
    analyzer = XBRLFinancialAnalyzer()
    
    # EDINETマッピング読み込み
    if not analyzer.load_edinet_mapping():
        print("Error: Could not load EDINET mapping")
        return
    
    # 少数の企業でテスト
    xbrl_files = analyzer.find_xbrl_files()[:3]  # 最初の3社のみ
    
    print(f"=== 連結経営指標抽出テスト ({len(xbrl_files)}ファイル) ===")
    
    for file_path in xbrl_files:
        print(f"\n--- {file_path} ---")
        
        # EDINETコード抽出
        edinet_code = analyzer.extract_edinet_code(file_path)
        company_info = analyzer.get_company_info(edinet_code) if edinet_code else None
        
        if company_info:
            stock_code, company_name = company_info
            print(f"企業: {stock_code} - {company_name}")
            
            # 財務データ抽出（管理指標を含む）
            financial_data = analyzer.extract_financial_data(file_path)
            
            # 管理指標のみを表示
            management_indicators = {k: v for k, v in financial_data.items() 
                                   if k.startswith(('net_sales_', 'operating_income_', 'ordinary_income_', 
                                                   'net_income_', 'total_assets_', 'net_assets_', 
                                                   'earnings_per_share_', 'equity_ratio_', 'roa_', 'roe_'))}
            
            extracted_count = sum(1 for v in management_indicators.values() if v is not None)
            print(f"抽出された指標: {extracted_count}/{len(management_indicators)}項目")
            
            # 有効な指標を表示
            for key, value in management_indicators.items():
                if value is not None:
                    if 'per_share' in key or 'ratio' in key or 'roa' in key or 'roe' in key:
                        print(f"  {key}: {value:.2f}")
                    else:
                        print(f"  {key}: {value:,.0f}")
        else:
            print("企業情報取得失敗")

if __name__ == "__main__":
    test_management_indicators()