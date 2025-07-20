#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
時価総額API取得のテスト
"""

from xbrl_financial_analyzer import XBRLFinancialAnalyzer
import yfinance as yf

def test_market_cap_api():
    analyzer = XBRLFinancialAnalyzer()
    
    # テスト銘柄
    test_stocks = ['6137', '9509', '7203', '8035']
    
    print("=== 時価総額API取得テスト ===")
    
    for stock_code in test_stocks:
        print(f"\n--- {stock_code} ---")
        
        # 新しいAPI方式
        market_cap = analyzer.get_market_cap(stock_code)
        print(f"API時価総額: {market_cap:,.0f}円" if market_cap else "API時価総額: 取得失敗")
        
        # 手動計算方式（比較用）
        try:
            ticker = yf.Ticker(f"{stock_code}.T")
            info = ticker.info
            current_price = info.get('currentPrice', 0)
            shares_outstanding = info.get('sharesOutstanding', 0)
            
            if current_price > 0 and shares_outstanding > 0:
                manual_market_cap = current_price * shares_outstanding
                print(f"手動時価総額: {manual_market_cap:,.0f}円")
                print(f"株価: {current_price:,.0f}円")
                print(f"発行済株式数: {shares_outstanding:,.0f}株")
                
                if market_cap:
                    diff = market_cap - manual_market_cap
                    print(f"差異: {diff:,.0f}円 ({diff/market_cap*100:.2f}%)")
                    
        except Exception as e:
            print(f"手動計算エラー: {e}")

if __name__ == "__main__":
    test_market_cap_api()