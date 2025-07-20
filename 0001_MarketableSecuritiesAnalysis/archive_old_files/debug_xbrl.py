#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XBRL抽出デバッグツール
特定企業のXBRLファイルを詳細に解析してデータ抽出の正確性を検証する
"""

import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Optional

class XBRLDebugger:
    def __init__(self):
        self.namespaces = {
            'jppfs_cor': [
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2022-11-01/jppfs_cor',
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2019-11-01/jppfs_cor',
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2018-11-01/jppfs_cor'
            ],
            'jpcrp_cor': [
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2022-11-01/jpcrp_cor',
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2019-11-01/jpcrp_cor',
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2018-11-01/jpcrp_cor'
            ]
        }
    
    def debug_file(self, file_path: str, company_name: str = ""):
        """XBRLファイルをデバッグ"""
        print(f"=== {company_name} XBRL Debug Analysis ===")
        print(f"File: {file_path}")
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # コンテキスト情報を取得
            contexts = self._get_contexts(root)
            print(f"\n=== Contexts Found: {len(contexts)} ===")
            for ctx_id, info in list(contexts.items())[:10]:  # 最初の10個だけ表示
                print(f"  {ctx_id}: {info}")
            
            # 投資有価証券関連タグを検索
            print(f"\n=== Investment Securities Analysis ===")
            securities_data = self._debug_investment_securities(root)
            
            # 配当金関連タグを検索
            print(f"\n=== Dividend Income Analysis ===")
            dividend_data = self._debug_dividend_income(root)
            
            # 発行済み株式数
            print(f"\n=== Issued Shares Analysis ===")
            shares_data = self._debug_issued_shares(root)
            
            return {
                'contexts': contexts,
                'securities': securities_data,
                'dividends': dividend_data,
                'shares': shares_data
            }
            
        except Exception as e:
            print(f"Error analyzing file: {e}")
            return None
    
    def _get_contexts(self, root):
        """コンテキスト情報を取得"""
        contexts = {}
        
        # xbrl:contextを検索
        for context in root.findall('.//{http://www.xbrl.org/2003/instance}context'):
            ctx_id = context.get('id', 'unknown')
            
            # 期間情報を取得
            period_info = "unknown"
            period_elem = context.find('.//{http://www.xbrl.org/2003/instance}period')
            if period_elem is not None:
                instant = period_elem.find('.//{http://www.xbrl.org/2003/instance}instant')
                if instant is not None:
                    period_info = f"instant:{instant.text}"
                else:
                    start = period_elem.find('.//{http://www.xbrl.org/2003/instance}startDate')
                    end = period_elem.find('.//{http://www.xbrl.org/2003/instance}endDate')
                    if start is not None and end is not None:
                        period_info = f"duration:{start.text}to{end.text}"
            
            # エンティティ情報
            entity_info = "unknown"
            entity = context.find('.//{http://www.xbrl.org/2003/instance}entity')
            if entity is not None:
                identifier = entity.find('.//{http://www.xbrl.org/2003/instance}identifier')
                if identifier is not None:
                    entity_info = identifier.text
            
            contexts[ctx_id] = f"{period_info}, entity:{entity_info}"
        
        return contexts
    
    def _debug_investment_securities(self, root):
        """投資有価証券の詳細デバッグ"""
        tags = [
            'jppfs_cor:InvestmentSecurities',
            'jppfs_cor:InvestmentSecuritiesNoncurrentAssets',
            'jppfs_cor:InvestmentSecuritiesCurrentAssets',
            'jppfs_cor:MarketableSecurities',
            'jppfs_cor:MarketableSecuritiesCA',
            'jppfs_cor:AvailableForSaleSecurities',
            'jppfs_cor:EquitySecurities',
            'jppfs_cor:OtherSecuritiesCA',
            'jppfs_cor:OtherSecuritiesIA'
        ]
        
        found_data = []
        
        # まず全ての数値要素を検索してパターンを把握
        print("  === All numeric elements containing 'securities' or similar ===")
        all_elements = root.findall('.//*')
        securities_keywords = ['investment', 'securities', 'marketable', 'equity', 'available']
        
        for element in all_elements:
            if element.text and element.text.strip():
                try:
                    value = float(element.text)
                    if value > 0:
                        tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
                        if any(keyword.lower() in tag_name.lower() for keyword in securities_keywords):
                            context_ref = element.get('contextRef', 'no_context')
                            print(f"    Found potential: {tag_name} = {value:,.0f} (context: {context_ref})")
                except (ValueError, TypeError):
                    continue
        
        print("  === Searching specific tags ===")
        for tag in tags:
            namespace = tag.split(":")[0]
            tag_name = tag.split(":")[1]
            namespace_uris = self.namespaces.get(namespace, [])
            
            for namespace_uri in namespace_uris:
                # 全ての該当要素を検索
                elements = root.findall(f'.//{{{namespace_uri}}}{tag_name}')
                
                for element in elements:
                    try:
                        value = float(element.text or 0)
                        context_ref = element.get('contextRef', 'no_context')
                        found_data.append({
                            'tag': tag,
                            'value': value,
                            'context': context_ref,
                            'text': element.text
                        })
                        print(f"  Found: {tag} = {value:,.0f} (context: {context_ref})")
                    except (ValueError, TypeError):
                        continue
        
        return found_data
    
    def _debug_dividend_income(self, root):
        """配当金収入の詳細デバッグ"""
        tags = [
            'jppfs_cor:DividendsIncomeNOI',
            'jppfs_cor:InterestAndDividendsIncomeNOI',
            'jppfs_cor:DividendIncome',
            'jppfs_cor:DividendIncomeNonOperatingIncome',
            'jppfs_cor:DividendIncomeOperatingIncome',
            'jppfs_cor:DividendIncomeSubsidiariesAndAffiliates',
            'jppfs_cor:InterestAndDividendsIncome'
        ]
        
        found_data = []
        
        # まず全ての数値要素を検索してパターンを把握
        print("  === All numeric elements containing 'dividend' or 'interest' ===")
        all_elements = root.findall('.//*')
        dividend_keywords = ['dividend', 'interest', 'income']
        
        for element in all_elements:
            if element.text and element.text.strip():
                try:
                    value = float(element.text)
                    if value > 0:
                        tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
                        if any(keyword.lower() in tag_name.lower() for keyword in dividend_keywords):
                            context_ref = element.get('contextRef', 'no_context')
                            print(f"    Found potential: {tag_name} = {value:,.0f} (context: {context_ref})")
                except (ValueError, TypeError):
                    continue
        
        print("  === Searching specific tags ===")
        for tag in tags:
            namespace = tag.split(":")[0]
            tag_name = tag.split(":")[1]
            namespace_uris = self.namespaces.get(namespace, [])
            
            for namespace_uri in namespace_uris:
                elements = root.findall(f'.//{{{namespace_uri}}}{tag_name}')
                
                for element in elements:
                    try:
                        value = float(element.text or 0)
                        context_ref = element.get('contextRef', 'no_context')
                        found_data.append({
                            'tag': tag,
                            'value': value,
                            'context': context_ref,
                            'text': element.text
                        })
                        print(f"  Found: {tag} = {value:,.0f} (context: {context_ref})")
                    except (ValueError, TypeError):
                        continue
        
        return found_data
    
    def _debug_issued_shares(self, root):
        """発行済み株式数の詳細デバッグ"""
        tags = [
            'jpcrp_cor:NumberOfIssuedSharesAsOfFiscalYearEndIssuedSharesTotalNumberOfSharesEtc',
            'jpcrp_cor:TotalNumberOfIssuedSharesSummaryOfBusinessResults',
            'jpcrp_cor:NumberOfIssuedSharesAsOfFiscalYearEnd',
            'jpcrp_cor:TotalNumberOfIssuedShares',
            'jppfs_cor:NumberOfIssuedSharesStockholdersEquityTotal'
        ]
        
        found_data = []
        
        for tag in tags:
            namespace = tag.split(":")[0]
            tag_name = tag.split(":")[1]
            namespace_uris = self.namespaces.get(namespace, [])
            
            for namespace_uri in namespace_uris:
                elements = root.findall(f'.//{{{namespace_uri}}}{tag_name}')
                
                for element in elements:
                    try:
                        value = float(element.text or 0)
                        context_ref = element.get('contextRef', 'no_context')
                        found_data.append({
                            'tag': tag,
                            'value': value,
                            'context': context_ref,
                            'text': element.text
                        })
                        print(f"  Found: {tag} = {value:,.0f} (context: {context_ref})")
                    except (ValueError, TypeError):
                        continue
        
        return found_data

def main():
    debugger = XBRLDebugger()
    
    # 問題のある企業のファイルを調査
    test_files = [
        ("/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl/S100W0BE/XBRL/PublicDoc/jpcrp030000-asr-001_E04500-000_2025-03-31_01_2025-06-24.xbrl", "北海道電力 (9509)"),
    ]
    
    for file_path, company_name in test_files:
        try:
            result = debugger.debug_file(file_path, company_name)
            print(f"\n" + "="*80 + "\n")
        except Exception as e:
            print(f"Error processing {company_name}: {e}")

if __name__ == "__main__":
    main()