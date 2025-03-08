import screening as s
import getStockFinancialInfo as gsfi

import pandas as pd
import yfinance as yf


def countOperatingProfitMargin(df: pd.core.frame.DataFrame) -> int:

    try:

        count = 0
        if df['財務情報'].iloc[0]['営業利益率'] > df['財務情報'].iloc[1]['営業利益率']:
            count += 1
        if df['財務情報'].iloc[1]['営業利益率'] > df['財務情報'].iloc[2]['営業利益率']:
            count += 1
        if df['財務情報'].iloc[2]['営業利益率'] > df['財務情報'].iloc[3]['営業利益率']:
            count += 1
        return count

    except:
        return 0


def calAvgRevenueGrowthRate(df: pd.core.frame.DataFrame) -> float:
    try:
        avg_growth_rate = (df['財務情報'].iloc[0]['売上高'] / df['財務情報'].iloc[1]['売上高'] +
                           df['財務情報'].iloc[1]['売上高'] / df['財務情報'].iloc[2]['売上高'] +
                           df['財務情報'].iloc[2]['売上高'] / df['財務情報'].iloc[3]['売上高']) / 3
        return avg_growth_rate

    except:
        return 0


def createNotionUpDataFrame(codeList: list) -> pd.core.frame.DataFrame:
    '''
    Notion用のデータフレームを作成する

    #データフレームのカラム
    - code: 銘柄コード
    - name: 銘柄名
    - market_cap: 時価総額
    - operating_profit_margin: 営業利益率
    - roe: ROE
    - countOperatingProfitMargin: 営業利益率の増加回数
    - score: countOperatingProfitMargin * calAvgRevenueGrowthRate
    '''

    df_list = []
    for code in codeList:

        stockInfo = gsfi.get_stock_financial_info(code)

        # データフレームを取得
        stock_code_df = gsfi.getStockCodeDataFrame()

        def get_office_name(code):
            return stock_code_df.loc[stock_code_df['code'] == code, 'office_name'].values[0] if not stock_code_df.loc[stock_code_df['code'] == code, 'office_name'].empty else None

        try:
            data = {
                'code': [code[:-2]],
                'name': [get_office_name(code[:-2])],
                'market_cap': stockInfo['基本情報']['時価総額'],
                'operating_profit_margin': stockInfo['財務情報']['営業利益率'].iloc[0],
                'roe': stockInfo['基本情報']['ROE'],
                'countOperatingProfitMargin': [countOperatingProfitMargin(stockInfo)],
                'score': [countOperatingProfitMargin(stockInfo) * calAvgRevenueGrowthRate(stockInfo)]
            }
        except:
            print(code,stockInfo)

        df = pd.DataFrame(data)
        df_list.append(df)

    result_df = pd.concat(df_list, ignore_index=True)

    return result_df


if __name__ == '__main__':
    # allCodeList = gsfi.getStockCodeDataFrame()
    # codeList = s.screen_stocks(allCodeList)
    codeList = ['1414.T', '3393.T']

    df = createNotionUpDataFrame(codeList)
    print(df)
