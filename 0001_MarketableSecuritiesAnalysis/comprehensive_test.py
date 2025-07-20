#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
包括的テストシステム - 1000社以上の企業で連結経営指標抽出をテスト
"""

import pandas as pd
import numpy as np
from xbrl_financial_analyzer import XBRLFinancialAnalyzer
import time
from collections import defaultdict
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveTest:
    def __init__(self):
        self.analyzer = XBRLFinancialAnalyzer()
        self.results = []
        self.statistics = defaultdict(int)
        
    def run_comprehensive_test(self, target_count: int = 1000):
        """
        包括的テストを実行
        
        Args:
            target_count: テスト対象企業数
        """
        logger.info(f"包括的テスト開始: 目標 {target_count}社")
        
        # EDINETマッピング読み込み
        if not self.analyzer.load_edinet_mapping():
            logger.error("EDINETマッピングの読み込みに失敗しました")
            return None
        
        # XBRLファイル検索
        xbrl_files = self.analyzer.find_xbrl_files()
        if not xbrl_files:
            logger.error("XBRLファイルが見つかりません")
            return None
        
        logger.info(f"発見されたXBRLファイル数: {len(xbrl_files)}")
        
        # テスト対象ファイルを選択
        test_files = xbrl_files[:target_count] if len(xbrl_files) >= target_count else xbrl_files
        
        logger.info(f"テスト対象ファイル数: {len(test_files)}")
        
        # 各ファイルを処理
        start_time = time.time()
        successful_extractions = 0
        
        for i, file_path in enumerate(test_files):
            if i % 100 == 0:
                elapsed = time.time() - start_time
                logger.info(f"処理進捗: {i+1}/{len(test_files)} ({(i+1)/len(test_files)*100:.1f}%) - 経過時間: {elapsed:.1f}秒")
            
            # EDINETコード抽出
            edinet_code = self.analyzer.extract_edinet_code(file_path)
            if not edinet_code:
                self.statistics['no_edinet_code'] += 1
                continue
            
            # 企業情報取得
            company_info = self.analyzer.get_company_info(edinet_code)
            if not company_info:
                self.statistics['no_company_info'] += 1
                continue
                
            stock_code, company_name = company_info
            
            # 財務データ抽出
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(file_path)
                root = tree.getroot()
                
                # 企業タイプと会計基準を判定
                company_type = self.analyzer._detect_company_type(edinet_code)
                accounting_standard = self.analyzer._detect_accounting_standard(root)
                
                # 業種統計
                self.statistics[f'company_type_{company_type}'] += 1
                self.statistics[f'accounting_standard_{accounting_standard}'] += 1
                
                # 連結経営指標抽出
                management_indicators = self.analyzer.extract_management_indicators(root, company_type, accounting_standard)
                
                # 抽出成功した指標数をカウント
                extracted_count = sum(1 for v in management_indicators.values() if v is not None)
                
                # 結果を保存
                result = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'edinet_code': edinet_code,
                    'company_type': company_type,
                    'accounting_standard': accounting_standard,
                    'extracted_indicators_count': extracted_count,
                    'total_indicators_count': len(management_indicators),
                    'extraction_rate': extracted_count / len(management_indicators) if len(management_indicators) > 0 else 0,
                    'file_path': file_path
                }
                
                # 主要指標の抽出状況をチェック
                key_indicators = ['net_sales_cy', 'operating_income_cy', 'total_assets_cy', 'net_assets_cy']
                for indicator in key_indicators:
                    result[f'has_{indicator}'] = indicator in management_indicators and management_indicators[indicator] is not None
                
                result.update(management_indicators)
                self.results.append(result)
                successful_extractions += 1
                
                # 特に良好な抽出結果をログ出力
                if extracted_count >= 10:
                    logger.info(f"良好な抽出: {stock_code} ({company_type}, {accounting_standard}) - {extracted_count}/{len(management_indicators)}指標")
                
            except Exception as e:
                self.statistics['extraction_error'] += 1
                logger.debug(f"抽出エラー {file_path}: {e}")
                continue
        
        total_time = time.time() - start_time
        logger.info(f"テスト完了: {successful_extractions}/{len(test_files)}社処理完了 - 総時間: {total_time:.1f}秒")
        
        return pd.DataFrame(self.results) if self.results else pd.DataFrame()
    
    def analyze_results(self, df: pd.DataFrame):
        """テスト結果を分析"""
        if df.empty:
            logger.warning("分析対象データが空です")
            return
        
        logger.info("=== テスト結果分析 ===")
        
        # 基本統計
        print(f"\n--- 基本統計 ---")
        print(f"成功した企業数: {len(df)}社")
        print(f"平均抽出指標数: {df['extracted_indicators_count'].mean():.1f}個")
        print(f"平均抽出率: {df['extraction_rate'].mean()*100:.1f}%")
        print(f"最大抽出指標数: {df['extracted_indicators_count'].max()}個")
        print(f"最小抽出指標数: {df['extracted_indicators_count'].min()}個")
        
        # 企業タイプ別統計
        print(f"\n--- 企業タイプ別統計 ---")
        type_stats = df.groupby('company_type')['extraction_rate'].agg(['count', 'mean', 'std']).round(3)
        print(type_stats)
        
        # 会計基準別統計
        print(f"\n--- 会計基準別統計 ---")
        standard_stats = df.groupby('accounting_standard')['extraction_rate'].agg(['count', 'mean', 'std']).round(3)
        print(standard_stats)
        
        # 主要指標の抽出成功率
        print(f"\n--- 主要指標抽出成功率 ---")
        key_indicators = ['has_net_sales_cy', 'has_operating_income_cy', 'has_total_assets_cy', 'has_net_assets_cy']
        for indicator in key_indicators:
            if indicator in df.columns:
                success_rate = df[indicator].mean() * 100
                print(f"{indicator}: {success_rate:.1f}%")
        
        # 抽出率の分布
        print(f"\n--- 抽出率分布 ---")
        bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0]
        labels = ['0-10%', '10-20%', '20-30%', '30-40%', '40-50%', '50%+']
        df['rate_category'] = pd.cut(df['extraction_rate'], bins=bins, labels=labels, include_lowest=True)
        rate_dist = df['rate_category'].value_counts().sort_index()
        print(rate_dist)
        
        # 高パフォーマンス企業（抽出率30%以上）
        high_performance = df[df['extraction_rate'] >= 0.3]
        if len(high_performance) > 0:
            print(f"\n--- 高パフォーマンス企業 ({len(high_performance)}社, 抽出率30%以上) ---")
            for _, row in high_performance.head(10).iterrows():
                print(f"  {row['stock_code']} {row['company_name']} ({row['company_type']}, {row['accounting_standard']}) - {row['extraction_rate']*100:.1f}%")
        
        # 問題のある企業（抽出率10%以下）
        low_performance = df[df['extraction_rate'] <= 0.1]
        if len(low_performance) > 0:
            print(f"\n--- 低パフォーマンス企業 ({len(low_performance)}社, 抽出率10%以下) ---")
            for _, row in low_performance.head(5).iterrows():
                print(f"  {row['stock_code']} {row['company_name']} ({row['company_type']}, {row['accounting_standard']}) - {row['extraction_rate']*100:.1f}%")
        
        # 統計情報を出力
        print(f"\n--- 処理統計 ---")
        for key, value in self.statistics.items():
            print(f"{key}: {value}")
    
    def save_results(self, df: pd.DataFrame, filename: str = None):
        """結果をCSVファイルに保存"""
        if df.empty:
            logger.warning("保存対象データが空です")
            return
        
        if filename is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_test_results_{timestamp}.csv"
        
        df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"結果をCSVファイルに保存しました: {filename}")
        return filename

def main():
    """メイン処理"""
    tester = ComprehensiveTest()
    
    # 包括的テスト実行（1000社を目標）
    results_df = tester.run_comprehensive_test(target_count=1000)
    
    if not results_df.empty:
        # 結果分析
        tester.analyze_results(results_df)
        
        # 結果保存
        csv_file = tester.save_results(results_df)
        print(f"\n詳細結果: {csv_file}")
        
        # 改善提案の生成
        print(f"\n=== 改善提案 ===")
        avg_rate = results_df['extraction_rate'].mean()
        
        if avg_rate < 0.2:
            print("- 抽出率が低いため、タグマッピングの見直しが必要です")
            print("- より多くの業種別タクソノミーへの対応が必要です")
            print("- コンテキストパターンの拡張を検討してください")
        elif avg_rate < 0.4:
            print("- 特定業種（銀行、保険など）への対応強化が必要です")
            print("- IFRS対応の拡充を検討してください")
        else:
            print("- 良好な抽出率です。細かい調整で更なる向上を目指してください")
        
        # 業種別の課題分析
        type_performance = results_df.groupby('company_type')['extraction_rate'].mean()
        worst_type = type_performance.idxmin()
        worst_rate = type_performance.min()
        
        if worst_rate < 0.15:
            print(f"- 「{worst_type}」タイプの企業で抽出率が特に低いです（{worst_rate*100:.1f}%）")
            print(f"- {worst_type}企業向けの専用タグマッピングの追加を推奨します")
    
    else:
        print("テスト結果が得られませんでした。システム設定を確認してください。")

if __name__ == "__main__":
    main()