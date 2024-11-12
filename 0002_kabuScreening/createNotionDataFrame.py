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
        stock = yf.Ticker(code)
        info = stock.info

        stockInfo = gsfi.get_stock_financial_info(code)

        # データフレームを取得
        stock_code_df = gsfi.getStockCodeDataFrame()

        def get_office_name(code):
            return stock_code_df.loc[stock_code_df['code'] == code, 'office_name'].values[0] if not stock_code_df.loc[stock_code_df['code'] == code, 'office_name'].empty else None

        data = {
            'code': [code[:-2]],
            'name': [get_office_name(code[:-2])],
            'market_cap': stockInfo['基本情報']['時価総額'],
            'operating_profit_margin': stockInfo['財務情報']['営業利益率'].iloc[0],
            'roe': stockInfo['基本情報']['ROE'],
            'countOperatingProfitMargin': [countOperatingProfitMargin(stockInfo)],
            'score': [abs(countOperatingProfitMargin(stockInfo) * calAvgRevenueGrowthRate(stockInfo))]
        }

        df = pd.DataFrame(data)
        df_list.append(df)

        result_df = pd.concat(df_list, ignore_index=True)

    return result_df


if __name__ == '__main__':
    # allCodeList = gsfi.getStockCodeDataFrame()
    # codeList = s.screen_stocks(allCodeList)
    codeList = ['1491.T', '1776.T', '1948.T', '1964.T', '1966.T', '2136.T', '2179.T', '2221.T', '2389.T', '2435.T', '2806.T', '2901.T', '2924.T', '3041.T', '3089.T', '3189.T', '3299.T', '3416.T', '3681.T', '3691.T', '3696.T', '3777.T', '3779.T', '3798.T', '3842.T', '3847.T', '3850.T', '3900.T', '3909.T', '3944.T', '3947.T', '3991.T', '4078.T', '4248.T', '4310.T', '4319.T', '4461.T', '4484.T', '4498.T', '4538.T', '4685.T', '4709.T', '4957.T', '5285.T',
                '5380.T', '5386.T', '5660.T', '6039.T', '6149.T', '6164.T', '6180.T', '6203.T', '6226.T', '6232.T', '6240.T', '6408.T', '6757.T', '6817.T', '6835.T', '6898.T', '6907.T', '7073.T', '7422.T', '7602.T', '7687.T', '7709.T', '7719.T', '7781.T', '7793.T', '7957.T', '7971.T', '7991.T', '8005.T', '8006.T', '8107.T', '8624.T', '8732.T', '8747.T', '8860.T', '8996.T', '9028.T', '9130.T', '9193.T', '9332.T', '9742.T', '9776.T', '9795.T', '9845.T', '9853.T']

    createNotionUpDataFrame(codeList)
