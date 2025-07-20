#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XBRL財務分析システム
EDINETからダウンロードしたXBRLファイルを解析し、企業の投資有価証券と配当収益を抽出して財務分析を行う
"""

import pandas as pd
import numpy as np
import yfinance as yf
import re
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import requests
import glob
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class XBRLFinancialAnalyzer:
    """XBRL財務分析システムのメインクラス"""
    
    def __init__(self, xbrl_base_path: str = "xbrl"):
        """
        初期化
        
        Args:
            xbrl_base_path: XBRLファイルのベースパス
        """
        self.xbrl_base_path = xbrl_base_path
        self.edinet_mapping = None
        self.results = []
        
        # XBRLネームスペース定義（複数バージョン対応）
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
            ],
            'xbrli': ['http://www.xbrl.org/2003/instance']
        }
        
        # ファイルサイズ制限 (50MB)
        self.max_file_size = 50 * 1024 * 1024
        # 最小値制限
        self.min_value = 1000000  # 100万
        self.min_shares = 1000  # 発行済み株式数の最小値（1000株）
        
        # 業種別のネームスペース定義を追加
        self.namespaces.update({
            'jppfs_bk': [  # 銀行業用タクソノミー
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2023-12-01/jppfs_bk',
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2022-11-01/jppfs_bk',
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2019-11-01/jppfs_bk'
            ],
            'jppfs_in1': [  # 保険業用タクソノミー
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2023-12-01/jppfs_in1',
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2022-11-01/jppfs_in1'
            ],
            'jppfs_sec': [  # 証券業用タクソノミー
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2023-12-01/jppfs_sec',
                'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2022-11-01/jppfs_sec'
            ],
            'ifrs': [  # IFRS用タクソノミー
                'http://xbrl.ifrs.org/taxonomy/2023-03-23/ifrs-full',
                'http://xbrl.ifrs.org/taxonomy/2022-03-24/ifrs-full'
            ]
        })
        
        # 業種別タグマッピング
        self.bank_indicators_tags = {
            # 銀行業特有の指標
            'interest_income_cy': ['jppfs_bk:InterestIncome', 'jpcrp_cor:InterestIncomeSummaryOfBusinessResults'],
            'interest_income_py1': ['jppfs_bk:InterestIncomePY1', 'jpcrp_cor:InterestIncomeSummaryOfBusinessResultsPY1'],
            'interest_expenses_cy': ['jppfs_bk:InterestExpenses'],
            'interest_expenses_py1': ['jppfs_bk:InterestExpensesPY1'],
            'net_interest_income_cy': ['jppfs_bk:NetInterestIncome'],
            'net_interest_income_py1': ['jppfs_bk:NetInterestIncomePY1'],
            'trust_fees_cy': ['jppfs_bk:TrustFees'],
            'trust_fees_py1': ['jppfs_bk:TrustFeesPY1'],
            'trading_income_cy': ['jppfs_bk:TradingIncome'],
            'trading_income_py1': ['jppfs_bk:TradingIncomePY1'],
            'other_operating_income_cy': ['jppfs_bk:OtherOperatingIncome'],
            'other_operating_income_py1': ['jppfs_bk:OtherOperatingIncomePY1'],
            'general_administrative_expenses_cy': ['jppfs_bk:GeneralAndAdministrativeExpenses'],
            'general_administrative_expenses_py1': ['jppfs_bk:GeneralAndAdministrativeExpensesPY1'],
            'provision_for_allowance_cy': ['jppfs_bk:ProvisionForAllowanceForCreditLosses'],
            'provision_for_allowance_py1': ['jppfs_bk:ProvisionForAllowanceForCreditLossesPY1'],
            'loans_and_bills_discounted_cy': ['jppfs_bk:LoansAndBillsDiscounted'],
            'loans_and_bills_discounted_py1': ['jppfs_bk:LoansAndBillsDiscountedPY1'],
            'deposits_cy': ['jppfs_bk:Deposits'],
            'deposits_py1': ['jppfs_bk:DepositsPY1'],
            'capital_adequacy_ratio_cy': ['jppfs_bk:CapitalAdequacyRatio'],
            'capital_adequacy_ratio_py1': ['jppfs_bk:CapitalAdequacyRatioPY1']
        }
        
        # IFRS指標タグマッピング
        self.ifrs_indicators_tags = {
            'revenue_cy': ['ifrs:Revenue', 'jpcrp_cor:NetSalesSummaryOfBusinessResults'],
            'revenue_py1': ['ifrs:RevenuePY1', 'jpcrp_cor:NetSalesSummaryOfBusinessResultsPY1'],
            'operating_profit_cy': ['ifrs:OperatingProfit', 'jpcrp_cor:OperatingIncomeSummaryOfBusinessResults'],
            'operating_profit_py1': ['ifrs:OperatingProfitPY1', 'jpcrp_cor:OperatingIncomeSummaryOfBusinessResultsPY1'],
            'profit_before_tax_cy': ['ifrs:ProfitLossBeforeTax'],
            'profit_before_tax_py1': ['ifrs:ProfitLossBeforeTaxPY1'],
            'profit_cy': ['ifrs:ProfitLoss', 'jpcrp_cor:NetIncomeSummaryOfBusinessResults'],
            'profit_py1': ['ifrs:ProfitLossPY1', 'jpcrp_cor:NetIncomeSummaryOfBusinessResultsPY1'],
            'total_assets_cy': ['ifrs:Assets', 'jpcrp_cor:TotalAssetsSummaryOfBusinessResults'],
            'total_assets_py1': ['ifrs:AssetsPY1', 'jpcrp_cor:TotalAssetsSummaryOfBusinessResultsPY1'],
            'total_equity_cy': ['ifrs:Equity', 'jpcrp_cor:NetAssetsSummaryOfBusinessResults'],
            'total_equity_py1': ['ifrs:EquityPY1', 'jpcrp_cor:NetAssetsSummaryOfBusinessResultsPY1'],
            'basic_earnings_per_share_cy': ['ifrs:BasicEarningsLossPerShare'],
            'basic_earnings_per_share_py1': ['ifrs:BasicEarningsLossPerSharePY1']
        }
        
        # 連結経営指標等のタグマッピング（1章の主要指標）
        self.management_indicators_tags = {
            # 売上高・収益
            'net_sales_cy': ['jpcrp_cor:NetSalesSummaryOfBusinessResults', 'jppfs_cor:NetSales'],
            'net_sales_py1': ['jpcrp_cor:NetSalesSummaryOfBusinessResultsPY1', 'jppfs_cor:NetSalesPY1'],
            'net_sales_py2': ['jpcrp_cor:NetSalesSummaryOfBusinessResultsPY2', 'jppfs_cor:NetSalesPY2'],
            'net_sales_py3': ['jpcrp_cor:NetSalesSummaryOfBusinessResultsPY3', 'jppfs_cor:NetSalesPY3'],
            'net_sales_py4': ['jpcrp_cor:NetSalesSummaryOfBusinessResultsPY4', 'jppfs_cor:NetSalesPY4'],
            
            # 営業利益
            'operating_income_cy': ['jpcrp_cor:OperatingIncomeSummaryOfBusinessResults', 'jppfs_cor:OperatingIncome'],
            'operating_income_py1': ['jpcrp_cor:OperatingIncomeSummaryOfBusinessResultsPY1', 'jppfs_cor:OperatingIncomePY1'],
            'operating_income_py2': ['jpcrp_cor:OperatingIncomeSummaryOfBusinessResultsPY2', 'jppfs_cor:OperatingIncomePY2'],
            'operating_income_py3': ['jpcrp_cor:OperatingIncomeSummaryOfBusinessResultsPY3', 'jppfs_cor:OperatingIncomePY3'],
            'operating_income_py4': ['jpcrp_cor:OperatingIncomeSummaryOfBusinessResultsPY4', 'jppfs_cor:OperatingIncomePY4'],
            
            # 経常利益
            'ordinary_income_cy': ['jpcrp_cor:OrdinaryIncomeSummaryOfBusinessResults', 'jppfs_cor:OrdinaryIncome'],
            'ordinary_income_py1': ['jpcrp_cor:OrdinaryIncomeSummaryOfBusinessResultsPY1', 'jppfs_cor:OrdinaryIncomePY1'],
            'ordinary_income_py2': ['jpcrp_cor:OrdinaryIncomeSummaryOfBusinessResultsPY2', 'jppfs_cor:OrdinaryIncomePY2'],
            'ordinary_income_py3': ['jpcrp_cor:OrdinaryIncomeSummaryOfBusinessResultsPY3', 'jppfs_cor:OrdinaryIncomePY3'],
            'ordinary_income_py4': ['jpcrp_cor:OrdinaryIncomeSummaryOfBusinessResultsPY4', 'jppfs_cor:OrdinaryIncomePY4'],
            
            # 当期純利益
            'net_income_cy': ['jpcrp_cor:NetIncomeSummaryOfBusinessResults', 'jppfs_cor:NetIncome'],
            'net_income_py1': ['jpcrp_cor:NetIncomeSummaryOfBusinessResultsPY1', 'jppfs_cor:NetIncomePY1'],
            'net_income_py2': ['jpcrp_cor:NetIncomeSummaryOfBusinessResultsPY2', 'jppfs_cor:NetIncomePY2'],
            'net_income_py3': ['jpcrp_cor:NetIncomeSummaryOfBusinessResultsPY3', 'jppfs_cor:NetIncomePY3'],
            'net_income_py4': ['jpcrp_cor:NetIncomeSummaryOfBusinessResultsPY4', 'jppfs_cor:NetIncomePY4'],
            
            # 包括利益
            'comprehensive_income_cy': ['jpcrp_cor:ComprehensiveIncomeSummaryOfBusinessResults', 'jppfs_cor:ComprehensiveIncome'],
            'comprehensive_income_py1': ['jpcrp_cor:ComprehensiveIncomeSummaryOfBusinessResultsPY1'],
            'comprehensive_income_py2': ['jpcrp_cor:ComprehensiveIncomeSummaryOfBusinessResultsPY2'],
            'comprehensive_income_py3': ['jpcrp_cor:ComprehensiveIncomeSummaryOfBusinessResultsPY3'],
            'comprehensive_income_py4': ['jpcrp_cor:ComprehensiveIncomeSummaryOfBusinessResultsPY4'],
            
            # 総資産
            'total_assets_cy': ['jpcrp_cor:TotalAssetsSummaryOfBusinessResults', 'jppfs_cor:TotalAssets'],
            'total_assets_py1': ['jpcrp_cor:TotalAssetsSummaryOfBusinessResultsPY1', 'jppfs_cor:TotalAssetsPY1'],
            'total_assets_py2': ['jpcrp_cor:TotalAssetsSummaryOfBusinessResultsPY2', 'jppfs_cor:TotalAssetsPY2'],
            'total_assets_py3': ['jpcrp_cor:TotalAssetsSummaryOfBusinessResultsPY3', 'jppfs_cor:TotalAssetsPY3'],
            'total_assets_py4': ['jpcrp_cor:TotalAssetsSummaryOfBusinessResultsPY4', 'jppfs_cor:TotalAssetsPY4'],
            
            # 純資産
            'net_assets_cy': ['jpcrp_cor:NetAssetsSummaryOfBusinessResults', 'jppfs_cor:NetAssets'],
            'net_assets_py1': ['jpcrp_cor:NetAssetsSummaryOfBusinessResultsPY1', 'jppfs_cor:NetAssetsPY1'],
            'net_assets_py2': ['jpcrp_cor:NetAssetsSummaryOfBusinessResultsPY2', 'jppfs_cor:NetAssetsPY2'],
            'net_assets_py3': ['jpcrp_cor:NetAssetsSummaryOfBusinessResultsPY3', 'jppfs_cor:NetAssetsPY3'],
            'net_assets_py4': ['jpcrp_cor:NetAssetsSummaryOfBusinessResultsPY4', 'jppfs_cor:NetAssetsPY4'],
            
            # 1株当たり指標
            'earnings_per_share_cy': ['jpcrp_cor:BasicEarningsPerShareSummaryOfBusinessResults'],
            'earnings_per_share_py1': ['jpcrp_cor:BasicEarningsPerShareSummaryOfBusinessResultsPY1'],
            'earnings_per_share_py2': ['jpcrp_cor:BasicEarningsPerShareSummaryOfBusinessResultsPY2'],
            'earnings_per_share_py3': ['jpcrp_cor:BasicEarningsPerShareSummaryOfBusinessResultsPY3'],
            'earnings_per_share_py4': ['jpcrp_cor:BasicEarningsPerShareSummaryOfBusinessResultsPY4'],
            
            'net_assets_per_share_cy': ['jpcrp_cor:NetAssetsPerShareSummaryOfBusinessResults'],
            'net_assets_per_share_py1': ['jpcrp_cor:NetAssetsPerShareSummaryOfBusinessResultsPY1'],
            'net_assets_per_share_py2': ['jpcrp_cor:NetAssetsPerShareSummaryOfBusinessResultsPY2'],
            'net_assets_per_share_py3': ['jpcrp_cor:NetAssetsPerShareSummaryOfBusinessResultsPY3'],
            'net_assets_per_share_py4': ['jpcrp_cor:NetAssetsPerShareSummaryOfBusinessResultsPY4'],
            
            # 財務比率
            'equity_ratio_cy': ['jpcrp_cor:EquityToTotalAssetsRatioSummaryOfBusinessResults'],
            'equity_ratio_py1': ['jpcrp_cor:EquityToTotalAssetsRatioSummaryOfBusinessResultsPY1'],
            'equity_ratio_py2': ['jpcrp_cor:EquityToTotalAssetsRatioSummaryOfBusinessResultsPY2'],
            'equity_ratio_py3': ['jpcrp_cor:EquityToTotalAssetsRatioSummaryOfBusinessResultsPY3'],
            'equity_ratio_py4': ['jpcrp_cor:EquityToTotalAssetsRatioSummaryOfBusinessResultsPY4'],
            
            'roa_cy': ['jpcrp_cor:ReturnOnAssetsSummaryOfBusinessResults'],
            'roa_py1': ['jpcrp_cor:ReturnOnAssetsSummaryOfBusinessResultsPY1'],
            'roa_py2': ['jpcrp_cor:ReturnOnAssetsSummaryOfBusinessResultsPY2'],
            'roa_py3': ['jpcrp_cor:ReturnOnAssetsSummaryOfBusinessResultsPY3'],
            'roa_py4': ['jpcrp_cor:ReturnOnAssetsSummaryOfBusinessResultsPY4'],
            
            'roe_cy': ['jpcrp_cor:ReturnOnEquitySummaryOfBusinessResults'],
            'roe_py1': ['jpcrp_cor:ReturnOnEquitySummaryOfBusinessResultsPY1'],
            'roe_py2': ['jpcrp_cor:ReturnOnEquitySummaryOfBusinessResultsPY2'],
            'roe_py3': ['jpcrp_cor:ReturnOnEquitySummaryOfBusinessResultsPY3'],
            'roe_py4': ['jpcrp_cor:ReturnOnEquitySummaryOfBusinessResultsPY4'],
            
            # 従業員数
            'employees_cy': ['jpcrp_cor:NumberOfEmployees'],
            'employees_py1': ['jpcrp_cor:NumberOfEmployeesPY1'],
            'employees_py2': ['jpcrp_cor:NumberOfEmployeesPY2'],
            'employees_py3': ['jpcrp_cor:NumberOfEmployeesPY3'],
            'employees_py4': ['jpcrp_cor:NumberOfEmployeesPY4'],
        }
    
    def load_edinet_mapping(self) -> bool:
        """
        EDINETコードマッピングテーブルを読み込む
        
        Returns:
            bool: 読み込み成功の可否
        """
        logger.info("EDINETコードマッピングテーブルを読み込み中...")
        
        try:
            # HTMLテーブルから読み込み
            url = "https://code4fukui.github.io/EDINET/seccode.html"
            tables = pd.read_html(url, encoding='utf-8')
            
            if len(tables) > 0:
                df = tables[0]
                # カラム名を確認して適切に設定
                if len(df.columns) >= 3:
                    df.columns = ['edinet_code', 'security_code', 'company_name']
                    
                    # 証券コードの処理（5桁の場合は4桁に変換）
                    df['stock_code'] = df['security_code'].astype(str).apply(
                        lambda x: x[:4] if len(x) == 5 else x
                    )
                    
                    self.edinet_mapping = df
                    logger.info(f"EDINETマッピングテーブル読み込み完了: {len(df)}件")
                    return True
                    
        except Exception as e:
            logger.warning(f"HTMLテーブル読み込み失敗: {e}")
            
        # フォールバック: CSVファイルから読み込み
        try:
            csv_path = "downloads/extracted/EdinetcodeDlInfo.csv"
            if os.path.exists(csv_path):
                # 複数のエンコーディングを試す
                encodings = ['utf-8', 'shift_jis', 'cp932', 'euc-jp']
                for encoding in encodings:
                    try:
                        df = pd.read_csv(csv_path, encoding=encoding, skiprows=1)  # ヘッダー行をスキップ
                        # カラム名の確認と調整
                        if len(df.columns) >= 13:
                            # 正しい列名を設定（実際のCSVファイル構造に基づく）
                            expected_cols = ['edinet_code', 'submitter_type', 'market_division', 
                                           'consolidated', 'capital', 'settlement_date', 'company_name',
                                           'company_name_english', 'company_name_kana', 'location', 
                                           'industry', 'security_code', 'corporate_number']
                            
                            # データフレームの列数に合わせて調整
                            df.columns = expected_cols[:len(df.columns)]
                            
                            # EDINETコード、証券コード、企業名、業種の列を選択
                            df = df[['edinet_code', 'security_code', 'company_name', 'industry']].copy()
                            
                            # データクリーニング
                            df['edinet_code'] = df['edinet_code'].astype(str).str.strip().str.strip('"')
                            df['security_code'] = df['security_code'].astype(str).str.strip().str.strip('"')
                            df['company_name'] = df['company_name'].astype(str).str.strip().str.strip('"')
                            df['industry'] = df['industry'].astype(str).str.strip().str.strip('"')
                            
                            # 無効なデータをフィルタリング
                            df = df[df['edinet_code'].str.startswith('E')]
                            df = df[pd.to_numeric(df['security_code'], errors='coerce').notna()]
                            df = df[df['security_code'] != 'nan']
                            
                            # 証券コードの処理（末尾の0を削除して適切な桁数に変換）
                            df['stock_code'] = df['security_code'].apply(self._clean_stock_code)
                            
                            # NaNや空の値を除外
                            df = df.dropna()
                            df = df[df['stock_code'] != 'nan']
                            
                            self.edinet_mapping = df
                            logger.info(f"CSVからEDINETマッピング読み込み完了: {len(df)}件 (エンコーディング: {encoding})")
                            return True
                        break
                    except UnicodeDecodeError:
                        continue
                
        except Exception as e:
            logger.error(f"CSVファイル読み込み失敗: {e}")
            
        return False
    
    def find_xbrl_files(self) -> List[str]:
        """
        XBRLファイルを検索する
        
        Returns:
            List[str]: XBRLファイルパスのリスト
        """
        logger.info("XBRLファイルを検索中...")
        
        pattern = os.path.join(
            self.xbrl_base_path,
            "S100*/XBRL/PublicDoc/jpcrp030000-asr-001_E*-000_*-*-*_*_*-*-*.xbrl"
        )
        
        files = glob.glob(pattern)
        logger.info(f"発見されたXBRLファイル数: {len(files)}")
        
        # ファイルサイズでフィルタリング
        valid_files = []
        for file_path in files:
            try:
                if os.path.getsize(file_path) <= self.max_file_size:
                    valid_files.append(file_path)
                else:
                    logger.warning(f"ファイルサイズが大きすぎるためスキップ: {file_path}")
            except OSError:
                logger.warning(f"ファイルアクセスエラー: {file_path}")
                
        logger.info(f"有効なXBRLファイル数: {len(valid_files)}")
        return valid_files
    
    def extract_edinet_code(self, file_path: str) -> Optional[str]:
        """
        ファイルパスからEDINETコードを抽出する
        
        Args:
            file_path: XBRLファイルパス
            
        Returns:
            Optional[str]: EDINETコード
        """
        match = re.search(r'(E\d{5})-\d{3}', file_path)
        return match.group(1) if match else None
    
    def get_company_info(self, edinet_code: str) -> Optional[Tuple[str, str]]:
        """
        EDINETコードから企業情報を取得する
        
        Args:
            edinet_code: EDINETコード
            
        Returns:
            Optional[Tuple[str, str]]: (銘柄コード, 企業名)
        """
        if self.edinet_mapping is None:
            return None
            
        try:
            mask = self.edinet_mapping['edinet_code'] == edinet_code
            matching_rows = self.edinet_mapping[mask]
            
            if not matching_rows.empty:
                row = matching_rows.iloc[0]
                stock_code = str(row['stock_code'])
                company_name = str(row['company_name'])
                return stock_code, company_name
                
        except Exception as e:
            logger.warning(f"企業情報取得エラー {edinet_code}: {e}")
            
        return None
    
    def _clean_stock_code(self, sec_code):
        """証券コードから末尾の0を削除して適切な桁数にする"""
        if pd.isna(sec_code):
            return None
        
        # 数値に変換してから文字列に戻す（先頭の0を除去）
        try:
            code_num = int(float(sec_code))
            code_str = str(code_num)
            
            # 末尾の0を削除（ただし、全て0になることは避ける）
            while len(code_str) > 1 and code_str.endswith('0'):
                code_str = code_str[:-1]
            
            return code_str
        except (ValueError, TypeError):
            return None
    
    def _detect_company_type(self, edinet_code: str) -> str:
        """EDINETコードから企業の業種タイプを判定する"""
        if self.edinet_mapping is None:
            return 'general'
        
        try:
            mask = self.edinet_mapping['edinet_code'] == edinet_code
            matching_rows = self.edinet_mapping[mask]
            
            if not matching_rows.empty:
                # 実際のCSV構造に基づいて業種列を取得
                if 'industry' in self.edinet_mapping.columns:
                    industry = str(matching_rows.iloc[0]['industry'])
                elif len(self.edinet_mapping.columns) >= 11:
                    industry = str(matching_rows.iloc[0].iloc[10])  # 11列目が業種
                else:
                    return 'general'
                
                # 業種に基づいて企業タイプを判定
                if '銀行' in industry:
                    return 'bank'
                elif '保険' in industry:
                    return 'insurance'
                elif '証券' in industry:
                    return 'securities'
                elif '卸売' in industry:
                    return 'trading'
                else:
                    return 'general'
        except Exception as e:
            logger.debug(f"企業タイプ判定エラー {edinet_code}: {e}")
        
        return 'general'
    
    def _detect_accounting_standard(self, root) -> str:
        """XBRLファイルから会計基準（J-GAAP/IFRS）を判定する"""
        # IFRSタクソノミーの使用をチェック
        xml_str = ET.tostring(root, encoding='unicode')
        
        ifrs_indicators = [
            'ifrs-full',
            'http://xbrl.ifrs.org',
            'ifrs:Revenue',
            'ifrs:Assets',
            'ifrs:Equity'
        ]
        
        for indicator in ifrs_indicators:
            if indicator in xml_str:
                return 'ifrs'
        
        return 'jgaap'
    
    def extract_management_indicators(self, root, company_type: str = 'general', accounting_standard: str = 'jgaap') -> Dict[str, Optional[float]]:
        """
        連結経営指標等を抽出（1章の主要指標）
        
        Args:
            root: XBRLのrootエレメント
            company_type: 企業タイプ ('general', 'bank', 'insurance', 'securities', 'trading')
            accounting_standard: 会計基準 ('jgaap', 'ifrs')
            
        Returns:
            Dict[str, Optional[float]]: 連結経営指標のデータ
        """
        indicators = {}
        
        logger.info(f"連結経営指標等を抽出中... (企業タイプ: {company_type}, 会計基準: {accounting_standard})")
        
        # 業種と会計基準に応じたタグセットを選択
        tag_sets = [self.management_indicators_tags]
        
        if company_type == 'bank':
            tag_sets.append(self.bank_indicators_tags)
        elif accounting_standard == 'ifrs':
            tag_sets.append(self.ifrs_indicators_tags)
        
        # 各タグセットから指標を抽出
        for tag_set in tag_sets:
            for indicator_name, tags in tag_set.items():
                # 既に抽出済みの場合はスキップ
                if indicator_name in indicators and indicators[indicator_name] is not None:
                    continue
                
                # 期間に応じたコンテキストパターンを設定
                if 'cy' in indicator_name:  # 当期
                    context_patterns = [
                        'CurrentYearDuration',
                        'CurrentYearInstant',
                        'CurrentYearDuration_ConsolidatedMember',
                        'CurrentYearInstant_ConsolidatedMember'
                    ]
                elif 'py1' in indicator_name:  # 前期
                    context_patterns = [
                        'Prior1YearDuration',
                        'Prior1YearInstant',
                        'Prior1YearDuration_ConsolidatedMember',
                        'Prior1YearInstant_ConsolidatedMember'
                    ]
                elif 'py2' in indicator_name:  # 前々期
                    context_patterns = [
                        'Prior2YearDuration',
                        'Prior2YearInstant',
                        'Prior2YearDuration_ConsolidatedMember',
                        'Prior2YearInstant_ConsolidatedMember'
                    ]
                elif 'py3' in indicator_name:  # 3期前
                    context_patterns = [
                        'Prior3YearDuration',
                        'Prior3YearInstant',
                        'Prior3YearDuration_ConsolidatedMember',
                        'Prior3YearInstant_ConsolidatedMember'
                    ]
                elif 'py4' in indicator_name:  # 4期前
                    context_patterns = [
                        'Prior4YearDuration',
                        'Prior4YearInstant',
                        'Prior4YearDuration_ConsolidatedMember',
                        'Prior4YearInstant_ConsolidatedMember'
                    ]
                else:
                    context_patterns = [
                        'CurrentYearDuration',
                        'CurrentYearInstant',
                        'CurrentYearDuration_ConsolidatedMember',
                        'CurrentYearInstant_ConsolidatedMember'
                    ]
                
                # 各コンテキストパターンでタグを検索
                value = None
                for context_pattern in context_patterns:
                    value = self._extract_value_by_tags(root, tags, context_pattern, use_min_shares=False)
                    if value is not None:
                        break
                
                indicators[indicator_name] = value
                if value is not None:
                    logger.debug(f"抽出成功: {indicator_name} = {value:,.0f}")
        
        # 抽出成功した指標数をログ出力
        extracted_count = sum(1 for v in indicators.values() if v is not None)
        logger.info(f"連結経営指標抽出完了: {extracted_count}/{len(indicators)}項目")
        
        return indicators
    
    def extract_financial_data(self, file_path: str) -> Dict[str, Optional[float]]:
        """
        XBRLファイルから財務データを抽出する
        
        Args:
            file_path: XBRLファイルパス
            
        Returns:
            Dict[str, Optional[float]]: 財務データ
        """
        result = {
            'investment_securities': None,
            'prior_investment_securities': None,
            'dividend_income': None,
            'prior_dividend_income': None,
            'issued_shares': None,
            'current_net_sales': None,
            'prior_net_sales': None,
            'operating_income': None
        }
        
        try:
            # XMLファイルを解析
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 投資有価証券の抽出（当期・前期）
            result['investment_securities'] = self._extract_investment_securities(root, 'current')
            result['prior_investment_securities'] = self._extract_investment_securities(root, 'prior')
            
            # 受取配当金の抽出（当期・前期）
            result['dividend_income'] = self._extract_dividend_income(root, 'current')
            result['prior_dividend_income'] = self._extract_dividend_income(root, 'prior')
            
            # 発行済み株式数の抽出
            result['issued_shares'] = self._extract_issued_shares(root)
            
            # 売上高の抽出（当期・前期）
            result['current_net_sales'] = self._extract_net_sales(root, 'CurrentYearDuration')
            result['prior_net_sales'] = self._extract_net_sales(root, 'Prior1YearDuration')
            
            # 営業利益の抽出
            result['operating_income'] = self._extract_operating_income(root)
            
            # EDINETコードから企業タイプを判定
            edinet_code = self.extract_edinet_code(file_path)
            company_type = self._detect_company_type(edinet_code) if edinet_code else 'general'
            accounting_standard = self._detect_accounting_standard(root)
            
            # 連結経営指標等の抽出
            management_indicators = self.extract_management_indicators(root, company_type, accounting_standard)
            result.update(management_indicators)
            
        except Exception as e:
            logger.error(f"財務データ抽出エラー {file_path}: {e}")
            
        return result
    
    def _extract_investment_securities(self, root, period: str = 'current') -> Optional[float]:
        """投資有価証券を抽出（改善版）"""
        # より包括的なタグリスト（子会社・関連会社株式を除外）
        tags = [
            'jppfs_cor:InvestmentSecurities',  # 投資有価証券
            'jppfs_cor:InvestmentSecuritiesNoncurrentAssets',  # 固定資産の投資有価証券
            'jppfs_cor:InvestmentSecuritiesCurrentAssets',  # 流動資産の投資有価証券
            'jppfs_cor:LongTermInvestmentsELE',  # 長期投資（子会社以外）
            'jppfs_cor:InvestmentSecuritiesAndInvestmentAccountsReceivable',  # 投資有価証券及び出資金
            'jppfs_cor:MarketableSecurities',  # 有価証券
            'jppfs_cor:MarketableSecuritiesCA',  # 流動資産の有価証券
            'jppfs_cor:AvailableForSaleSecurities',  # その他有価証券
            'jppfs_cor:EquitySecurities',  # 株式
            'jppfs_cor:BondsHeldToMaturity',  # 満期保有目的の債券
            'jppfs_cor:OtherSecuritiesCA',  # その他の有価証券（流動）
            'jppfs_cor:OtherSecuritiesIA'  # その他の有価証券（固定）
        ]
        
        # 期間に応じたコンテキストパターンを設定
        if period == 'current':
            context_patterns = [
                'CurrentYearInstant',
                'CurrentYearInstant_NonConsolidatedMember',
                'FilingDateInstant',
                'FilingDateInstant_NonConsolidatedMember'
            ]
        else:  # prior
            context_patterns = [
                'Prior1YearInstant',
                'Prior1YearInstant_NonConsolidatedMember'
            ]
        
        # 最大値を取得（複数の項目がある場合）
        max_value = None
        for context_pattern in context_patterns:
            result = self._extract_value_by_tags(root, tags, context_pattern)
            if result and (max_value is None or result > max_value):
                max_value = result
                
        return max_value
    
    def _extract_dividend_income(self, root, period: str = 'current') -> Optional[float]:
        """受取配当金を抽出"""
        tags = [
            'jppfs_cor:DividendsIncomeNOI',  # 受取配当金（営業外収益）
            'jppfs_cor:InterestAndDividendsIncomeNOI',  # 受取利息及び配当金
            'jppfs_cor:DividendIncome',
            'jppfs_cor:DividendIncomeNonOperatingIncome',
            'jppfs_cor:DividendIncomeOperatingIncome',
            'jppfs_cor:DividendIncomeSubsidiariesAndAffiliates',
            'jppfs_cor:InterestAndDividendsIncome'
        ]
        
        # 期間に応じたコンテキストパターンを設定
        if period == 'current':
            context_patterns = [
                'CurrentYearDuration',
                'CurrentYearDuration_NonConsolidatedMember',
                'CurrentYearDuration_ConsolidatedMember'
            ]
        else:  # prior
            context_patterns = [
                'Prior1YearDuration',
                'Prior1YearDuration_NonConsolidatedMember',
                'Prior1YearDuration_ConsolidatedMember'
            ]
        
        for context_pattern in context_patterns:
            result = self._extract_value_by_tags(root, tags, context_pattern)
            if result:
                return result
                
        return None
    
    def _extract_issued_shares(self, root) -> Optional[float]:
        """発行済み株式数を抽出"""
        tags = [
            'jpcrp_cor:NumberOfIssuedSharesAsOfFiscalYearEndIssuedSharesTotalNumberOfSharesEtc',
            'jpcrp_cor:TotalNumberOfIssuedSharesSummaryOfBusinessResults',
            'jpcrp_cor:NumberOfIssuedSharesAsOfFiscalYearEnd',
            'jpcrp_cor:TotalNumberOfIssuedShares',
            'jppfs_cor:NumberOfIssuedSharesStockholdersEquityTotal'
        ]
        
        # 複数のコンテキストパターンを試す
        context_patterns = [
            'CurrentYearInstant',
            'FilingDateInstant',
            'CurrentYearInstant_NonConsolidatedMember',
            'FilingDateInstant_OrdinaryShareMember'
        ]
        
        for context_pattern in context_patterns:
            result = self._extract_value_by_tags(root, tags, context_pattern, use_min_shares=True)
            if result:
                return result
                
        return None
    
    def _extract_net_sales(self, root, context_type: str) -> Optional[float]:
        """売上高を抽出"""
        tags = [
            'jppfs_cor:NetSales',  # 売上高
            'jppfs_cor:Revenue',  # 営業収益
            'jpcrp_cor:NetSalesSummaryOfBusinessResults',  # 売上高（業績サマリー）
            'jppfs_cor:OperatingRevenue',  # 営業収益
            'jppfs_cor:TotalRevenues'  # 総収益
        ]
        
        # 複数のコンテキストパターンを試す
        context_patterns = [
            context_type,
            f'{context_type}_NonConsolidatedMember',
            f'{context_type}_ConsolidatedMember'
        ]
        
        for context_pattern in context_patterns:
            result = self._extract_value_by_tags(root, tags, context_pattern)
            if result:
                return result
                
        return None
    
    def _extract_operating_income(self, root) -> Optional[float]:
        """営業利益を抽出"""
        tags = [
            'jppfs_cor:OperatingIncome',  # 営業利益
            'jppfs_cor:OperatingProfit',  # 営業利益
            'jpcrp_cor:OperatingIncomeSummaryOfBusinessResults',  # 営業利益（業績サマリー）
            'jppfs_cor:IncomeFromOperations'  # 営業利益
        ]
        
        # 複数のコンテキストパターンを試す
        context_patterns = [
            'CurrentYearDuration',
            'CurrentYearDuration_NonConsolidatedMember',
            'CurrentYearDuration_ConsolidatedMember'
        ]
        
        for context_pattern in context_patterns:
            result = self._extract_value_by_tags(root, tags, context_pattern)
            if result:
                return result
                
        return None
    
    def _extract_value_by_tags(self, root, tags: List[str], context_type: str, use_min_shares: bool = False) -> Optional[float]:
        """指定されたタグから値を抽出"""
        min_threshold = self.min_shares if use_min_shares else self.min_value
        
        for tag in tags:
            namespace = tag.split(":")[0]
            tag_name = tag.split(":")[1]
            namespace_uris = self.namespaces.get(namespace, [])
            
            if not isinstance(namespace_uris, list):
                namespace_uris = [namespace_uris]
            
            for namespace_uri in namespace_uris:
                if namespace_uri:
                    # 複数の方法で要素を検索
                    search_patterns = [
                        f'.//{{{namespace_uri}}}{tag_name}',
                        f'.//{tag_name}',
                        f'.//{{*}}{tag_name}'
                    ]
                    
                    for pattern in search_patterns:
                        try:
                            elements = root.findall(pattern)
                            
                            for element in elements:
                                context_ref = element.get('contextRef')
                                # より厳密なコンテキストマッチング
                                if context_ref and (context_type == context_ref or context_type in context_ref):
                                    try:
                                        value = float(element.text or 0)
                                        if value >= min_threshold:
                                            logger.debug(f"発見: {tag} = {value:,} (context: {context_ref})")
                                            return value
                                    except (ValueError, TypeError):
                                        continue
                        except Exception:
                            continue
                            
        return None
    
    def get_stock_price(self, stock_code: str) -> Optional[float]:
        """
        株価を取得する
        
        Args:
            stock_code: 銘柄コード
            
        Returns:
            Optional[float]: 現在株価
        """
        try:
            symbol = f"{stock_code}.T"
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
                
        except Exception as e:
            if "404" not in str(e):
                logger.debug(f"株価取得エラー {stock_code}: {e}")
                
        return None
    
    def get_market_cap(self, stock_code: str) -> Optional[float]:
        """
        Yahoo Finance APIから時価総額を直接取得する

        Args:
            stock_code: 銘柄コード

        Returns:
            Optional[float]: 時価総額
        """
        try:
            symbol = f"{stock_code}.T"
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            market_cap = info.get('marketCap')
            if market_cap and market_cap > 0:
                return float(market_cap)
                
        except Exception as e:
            if "404" not in str(e):
                logger.debug(f"時価総額取得エラー {stock_code}: {e}")

        return None
    
    def calculate_ratios(self, market_cap: float, investment_securities: float, 
                        dividend_income: float, current_sales: Optional[float] = None,
                        prior_sales: Optional[float] = None, operating_income: Optional[float] = None) -> Tuple[float, float, float, float]:
        """
        財務比率を計算する
        
        Args:
            market_cap: 時価総額
            investment_securities: 投資有価証券
            dividend_income: 受取配当金
            current_sales: 当期売上高
            prior_sales: 前期売上高
            operating_income: 営業利益
            
        Returns:
            Tuple[float, float, float, float]: (資産比率, 配当比率, 営業利益率, 売上高成長率)
        """
        asset_ratio = investment_securities / market_cap if market_cap > 0 else 0
        dividend_ratio = dividend_income / investment_securities if investment_securities > 0 else 0
        
        # 営業利益率（営業利益 ÷ 売上高）
        operating_margin = (operating_income / current_sales * 100) if (current_sales and operating_income and current_sales > 0) else 0
        
        # 売上高成長率（(当期売上高 - 前期売上高) ÷ 前期売上高 × 100）
        sales_growth_rate = ((current_sales - prior_sales) / prior_sales * 100) if (current_sales and prior_sales and prior_sales > 0) else 0
        
        return asset_ratio, dividend_ratio, operating_margin, sales_growth_rate
    
    def process_single_file(self, file_path: str) -> Optional[Dict]:
        """
        単一のXBRLファイルを処理する
        
        Args:
            file_path: XBRLファイルパス
            
        Returns:
            Optional[Dict]: 処理結果
        """
        # EDINETコード抽出
        edinet_code = self.extract_edinet_code(file_path)
        if not edinet_code:
            logger.warning(f"EDINETコード抽出失敗: {file_path}")
            return None
        
        # 企業情報取得
        company_info = self.get_company_info(edinet_code)
        if not company_info:
            logger.warning(f"企業情報取得失敗: {edinet_code}")
            return None
            
        stock_code, company_name = company_info
        
        # 財務データ抽出
        financial_data = self.extract_financial_data(file_path)
        
        # 時価総額をYahoo Finance APIから直接取得
        market_cap = self.get_market_cap(stock_code)
        if not market_cap:
            logger.warning(f"時価総額取得失敗: {stock_code}")
            return None
        
        # 投資有価証券と配当金（当期・前期）
        investment_securities = financial_data.get('investment_securities', 0) or 0
        prior_investment_securities = financial_data.get('prior_investment_securities', 0) or 0
        dividend_income = financial_data.get('dividend_income', 0) or 0
        prior_dividend_income = financial_data.get('prior_dividend_income', 0) or 0
        
        # 売上と営業利益
        current_sales = financial_data.get('current_net_sales')
        prior_sales = financial_data.get('prior_net_sales')
        operating_income = financial_data.get('operating_income')
        
        # 比率計算
        asset_ratio, dividend_ratio, operating_margin, sales_growth_rate = self.calculate_ratios(
            market_cap, investment_securities, dividend_income, current_sales, prior_sales, operating_income
        )
        
        result = {
            'stock_code': stock_code,
            'company_name': company_name,
            'market_cap': market_cap,
            'bs_securities_assets': investment_securities,
            'bs_securities_assets_prior': prior_investment_securities,
            'pl_dividend_income': dividend_income,
            'pl_dividend_income_prior': prior_dividend_income,
            'current_net_sales': current_sales or 0,
            'operating_income': operating_income or 0,
            'asset_ratio': round(asset_ratio, 2),
            'dividend_ratio': round(dividend_ratio, 2),
            'operating_margin': round(operating_margin, 2),
            'sales_growth_rate': round(sales_growth_rate, 2)
        }
        
        # 連結経営指標等を結果に追加
        for key, value in financial_data.items():
            if key.startswith(('net_sales_', 'operating_income_', 'ordinary_income_', 'net_income_', 
                              'comprehensive_income_', 'total_assets_', 'net_assets_', 
                              'earnings_per_share_', 'net_assets_per_share_', 'equity_ratio_', 
                              'roa_', 'roe_', 'employees_')):
                result[key] = value
        
        logger.info(f"処理完了: {stock_code} - {company_name}")
        return result
    
    def run_management_indicators_analysis(self) -> pd.DataFrame:
        """
        連結経営指標等の包括的分析を実行する
        
        Returns:
            pd.DataFrame: 連結経営指標分析結果
        """
        logger.info("連結経営指標等の包括的分析を開始します...")
        
        # EDINETマッピング読み込み
        if not self.load_edinet_mapping():
            logger.error("EDINETマッピングの読み込みに失敗しました")
            return pd.DataFrame()
        
        # XBRLファイル検索
        xbrl_files = self.find_xbrl_files()
        if not xbrl_files:
            logger.error("XBRLファイルが見つかりません")
            return pd.DataFrame()
        
        # 各ファイルを処理
        results = []
        total_files = len(xbrl_files)
        logger.info(f"処理対象ファイル数: {total_files}")
        
        for i, file_path in enumerate(xbrl_files):
            if i % 50 == 0:  # 50ファイルごとに進捗報告
                logger.info(f"処理進捗: {i+1}/{total_files} ({(i+1)/total_files*100:.1f}%)")
            
            # EDINETコード抽出
            edinet_code = self.extract_edinet_code(file_path)
            if not edinet_code:
                continue
            
            # 企業情報取得
            company_info = self.get_company_info(edinet_code)
            if not company_info:
                continue
                
            stock_code, company_name = company_info
            
            # 財務データ抽出（管理指標を含む）
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                
                # 企業タイプと会計基準を判定
                company_type = self._detect_company_type(edinet_code)
                accounting_standard = self._detect_accounting_standard(root)
                
                management_indicators = self.extract_management_indicators(root, company_type, accounting_standard)
                
                # 基本情報と合わせて結果作成
                result = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'edinet_code': edinet_code,
                    'company_type': company_type,
                    'accounting_standard': accounting_standard,
                    'file_path': file_path
                }
                result.update(management_indicators)
                
                results.append(result)
                logger.info(f"管理指標抽出完了: {stock_code} - {company_name}")
                
            except Exception as e:
                logger.error(f"管理指標抽出エラー {file_path}: {e}")
                continue
        
        # DataFrame作成
        if results:
            df = pd.DataFrame(results)
            logger.info(f"連結経営指標分析完了: {len(results)}件の企業を処理しました")
            return df
        else:
            logger.warning("有効な結果が得られませんでした")
            return pd.DataFrame()
    
    def run_analysis(self) -> pd.DataFrame:
        """
        財務分析を実行する
        
        Returns:
            pd.DataFrame: 分析結果
        """
        logger.info("XBRL財務分析を開始します...")
        
        # EDINETマッピング読み込み
        if not self.load_edinet_mapping():
            logger.error("EDINETマッピングの読み込みに失敗しました")
            return pd.DataFrame()
        
        # XBRLファイル検索
        xbrl_files = self.find_xbrl_files()
        if not xbrl_files:
            logger.error("XBRLファイルが見つかりません")
            return pd.DataFrame()
        
        # 各ファイルを処理（全量処理）
        results = []
        total_files = len(xbrl_files)
        logger.info(f"処理対象ファイル数: {total_files}")
        
        for i, file_path in enumerate(xbrl_files):
            if i % 100 == 0:  # 100ファイルごとに進捗報告
                logger.info(f"処理進捗: {i+1}/{total_files} ({(i+1)/total_files*100:.1f}%)")
            
            result = self.process_single_file(file_path)
            if result:
                results.append(result)
                if result['bs_securities_assets'] > 1000000000:  # 10億円以上の有価証券保有企業のみログ出力
                    logger.info(f"大口有価証券保有: {result['stock_code']} - {result['company_name']} - {result['bs_securities_assets']:,.0f}円 営業利益率:{result['operating_margin']:.1f}%")
            else:
                logger.debug(f"処理失敗: {os.path.basename(file_path)}")
        
        # DataFrame作成
        if results:
            df = pd.DataFrame(results)
            logger.info(f"分析完了: {len(results)}件の企業を処理しました")
            return df
        else:
            logger.warning("有効な結果が得られませんでした")
            return pd.DataFrame()
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        結果をCSVファイルに保存する
        
        Args:
            df: 分析結果のDataFrame
            filename: 出力ファイル名
            
        Returns:
            str: 保存されたファイルパス
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"xbrl_financial_analysis_{timestamp}.csv"
        
        df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"結果をCSVファイルに保存しました: {filename}")
        return filename


def main():
    """メイン処理"""
    import sys
    
    # 分析システム初期化
    analyzer = XBRLFinancialAnalyzer()
    
    # コマンドライン引数で分析タイプを指定
    analysis_type = "securities"  # デフォルトは有価証券分析
    if len(sys.argv) > 1:
        if sys.argv[1] == "--management-indicators":
            analysis_type = "management"
        elif sys.argv[1] == "--help":
            print("使用方法:")
            print("  python xbrl_financial_analyzer.py                    # 有価証券分析（デフォルト）")
            print("  python xbrl_financial_analyzer.py --management-indicators  # 連結経営指標分析")
            return
    
    if analysis_type == "management":
        # 連結経営指標分析実行
        results_df = analyzer.run_management_indicators_analysis()
        
        if not results_df.empty:
            print("\n=== 連結経営指標等分析結果 ===")
            print(f"処理企業数: {len(results_df)}社")
            
            # 各指標の有効データ数を確認
            indicator_counts = {}
            for col in results_df.columns:
                if col.startswith(('net_sales_', 'operating_income_', 'ordinary_income_', 
                                  'net_income_', 'comprehensive_income_', 'total_assets_', 
                                  'net_assets_', 'earnings_per_share_', 'net_assets_per_share_', 
                                  'equity_ratio_', 'roa_', 'roe_', 'employees_')):
                    valid_count = results_df[col].notna().sum()
                    if valid_count > 0:
                        indicator_counts[col] = valid_count
            
            print(f"\n=== 指標別データ取得状況 ===")
            for indicator, count in sorted(indicator_counts.items()):
                percentage = (count / len(results_df)) * 100
                print(f"{indicator}: {count}社 ({percentage:.1f}%)")
            
            # CSV保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = f"management_indicators_analysis_{timestamp}.csv"
            results_df.to_csv(csv_file, index=False, encoding='utf-8')
            print(f"\n結果をCSVファイルに保存しました: {csv_file}")
            
        else:
            print("連結経営指標分析結果が得られませんでした。ログを確認してください。")
            
    else:
        # 有価証券分析実行（従来の機能）
        results_df = analyzer.run_analysis()
        
        if not results_df.empty:
            # 結果表示
            print("\n=== XBRL財務分析結果 ===")
            print(results_df.to_string(index=False))
            
            # CSV保存
            csv_file = analyzer.save_to_csv(results_df)
            print(f"\n結果をCSVファイルに保存しました: {csv_file}")
            
            # サマリー表示
            print(f"\n=== サマリー ===")
            print(f"処理企業数: {len(results_df)}社")
            print(f"平均時価総額: {results_df['market_cap'].mean():,.0f}円")
            print(f"平均資産比率: {results_df['asset_ratio'].mean():.2f}倍")
            print(f"平均配当比率: {results_df['dividend_ratio'].mean():.2f}倍")
            print(f"平均営業利益率: {results_df['operating_margin'].mean():.2f}%")
            print(f"平均売上高成長率: {results_df['sales_growth_rate'].mean():.2f}%")
            
            # 配当金を持つ企業の統計
            dividend_companies = results_df[results_df['pl_dividend_income'] > 0]
            if len(dividend_companies) > 0:
                print(f"\n=== 配当金保有企業 ({len(dividend_companies)}社) ===")
                print(f"平均配当比率: {dividend_companies['dividend_ratio'].mean():.2f}倍")
                print(f"平均営業利益率: {dividend_companies['operating_margin'].mean():.2f}%")
                
            # 前年データを持つ企業の統計
            prior_data_companies = results_df[
                (results_df['bs_securities_assets_prior'] > 0) | 
                (results_df['pl_dividend_income_prior'] > 0)
            ]
            if len(prior_data_companies) > 0:
                print(f"\n=== 前年比較可能企業 ({len(prior_data_companies)}社) ===")
                
                # 投資有価証券前年比（0除算を防ぐ）
                valid_securities = prior_data_companies[prior_data_companies['bs_securities_assets_prior'] > 0]
                if len(valid_securities) > 0:
                    securities_ratios = valid_securities['bs_securities_assets'] / valid_securities['bs_securities_assets_prior']
                    print(f"投資有価証券前年比（{len(valid_securities)}社）: 平均{securities_ratios.mean():.2f}倍、中央値{securities_ratios.median():.2f}倍")
                
                # 配当金前年比（0除算を防ぐ）
                valid_dividends = prior_data_companies[prior_data_companies['pl_dividend_income_prior'] > 0]
                if len(valid_dividends) > 0:
                    dividend_ratios = valid_dividends['pl_dividend_income'] / valid_dividends['pl_dividend_income_prior']
                    print(f"配当金前年比（{len(valid_dividends)}社）: 平均{dividend_ratios.mean():.2f}倍、中央値{dividend_ratios.median():.2f}倍")
            
        else:
            print("分析結果が得られませんでした。ログを確認してください。")


if __name__ == "__main__":
    main()