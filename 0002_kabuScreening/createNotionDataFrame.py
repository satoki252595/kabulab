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
    codeList = ['1438.T', '1439.T', '146A.T', '1491.T', '166A.T', '1764.T', '1776.T', '1799.T', '1814.T', '1966.T', '1975.T', '1994.T', '208A.T', '2112.T', '2130.T', '2134.T', '2136.T', '2185.T', '2221.T', '2345.T', '2389.T', '2435.T', '2573.T', '2788.T', '2911.T', '2934.T', '2981.T', '2993.T', '3020.T', '3069.T', '3075.T', '3077.T', '3089.T', '3176.T', '3241.T', '3322.T', '3347.T', '3416.T', '3461.T', '3583.T', '3633.T', '3671.T', '3688.T', '3691.T', '3696.T', '3727.T', '3747.T', '3777.T', '3798.T', '3807.T', '3837.T', '3842.T', '3847.T', '3848.T', '3850.T', '3857.T', '4016.T', '4054.T', '4124.T', '4171.T', '4221.T', '4235.T', '4259.T', '4390.T', '4418.T', '4465.T', '4538.T', '4554.T', '4588.T', '4620.T', '4635.T', '4754.T', '4833.T', '5070.T', '5121.T', '5194.T', '5284.T', '5285.T', '5527.T', '5588.T', '5610.T', '5660.T', '5699.T', '5892.T', '5950.T', '5997.T', '6033.T', '6039.T', '6091.T', '6137.T', '6145.T', '6149.T', '6180.T', '6203.T', '6226.T', '6231.T', '6240.T', '6245.T', '6330.T', '6358.T', '6378.T', '6402.T', '6408.T', '6570.T', '6757.T', '6794.T', '6819.T', '6824.T', '6834.T', '6862.T', '6863.T', '6932.T', '7018.T', '7021.T', '7268.T', '7314.T', '7317.T', '7345.T', '7602.T', '7749.T', '7760.T', '7851.T', '7914.T', '7918.T', '7991.T', '8107.T', '8135.T', '8152.T', '8345.T', '8732.T', '8783.T', '8789.T', '8836.T', '9028.T', '9073.T', '9127.T', '9173.T', '9193.T', '9308.T', '9365.T', '9441.T', '9742.T', '9776.T', '9816.T']

    df = createNotionUpDataFrame(codeList)
    print(df)
