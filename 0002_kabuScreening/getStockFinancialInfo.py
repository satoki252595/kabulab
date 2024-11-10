import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import urllib
import re


def getStockCodeDataFrame() -> pd.core.frame.DataFrame:
    '''
    東証の上場銘柄コード一覧をdf形式で出力する。
    URL = 'https://www.jpx.co.jp/markets/statistics-equities/misc/01.html'
    '''

    URL = 'https://www.jpx.co.jp/markets/statistics-equities/misc/01.html'

    response = urllib.request.urlopen(URL).read().decode("utf-8")
    string_html = re.findall('<a href=\".+?\.xls\"', response)
    url_list = []
    for i in string_html:
        j = i.lstrip('<a href=\"')
        k = j.rstrip('\"')
        url_list.append('https://www.jpx.co.jp'+k)
    url = url_list[0]

    # 国内株式のみ抽出

    df = pd.read_excel(url)
    df = df[(df.iloc[:, 3] == 'プライム（内国株式）') | (df.iloc[:, 3] ==
                                               'スタンダード（内国株式）') | (df.iloc[:, 3] == 'グロース（内国株式）')]

    # 列名の変更
    df.columns = ['date', 'code', 'office_name', 'market_class', 'industry_detail_code',
                  'industry_detail', 'industry_code', 'industry', 'scale_code', 'scale_class']

    # 'date'列をdatetime->strへ型変換
    df['date'] = df['date'].astype(str)
    df['code'] = df['code'].astype(str)
    df['industry_detail_code'] = df['industry_detail_code'].astype(str)
    df['industry_code'] = df['industry_code'].astype(str)
    df['scale_code'] = df['scale_code'].astype(str)

    return df


def get_stock_financial_info(ticker_symbol):
    """
    指定した銘柄の財務情報を取得する関数

    Parameters:
    ticker_symbol (str): 銘柄コード（例：'7203.T'）

    Returns:
    dict: 財務情報を含む辞書
    """
    # Tickerオブジェクトの作成
    ticker = yf.Ticker(ticker_symbol)

    try:
        # 基本情報の取得
        info = ticker.info

        # 財務諸表の取得
        financials = ticker.financials

        # 結果を格納する辞書
        result = {
            '基本情報': {
                '株式発行数': info.get('sharesOutstanding', '-'),
                '時価総額': info.get('marketCap', '-'),
                'ROE': info.get('returnOnEquity', '-'),
                '事業内容': info.get('longBusinessSummary', '-')

            },
            '財務情報': None,
            'データ取得状況': {
                '基本情報': True,
                '財務情報': False
            }
        }

        # 財務情報の取得と計算
        financial_data = []

        if not financials.empty:
            # 各期間のデータを処理
            for date in financials.columns:
                period_data = {}
                period_data['期間'] = date.strftime('%Y-%m-%d')

                # 売上高の取得
                try:
                    revenue = financials.loc['Total Revenue', date]
                    period_data['売上高'] = revenue if not pd.isna(
                        revenue) else None
                except KeyError:
                    period_data['売上高'] = None

                # 営業利益の取得
                try:
                    operating_income = financials.loc['Operating Income', date]
                    period_data['営業利益'] = operating_income if not pd.isna(
                        operating_income) else None
                except KeyError:
                    period_data['営業利益'] = None

                # 営業利益率の計算
                if period_data['売上高'] and period_data['営業利益']:

                    period_data['営業利益率'] = round(
                        (period_data['営業利益'] / period_data['売上高'] * 100), 2)
                else:
                    period_data['営業利益率'] = None

                # 有効なデータが1つでもあれば追加
                if any(v is not None for v in period_data.values()):
                    financial_data.append(period_data)

            if financial_data:
                result['財務情報'] = pd.DataFrame(financial_data)
                result['データ取得状況']['財務情報'] = True

        return result

    except Exception as e:
        print(f"データ取得中にエラーが発生しました: {str(e)}")
        return None


def format_number(value):
    """
    数値を見やすい形式にフォーマットする関数
    """
    if pd.isna(value) or value == '-':
        return '-'
    elif isinstance(value, (int, float)):
        if value >= 1000000000:  # 10億以上
            return f"¥{value/1000000000:.2f}B"
        elif value >= 1000000:  # 100万以上
            return f"¥{value/1000000:.2f}M"
        else:
            return f"¥{value:,.0f}"
    return value


def display_financial_info(ticker_symbol):
    """
    財務情報を見やすく表示する関数

    Parameters:
    ticker_symbol (str): 銘柄コード
    """
    result = get_stock_financial_info(ticker_symbol)

    if result is None:
        print("データを取得できませんでした。")
        return

    print(f"\n=== {ticker_symbol} の財務情報 ===\n")

    # 基本情報の表示
    print("【基本情報】")
    if result['データ取得状況']['基本情報']:
        print(f"株式発行数: {format_number(result['基本情報']['株式発行数'])}")
        print(f"時価総額: {format_number(result['基本情報']['時価総額'])}")
        roe = result['基本情報']['ROE']
        if roe is not None:
            roe_percentage = f"{roe * 100:.1f}%"
        else:
            roe_percentage = '-'
        print(f"ROE: {roe_percentage}")
        print(f"事業内容: {result['基本情報']['事業内容']}")
    else:
        print("基本情報を取得できませんでした。")

    print("\n【財務情報】")
    if result['データ取得状況']['財務情報'] and result['財務情報'] is not None:
        # 財務情報のフォーマット
        formatted_df = result['財務情報'].copy()
        for col in ['売上高', '営業利益']:
            if col in formatted_df.columns:
                formatted_df[col] = formatted_df[col].apply(format_number)
        if '営業利益率' in formatted_df.columns:
            formatted_df['営業利益率'] = formatted_df['営業利益率'].apply(
                lambda x: f"{x:.2f}%" if pd.notnull(x) else '-'
            )

        print(formatted_df.to_string(index=False))
    else:
        print("財務情報を取得できませんでした。")


# 使用例
if __name__ == "__main__":
    # 日本株の例（トヨタ自動車）
    ticker_symbol = '7203.T'
    display_financial_info(ticker_symbol)
