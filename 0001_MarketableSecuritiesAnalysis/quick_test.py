#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
クイックテスト - 100社程度での動作確認
"""

import pandas as pd
from xbrl_financial_analyzer import XBRLFinancialAnalyzer
import time
from collections import defaultdict

def quick_test():
    """クイックテスト実行"""
    print("=== クイックテスト開始 (100社) ===")
    
    analyzer = XBRLFinancialAnalyzer()
    
    # EDINETマッピング読み込み
    if not analyzer.load_edinet_mapping():
        print("EDINETマッピング読み込み失敗")
        return
    
    # XBRLファイル検索
    xbrl_files = analyzer.find_xbrl_files()
    test_files = xbrl_files[:100]  # 100社のみテスト
    
    print(f"テスト対象: {len(test_files)}ファイル")
    
    results = []
    company_types = defaultdict(int)
    accounting_standards = defaultdict(int)
    
    start_time = time.time()
    
    for i, file_path in enumerate(test_files):
        print(f"処理中 {i+1}/100: {file_path.split('/')[-1]}")
        
        # EDINETコード抽出
        edinet_code = analyzer.extract_edinet_code(file_path)
        if not edinet_code:
            continue
        
        # 企業情報取得
        company_info = analyzer.get_company_info(edinet_code)
        if not company_info:
            continue
            
        stock_code, company_name = company_info
        
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 企業タイプと会計基準判定
            company_type = analyzer._detect_company_type(edinet_code)
            accounting_standard = analyzer._detect_accounting_standard(root)
            
            company_types[company_type] += 1
            accounting_standards[accounting_standard] += 1
            
            # 連結経営指標抽出
            management_indicators = analyzer.extract_management_indicators(root, company_type, accounting_standard)
            
            extracted_count = sum(1 for v in management_indicators.values() if v is not None)
            extraction_rate = extracted_count / len(management_indicators) if len(management_indicators) > 0 else 0
            
            result = {
                'stock_code': stock_code,
                'company_name': company_name,
                'company_type': company_type,
                'accounting_standard': accounting_standard,
                'extracted_count': extracted_count,
                'total_count': len(management_indicators),
                'extraction_rate': extraction_rate
            }
            
            # 主要指標の抽出状況
            key_indicators = ['net_sales_cy', 'operating_income_cy', 'total_assets_cy', 'net_assets_cy']
            for indicator in key_indicators:
                result[f'has_{indicator}'] = indicator in management_indicators and management_indicators[indicator] is not None
                if result[f'has_{indicator}']:
                    result[indicator] = management_indicators[indicator]
            
            results.append(result)
            
            print(f"  → {stock_code} {company_name} ({company_type}, {accounting_standard}) - {extracted_count}/{len(management_indicators)}指標 ({extraction_rate*100:.1f}%)")
            
        except Exception as e:
            print(f"  → エラー: {e}")
            continue
    
    elapsed_time = time.time() - start_time
    
    print(f"\n=== テスト結果 ===")
    print(f"処理時間: {elapsed_time:.1f}秒")
    print(f"成功企業数: {len(results)}社")
    
    if results:
        df = pd.DataFrame(results)
        
        # 基本統計
        print(f"平均抽出指標数: {df['extracted_count'].mean():.1f}個")
        print(f"平均抽出率: {df['extraction_rate'].mean()*100:.1f}%")
        
        # 業種別統計
        print(f"\n--- 業種別統計 ---")
        print("企業タイプ分布:")
        for company_type, count in company_types.items():
            print(f"  {company_type}: {count}社")
        
        print("会計基準分布:")
        for standard, count in accounting_standards.items():
            print(f"  {standard}: {count}社")
        
        # 高パフォーマンス企業
        high_performance = df[df['extraction_rate'] >= 0.2]
        if len(high_performance) > 0:
            print(f"\n--- 抽出率20%以上の企業 ({len(high_performance)}社) ---")
            for _, row in high_performance.head(10).iterrows():
                print(f"  {row['stock_code']} {row['company_name']} - {row['extraction_rate']*100:.1f}%")
        
        # 主要指標の抽出成功率
        print(f"\n--- 主要指標抽出成功率 ---")
        key_indicators = ['has_net_sales_cy', 'has_operating_income_cy', 'has_total_assets_cy', 'has_net_assets_cy']
        for indicator in key_indicators:
            if indicator in df.columns:
                success_rate = df[indicator].mean() * 100
                print(f"{indicator}: {success_rate:.1f}%")
        
        # 実際の値のサンプル表示
        print(f"\n--- 抽出値サンプル（上位5社） ---")
        sample_df = df[df['has_net_sales_cy']].head(5)
        for _, row in sample_df.iterrows():
            print(f"{row['stock_code']} {row['company_name']}:")
            if 'net_sales_cy' in row:
                print(f"  売上高: {row['net_sales_cy']:,.0f}円")
            if 'total_assets_cy' in row:
                print(f"  総資産: {row['total_assets_cy']:,.0f}円")
        
        # CSV保存
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"quick_test_results_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"\n詳細結果: {csv_file}")
        
        return True
    
    else:
        print("有効な結果が得られませんでした")
        return False

if __name__ == "__main__":
    quick_test()