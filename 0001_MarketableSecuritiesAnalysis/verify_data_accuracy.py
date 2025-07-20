#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
有報との一致性検証スクリプト
"""

import pandas as pd
import xml.etree.ElementTree as ET
from xbrl_financial_analyzer import XBRLFinancialAnalyzer
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataAccuracyVerifier:
    def __init__(self):
        self.analyzer = XBRLFinancialAnalyzer()
        self.discrepancies = []
        
    def verify_sample_companies(self, csv_file: str, sample_size: int = 20):
        """
        サンプル企業について有報との一致性を検証
        
        Args:
            csv_file: テスト結果CSVファイル
            sample_size: 検証するサンプル数
        """
        logger.info(f"データ精度検証開始: {sample_size}社のサンプル")
        
        # CSVファイル読み込み
        df = pd.read_csv(csv_file)
        
        # 主要指標が抽出されている企業をサンプルとして選択
        sample_companies = df[
            (df['has_net_sales_cy'] == True) & 
            (df['has_total_assets_cy'] == True) & 
            (df['has_net_assets_cy'] == True)
        ].head(sample_size)
        
        logger.info(f"検証対象企業数: {len(sample_companies)}社")
        
        for idx, company in sample_companies.iterrows():
            logger.info(f"検証中: {company['stock_code']} {company['company_name']}")
            self._verify_single_company(company)
            
        # 検証結果をまとめる
        self._summarize_verification_results()
    
    def _verify_single_company(self, company_data):
        """単一企業のデータ検証"""
        try:
            file_path = company_data['file_path']
            
            # XMLファイルを再度解析
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 会社情報
            stock_code = company_data['stock_code']
            company_name = company_data['company_name']
            company_type = company_data['company_type']
            accounting_standard = company_data['accounting_standard']
            
            # 経営指標を再抽出
            management_indicators = self.analyzer.extract_management_indicators(
                root, company_type, accounting_standard
            )
            
            # 主要指標の一致性をチェック
            self._check_indicator_consistency(
                stock_code, company_name, company_data, management_indicators
            )
            
            # XBRLファイル内での値の妥当性をチェック
            self._check_xbrl_values_validity(
                stock_code, company_name, root, management_indicators
            )
            
        except Exception as e:
            logger.error(f"検証エラー {stock_code} {company_name}: {e}")
            self.discrepancies.append({
                'stock_code': stock_code,
                'company_name': company_name,
                'type': 'processing_error',
                'message': str(e)
            })
    
    def _check_indicator_consistency(self, stock_code, company_name, csv_data, extracted_data):
        """CSVデータと再抽出データの一致性チェック"""
        
        key_indicators = [
            'net_sales_cy', 'operating_income_cy', 'total_assets_cy', 'net_assets_cy'
        ]
        
        for indicator in key_indicators:
            csv_value = csv_data.get(indicator)
            extracted_value = extracted_data.get(indicator)
            
            # 両方の値が存在する場合のみ比較
            if pd.notna(csv_value) and extracted_value is not None:
                # 数値の差異をチェック（小数点以下の違いは許容）
                if abs(float(csv_value) - float(extracted_value)) > 1000:  # 1000円以上の差異
                    self.discrepancies.append({
                        'stock_code': stock_code,
                        'company_name': company_name,
                        'type': 'value_mismatch',
                        'indicator': indicator,
                        'csv_value': csv_value,
                        'extracted_value': extracted_value,
                        'difference': abs(float(csv_value) - float(extracted_value))
                    })
                    logger.warning(f"値の不一致: {stock_code} {indicator} CSV:{csv_value} 抽出:{extracted_value}")
                else:
                    logger.debug(f"値一致: {stock_code} {indicator} = {csv_value}")
            
            # 片方のみ値がある場合
            elif pd.notna(csv_value) and extracted_value is None:
                self.discrepancies.append({
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'type': 'missing_in_reextraction',
                    'indicator': indicator,
                    'csv_value': csv_value
                })
            elif pd.isna(csv_value) and extracted_value is not None:
                self.discrepancies.append({
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'type': 'missing_in_csv',
                    'indicator': indicator,
                    'extracted_value': extracted_value
                })
    
    def _check_xbrl_values_validity(self, stock_code, company_name, root, indicators):
        """XBRLファイル内での値の妥当性チェック"""
        
        # 名前空間を取得
        namespaces = {
            'jppfs': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2019-11-01/jppfs_cor',
            'jpcrp': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2019-11-01/jpcrp_cor'
        }
        
        # 売上高の妥当性チェック
        net_sales = indicators.get('net_sales_cy')
        if net_sales is not None:
            # 異常に大きな値や小さな値をチェック
            if net_sales < 0:
                self.discrepancies.append({
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'type': 'negative_value',
                    'indicator': 'net_sales_cy',
                    'value': net_sales
                })
            elif net_sales > 1e15:  # 1000兆円を超える場合
                self.discrepancies.append({
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'type': 'unrealistic_large_value',
                    'indicator': 'net_sales_cy',
                    'value': net_sales
                })
        
        # 総資産と純資産の関係性チェック
        total_assets = indicators.get('total_assets_cy')
        net_assets = indicators.get('net_assets_cy')
        
        if total_assets is not None and net_assets is not None:
            if net_assets > total_assets:
                self.discrepancies.append({
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'type': 'logical_inconsistency',
                    'message': f'純資産({net_assets})が総資産({total_assets})を上回る',
                    'total_assets': total_assets,
                    'net_assets': net_assets
                })
            
            # 異常に高い自己資本比率（100%超）
            equity_ratio = (net_assets / total_assets) * 100
            if equity_ratio > 100:
                self.discrepancies.append({
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'type': 'unrealistic_ratio',
                    'message': f'自己資本比率が100%を超える: {equity_ratio:.1f}%',
                    'equity_ratio': equity_ratio
                })
    
    def _summarize_verification_results(self):
        """検証結果をまとめる"""
        logger.info("=== データ精度検証結果 ===")
        
        if not self.discrepancies:
            logger.info("✅ 差異は検出されませんでした。全てのデータが一致しています。")
            return
        
        # 問題の種類別に集計
        issue_types = {}
        for disc in self.discrepancies:
            issue_type = disc['type']
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(disc)
        
        logger.info(f"検出された問題数: {len(self.discrepancies)}件")
        
        for issue_type, issues in issue_types.items():
            logger.info(f"\n--- {issue_type} ({len(issues)}件) ---")
            
            if issue_type == 'value_mismatch':
                for issue in issues[:5]:  # 最初の5件のみ表示
                    logger.info(
                        f"  {issue['stock_code']} {issue['company_name']}: "
                        f"{issue['indicator']} CSV:{issue['csv_value']} 抽出:{issue['extracted_value']} "
                        f"差異:{issue['difference']:,.0f}円"
                    )
            
            elif issue_type == 'logical_inconsistency':
                for issue in issues:
                    logger.info(f"  {issue['stock_code']} {issue['company_name']}: {issue['message']}")
            
            elif issue_type == 'negative_value':
                for issue in issues:
                    logger.info(
                        f"  {issue['stock_code']} {issue['company_name']}: "
                        f"{issue['indicator']} = {issue['value']:,.0f}"
                    )
        
        # CSVファイルに結果を保存
        if self.discrepancies:
            df_disc = pd.DataFrame(self.discrepancies)
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            csv_file = f"data_accuracy_issues_{timestamp}.csv"
            df_disc.to_csv(csv_file, index=False, encoding='utf-8')
            logger.info(f"問題詳細をCSVファイルに保存: {csv_file}")
    
    def generate_improvement_recommendations(self):
        """改善提案を生成"""
        if not self.discrepancies:
            return
        
        logger.info("\n=== 改善提案 ===")
        
        issue_types = set(disc['type'] for disc in self.discrepancies)
        
        if 'value_mismatch' in issue_types:
            logger.info("1. 値の不一致について:")
            logger.info("   - XBRLタグの定義を見直し、より正確なマッピングを追加")
            logger.info("   - 単位変換処理（百万円、千円等）の確認")
            logger.info("   - コンテキスト期間の指定方法を見直し")
        
        if 'logical_inconsistency' in issue_types:
            logger.info("2. 論理的矛盾について:")
            logger.info("   - 連結・非連結の区別を正確に判定")
            logger.info("   - 表示通貨単位の統一処理を追加")
        
        if 'missing_in_reextraction' in issue_types:
            logger.info("3. 再抽出で欠損について:")
            logger.info("   - 一時的な処理エラーの可能性を調査")
            logger.info("   - タグマッピングの網羅性を向上")

def main():
    """メイン処理"""
    verifier = DataAccuracyVerifier()
    
    # 最新のテスト結果ファイルを使用
    csv_file = "comprehensive_test_results_20250720_092018.csv"
    
    # 50社のサンプルでデータ精度を検証
    verifier.verify_sample_companies(csv_file, sample_size=50)
    
    # 改善提案を生成
    verifier.generate_improvement_recommendations()

if __name__ == "__main__":
    main()