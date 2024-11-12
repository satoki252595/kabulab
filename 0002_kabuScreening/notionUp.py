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
    format_market_cap = lambda value: f"{value / 100000000:.2f}億円"
    # roeを小数点第2位で四捨五入するlambda関数
    format_roe = lambda value: f"{round(value, 2)}"

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
                            row["operating_profit_margin"])}}],
                        [{"type": "text", "text": {
                            "content": str(format_roe(row["roe"]*100))}}],
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

    # 関数の実行
    uploadToNotion(cndf.createNotionUpDataFrame(['3933.T']))
