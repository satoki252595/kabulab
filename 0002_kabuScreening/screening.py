import yfinance as yf
import pandas as pd
import re
import urllib.request
import tabula


def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="3mo")
    return hist


def is_perfect_order(hist) -> bool:
    ma5 = hist['Close'].rolling(window=5).mean()
    ma10 = hist['Close'].rolling(window=10).mean()
    ma20 = hist['Close'].rolling(window=20).mean()
    ma60 = hist['Close'].rolling(window=60).mean()
    return (ma5.iloc[-1] > ma10.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1])


def screen_stocks(tickers) -> list:
    screened_stocks = []
    for ticker in tickers:
        hist = get_stock_data(ticker)
        if len(hist) < 60:
            continue
        avg_volume_1w = hist['Volume'].rolling(window=5).mean().iloc[-1]
        avg_volume_1m = hist['Volume'].rolling(window=20).mean().iloc[-1]
        stock = yf.Ticker(ticker)
        market_cap = stock.info.get('marketCap')

        if avg_volume_1w > 1.5 * avg_volume_1m and is_perfect_order(hist) and market_cap < 50000000000:
            screened_stocks.append(ticker)
    return screened_stocks


if __name__ == '__main__':
    codeList = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'FB']
    df = createNotionUpDataFrame(codeList)
    print(df)
