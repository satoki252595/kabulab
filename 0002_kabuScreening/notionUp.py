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

    # スコア順にソート
    df_sorted = df.sort_values(by='score', ascending=False)

    children = []
    for index, row in df_sorted.iterrows():
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
                    [{"type": "text", "text": {"content": f"{row['market_cap']:,}"}}],
                    [{"type": "text", "text": {"content": str(
                        row["operating_profit_margin"])}}],
                    [{"type": "text", "text": {
                        "content": str(row["roe"]*100)}}],
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


if __name__ == "__main__":

    import createNotionDataFrame as cndf

    # 関数の実行
    uploadToNotion(cndf.createNotionUpDataFrame(
        ['1491.T', '1776.T', '1948.T', '1964.T', '1966.T', '2136.T', '2179.T', '2221.T', '2389.T', '2435.T', '2806.T', '2901.T', '2924.T', '3041.T', '3089.T', '3189.T', '3299.T', '3416.T', '3681.T', '3691.T', '3696.T', '3777.T', '3779.T', '3798.T', '3842.T', '3847.T', '3850.T', '3900.T', '3909.T', '3944.T', '3947.T', '3991.T', '4078.T', '4248.T', '4310.T', '4319.T', '4461.T', '4484.T', '4498.T', '4538.T', '4685.T', '4709.T', '4957.T', '5285.T', '5380.T', '5386.T', '5660.T', '6039.T', '6149.T', '6164.T', '6180.T', '6203.T', '6226.T', '6232.T', '6240.T', '6408.T', '6757.T', '6817.T', '6835.T', '6898.T', '6907.T', '7073.T', '7422.T', '7602.T', '7687.T', '7709.T', '7719.T', '7781.T', '7793.T', '7957.T', '7971.T', '7991.T', '8005.T', '8006.T', '8107.T', '8624.T', '8732.T', '8747.T', '8860.T', '8996.T', '9028.T', '9130.T', '9193.T', '9332.T', '9742.T', '9776.T', '9795.T', '9845.T', '9853.T']))
