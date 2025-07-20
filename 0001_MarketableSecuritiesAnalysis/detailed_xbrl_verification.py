#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XBRL内容との詳細突合せ検証スクリプト
"""

import pandas as pd
import xml.etree.ElementTree as ET
from xbrl_financial_analyzer import XBRLFinancialAnalyzer
import logging
import re

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DetailedXBRLVerifier:
    def __init__(self):
        self.analyzer = XBRLFinancialAnalyzer()
        self.verification_results = []
        
    def verify_xbrl_content_matching(self, csv_file: str, sample_size: int = 10):
        """
        XBRLファイル内容との詳細突合せ
        
        Args:
            csv_file: テスト結果CSVファイル
            sample_size: 検証するサンプル数
        """
        logger.info(f"XBRL内容詳細検証開始: {sample_size}社のサンプル")
        
        # CSVファイル読み込み
        df = pd.read_csv(csv_file)
        
        # 様々な企業タイプのサンプルを選択
        general_companies = df[df['company_type'] == 'general'].head(4)
        trading_companies = df[df['company_type'] == 'trading'].head(3)
        bank_companies = df[df['company_type'] == 'bank'].head(2)
        securities_companies = df[df['company_type'] == 'securities'].head(1)
        
        sample_companies = pd.concat([
            general_companies, trading_companies, bank_companies, securities_companies
        ])
        
        logger.info(f"検証対象企業数: {len(sample_companies)}社")
        logger.info(f"  - 一般企業: {len(general_companies)}社")
        logger.info(f"  - 商社: {len(trading_companies)}社")
        logger.info(f"  - 銀行: {len(bank_companies)}社")
        logger.info(f"  - 証券: {len(securities_companies)}社")
        
        for idx, company in sample_companies.iterrows():
            self._verify_company_xbrl_content(company)
            
        # 検証結果をまとめる
        self._summarize_detailed_verification()
    
    def _verify_company_xbrl_content(self, company_data):
        """個別企業のXBRL内容詳細検証"""
        try:
            file_path = company_data['file_path']
            stock_code = company_data['stock_code']
            company_name = company_data['company_name']
            company_type = company_data['company_type']
            
            logger.info(f"詳細検証中: {stock_code} {company_name} ({company_type})")
            
            # XMLファイルを解析
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 名前空間の取得
            namespaces = self._extract_namespaces(root)
            
            verification_result = {
                'stock_code': stock_code,
                'company_name': company_name,
                'company_type': company_type,
                'file_path': file_path,
                'namespaces_found': list(namespaces.keys()),
                'verification_details': []
            }
            
            # 主要指標のXBRL内での存在確認
            self._verify_indicators_in_xbrl(
                root, namespaces, company_data, verification_result
            )
            
            # コンテキスト情報の確認
            self._verify_context_information(
                root, namespaces, verification_result
            )
            
            # 単位情報の確認
            self._verify_unit_information(
                root, namespaces, verification_result
            )
            
            self.verification_results.append(verification_result)
            
        except Exception as e:
            logger.error(f"詳細検証エラー {stock_code} {company_name}: {e}")
    
    def _extract_namespaces(self, root):
        """XMLから名前空間を抽出"""
        namespaces = {}
        for prefix, uri in root.nsmap.items() if hasattr(root, 'nsmap') else {}:
            if prefix:
                namespaces[prefix] = uri
        
        # 手動で主要な名前空間を追加
        default_namespaces = {
            'jppfs': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2019-11-01/jppfs_cor',
            'jpcrp': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2019-11-01/jpcrp_cor',
            'jppfs_bk': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2019-11-01/jppfs_bk',
            'ifrs': 'http://xbrl.ifrs.org/taxonomy/2019-03-27/ifrs-full'
        }
        
        for prefix, uri in default_namespaces.items():
            if prefix not in namespaces:
                # 実際にその名前空間のタグが存在するかチェック
                test_elements = root.findall(f".//{{{uri}}}*")
                if test_elements:
                    namespaces[prefix] = uri
        
        return namespaces
    
    def _verify_indicators_in_xbrl(self, root, namespaces, company_data, result):
        """主要指標のXBRL内での存在確認"""
        
        # 検証対象の指標
        key_indicators = [
            ('net_sales_cy', 'NetSales', '売上高'),
            ('operating_income_cy', 'OperatingIncome', '営業利益'),
            ('total_assets_cy', 'Assets', '総資産'),
            ('net_assets_cy', 'NetAssets', '純資産')
        ]
        
        for indicator_key, xbrl_tag, japanese_name in key_indicators:
            csv_value = company_data.get(indicator_key)
            
            if pd.notna(csv_value):
                # XBRLファイル内でこの値を探す
                found_elements = self._find_value_in_xbrl(
                    root, namespaces, float(csv_value), xbrl_tag
                )
                
                detail = {
                    'indicator': indicator_key,
                    'japanese_name': japanese_name,
                    'csv_value': csv_value,
                    'found_in_xbrl': len(found_elements) > 0,
                    'matching_elements': []
                }
                
                for elem in found_elements[:3]:  # 最初の3つまで
                    detail['matching_elements'].append({
                        'tag': elem.tag,
                        'value': elem.text,
                        'context_ref': elem.get('contextRef', ''),
                        'unit_ref': elem.get('unitRef', ''),
                        'decimals': elem.get('decimals', '')
                    })
                
                result['verification_details'].append(detail)
                
                if found_elements:
                    logger.info(f"  ✅ {japanese_name}: {csv_value:,.0f}円 - XBRL内で確認")
                else:
                    logger.warning(f"  ⚠️ {japanese_name}: {csv_value:,.0f}円 - XBRL内で見つからず")
    
    def _find_value_in_xbrl(self, root, namespaces, target_value, tag_hint):
        """XBRL内で特定の値を探す"""
        found_elements = []
        
        # すべての数値要素を検索
        for elem in root.iter():
            if elem.text and elem.text.strip():
                try:
                    # 数値として解釈可能な要素のみチェック
                    element_value = float(elem.text.replace(',', ''))
                    
                    # 値が一致するかチェック（小数点以下の違いは許容）
                    if abs(element_value - target_value) < max(1000, target_value * 0.001):
                        # タグ名にヒントが含まれているかチェック
                        tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                        if tag_hint.lower() in tag_name.lower() or self._is_relevant_tag(tag_name, tag_hint):
                            found_elements.append(elem)
                            
                except (ValueError, TypeError):
                    continue
        
        return found_elements
    
    def _is_relevant_tag(self, tag_name, hint):
        """タグが関連性があるかチェック"""
        # 売上高関連
        if hint == 'NetSales':
            return any(keyword in tag_name.lower() for keyword in [
                'netsales', 'sales', 'revenue', 'turnover'
            ])
        
        # 営業利益関連
        elif hint == 'OperatingIncome':
            return any(keyword in tag_name.lower() for keyword in [
                'operatingincome', 'operating', 'income'
            ])
        
        # 総資産関連
        elif hint == 'Assets':
            return any(keyword in tag_name.lower() for keyword in [
                'assets', 'totalassets'
            ])
        
        # 純資産関連
        elif hint == 'NetAssets':
            return any(keyword in tag_name.lower() for keyword in [
                'netassets', 'equity', 'shareholders'
            ])
        
        return False
    
    def _verify_context_information(self, root, namespaces, result):
        """コンテキスト情報の確認"""
        contexts = root.findall('.//xbrli:context', {
            'xbrli': 'http://www.xbrl.org/2003/instance'
        })
        
        context_info = {
            'total_contexts': len(contexts),
            'current_contexts': 0,
            'prior_contexts': 0,
            'consolidated_contexts': 0
        }
        
        for context in contexts:
            context_id = context.get('id', '')
            
            # 当年度のコンテキストを判定
            if any(pattern in context_id.lower() for pattern in ['current', 'cy', 'duration']):
                context_info['current_contexts'] += 1
            
            # 前年度のコンテキストを判定
            if any(pattern in context_id.lower() for pattern in ['prior', 'py', 'previous']):
                context_info['prior_contexts'] += 1
            
            # 連結のコンテキストを判定
            if any(pattern in context_id.lower() for pattern in ['consolidated', 'consol']):
                context_info['consolidated_contexts'] += 1
        
        result['context_info'] = context_info
        logger.info(f"  コンテキスト: 総数{context_info['total_contexts']}, "
                   f"当年{context_info['current_contexts']}, "
                   f"前年{context_info['prior_contexts']}, "
                   f"連結{context_info['consolidated_contexts']}")
    
    def _verify_unit_information(self, root, namespaces, result):
        """単位情報の確認"""
        units = root.findall('.//xbrli:unit', {
            'xbrli': 'http://www.xbrl.org/2003/instance'
        })
        
        unit_info = {
            'total_units': len(units),
            'currency_units': 0,
            'share_units': 0,
            'pure_units': 0
        }
        
        for unit in units:
            unit_id = unit.get('id', '')
            measure_elements = unit.findall('.//xbrli:measure', {
                'xbrli': 'http://www.xbrl.org/2003/instance'
            })
            
            for measure in measure_elements:
                measure_text = measure.text if measure.text else ''
                
                if 'jpy' in measure_text.lower() or 'yen' in measure_text.lower():
                    unit_info['currency_units'] += 1
                elif 'shares' in measure_text.lower() or 'share' in unit_id.lower():
                    unit_info['share_units'] += 1
                elif 'pure' in measure_text.lower():
                    unit_info['pure_units'] += 1
        
        result['unit_info'] = unit_info
        logger.info(f"  単位: 総数{unit_info['total_units']}, "
                   f"通貨{unit_info['currency_units']}, "
                   f"株式{unit_info['share_units']}, "
                   f"純数{unit_info['pure_units']}")
    
    def _summarize_detailed_verification(self):
        """詳細検証結果をまとめる"""
        logger.info("\n=== XBRL内容詳細検証結果 ===")
        
        total_companies = len(self.verification_results)
        total_indicators_checked = 0
        indicators_found_in_xbrl = 0
        
        company_type_stats = {}
        
        for result in self.verification_results:
            company_type = result['company_type']
            if company_type not in company_type_stats:
                company_type_stats[company_type] = {
                    'companies': 0,
                    'indicators_total': 0,
                    'indicators_found': 0
                }
            
            company_type_stats[company_type]['companies'] += 1
            
            for detail in result['verification_details']:
                total_indicators_checked += 1
                company_type_stats[company_type]['indicators_total'] += 1
                
                if detail['found_in_xbrl']:
                    indicators_found_in_xbrl += 1
                    company_type_stats[company_type]['indicators_found'] += 1
        
        logger.info(f"検証対象企業数: {total_companies}社")
        logger.info(f"検証対象指標数: {total_indicators_checked}項目")
        logger.info(f"XBRL内で確認できた指標: {indicators_found_in_xbrl}項目 "
                   f"({indicators_found_in_xbrl/total_indicators_checked*100:.1f}%)")
        
        logger.info("\n--- 企業タイプ別詳細 ---")
        for company_type, stats in company_type_stats.items():
            if stats['indicators_total'] > 0:
                match_rate = stats['indicators_found'] / stats['indicators_total'] * 100
                logger.info(f"{company_type}: {stats['companies']}社, "
                           f"一致率 {stats['indicators_found']}/{stats['indicators_total']} "
                           f"({match_rate:.1f}%)")
        
        # 詳細結果をCSVに保存
        self._save_detailed_results()
    
    def _save_detailed_results(self):
        """詳細結果をCSVファイルに保存"""
        detailed_data = []
        
        for result in self.verification_results:
            base_row = {
                'stock_code': result['stock_code'],
                'company_name': result['company_name'],
                'company_type': result['company_type'],
                'total_contexts': result.get('context_info', {}).get('total_contexts', 0),
                'current_contexts': result.get('context_info', {}).get('current_contexts', 0),
                'consolidated_contexts': result.get('context_info', {}).get('consolidated_contexts', 0),
                'total_units': result.get('unit_info', {}).get('total_units', 0),
                'currency_units': result.get('unit_info', {}).get('currency_units', 0)
            }
            
            for detail in result['verification_details']:
                row = base_row.copy()
                row.update({
                    'indicator': detail['indicator'],
                    'japanese_name': detail['japanese_name'],
                    'csv_value': detail['csv_value'],
                    'found_in_xbrl': detail['found_in_xbrl'],
                    'matching_elements_count': len(detail['matching_elements'])
                })
                detailed_data.append(row)
        
        if detailed_data:
            df_detailed = pd.DataFrame(detailed_data)
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            csv_file = f"detailed_xbrl_verification_{timestamp}.csv"
            df_detailed.to_csv(csv_file, index=False, encoding='utf-8')
            logger.info(f"詳細検証結果をCSVファイルに保存: {csv_file}")

def main():
    """メイン処理"""
    verifier = DetailedXBRLVerifier()
    
    # 最新のテスト結果ファイルを使用
    csv_file = "comprehensive_test_results_20250720_092018.csv"
    
    # 詳細なXBRL内容検証を実行
    verifier.verify_xbrl_content_matching(csv_file, sample_size=10)

if __name__ == "__main__":
    main()