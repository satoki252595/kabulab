import os
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

# .envファイルを読み込む
load_dotenv()

# 環境変数から値を取得
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")


def uploadToNotion(df):
    '''
    Notion上のページにテキストをアップロードする関数

    # ページの構成
    ・本日の日付をタイトルとする。（トグル形式）
    ・日付内には以下の内容をスコア順にテーブルとして記載する。
     ・銘柄コード（文字列）
     ・銘柄名（文字列）
     ・時価総額（数値）
     ・営業利益率（数値）
     ・ROE（数値）
     ・営業利益率の増加回数（数値）
     ・スコア（数値）※表示はしないが、スコア順にソートするために必要
    '''

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2021-05-13"
    }

    today = datetime.today().strftime('%Y-%m-%d')
    
    # market_capを億円単位に変換し、文字列としてフォーマットするlambda関数
    format_market_cap = lambda value: f"{value / 100000000:.1f}億円"
    # roeを小数点第2位で四捨五入するlambda関数
    format_roe = lambda value: f"{round(value, 1)}" if isinstance(value, (int, float)) else value
    # スコア順にソート
    df_sorted = df.sort_values(by='score', ascending=False)

    children = []
    for index, row in df_sorted.iterrows():
        #100個以上のテーブル情報はnotionにアップロードできないため、100個までに制限。（ヘッダー行を考慮）
        if index < 99:
            children.append({
                "object": "block",
                "type": "table_row",
                "table_row": {
                    "cells": [
                        [{"type": "text", "text": {"content": str(row["code"])}}],
                        [{"type": "text", "text": {
                            "content": str(row["name"]),
                            "link": {"url": f"https://www.buffett-code.com/company/{row['code']}"}
                        }}],
                        [{"type": "text", "text": {"content": f"{format_market_cap(row['market_cap'])}"}}],
                        [{"type": "text", "text": {"content": str(
                            row["operating_profit_margin"])+"%"}}],
                        [{"type": "text", "text": {
                            "content": str(format_roe(row["roe"]*100))+"%"}}],
                        [{"type": "text", "text": {"content": str(
                            row["countOperatingProfitMargin"])+"年"}}],

                    ]
                }
            })

    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "title": [
                {
                    "type": "text",
                    "text": {
                        "content": today
                    }
                }
            ]
        },
        "children": [
            {
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "text": [
                        {
                            "type": "text",
                            "text": {
                                "content": today
                            }
                        }
                    ],
                    "children": [
                        {
                            "object": "block",
                            "type": "table",
                            "table": {
                                "table_width": 6,
                                "has_column_header": True,
                                "children": [
                                    {
                                        "object": "block",
                                        "type": "table_row",
                                        "table_row": {
                                            "cells": [
                                                [{"type": "text", "text": {
                                                    "content": "銘柄コード"}}],
                                                [{"type": "text", "text": {
                                                    "content": "銘柄名（リンク）"}}],
                                                [{"type": "text", "text": {
                                                    "content": "時価総額"}}],
                                                [{"type": "text", "text": {
                                                    "content": "営業利益率"}}],
                                                [{"type": "text", "text": {
                                                    "content": "ROE"}}],
                                                [{"type": "text", "text": {
                                                    "content": "営業利益率の増加年数"}}]
                                            ]
                                        }
                                    }
                                ] + children
                            }
                        }
                    ]
                }
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("Page uploaded successfully!")
    else:
        print(f"Failed to upload page. Status code: {response.status_code}")
        print(f"{response.text}")


if __name__ == "__main__":

    import createNotionDataFrame as cndf
    
        
    codeList = ['1438.T', '1439.T', '146A.T', '1491.T', '166A.T', '1764.T', '1776.T', '1799.T', '1814.T', '1966.T', '1975.T', '1994.T', '208A.T', '2112.T', '2130.T', '2134.T', '2136.T', '2185.T', '2221.T', '2345.T', '2389.T', '2435.T', '2573.T', '2788.T', '2911.T', '2934.T', '2981.T', '2993.T', '3020.T', '3069.T', '3075.T', '3077.T', '3089.T', '3176.T', '3241.T', '3322.T', '3347.T', '3416.T', '3461.T', '3583.T', '3633.T', '3671.T', '3688.T', '3691.T', '3696.T', '3727.T', '3747.T', '3777.T', '3798.T', '3807.T', '3837.T', '3842.T', '3847.T', '3848.T', '3850.T', '3857.T', '4016.T', '4054.T', '4124.T', '4171.T', '4221.T', '4235.T', '4259.T', '4390.T', '4418.T', '4465.T', '4538.T', '4554.T', '4588.T', '4620.T', '4635.T', '4754.T', '4833.T', '5070.T', '5121.T', '5194.T', '5284.T', '5285.T', '5527.T', '5588.T', '5610.T', '5660.T', '5699.T', '5892.T', '5950.T', '5997.T', '6033.T', '6039.T', '6091.T', '6137.T', '6145.T', '6149.T', '6180.T', '6203.T', '6226.T', '6231.T', '6240.T', '6245.T', '6330.T', '6358.T', '6378.T', '6402.T', '6408.T', '6570.T', '6757.T', '6794.T', '6819.T', '6824.T', '6834.T', '6862.T', '6863.T', '6932.T', '7018.T', '7021.T', '7268.T', '7314.T', '7317.T', '7345.T', '7602.T', '7749.T', '7760.T', '7851.T', '7914.T', '7918.T', '7991.T', '8107.T', '8135.T', '8152.T', '8345.T', '8732.T', '8783.T', '8789.T', '8836.T', '9028.T', '9073.T', '9127.T', '9173.T', '9193.T', '9308.T', '9365.T', '9441.T', '9742.T', '9776.T', '9816.T']


    # 関数の実行
    uploadToNotion(cndf.createNotionUpDataFrame(codeList))
