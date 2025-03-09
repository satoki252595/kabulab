import os
from dotenv import load_dotenv
from datetime import date, datetime,timedelta
import requests
import zipfile
import io
import logging
import pandas as pd
import re

import yfinance as yfinance
from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser

import pandas as pd
from arelle import Cntlr


load_dotenv()
EDINET_API_KEY = os.getenv('EDINET_API_KEY')

def get_documents_by_date(target_date, doc_type='030000'):
    """
    指定した日付にEDINETで開示された書類一覧を取得し、
    指定doc_type(有報)を満たすdoc_idとedinet_codeのリストを返す。
    """
    if isinstance(target_date, date):
        date_str = target_date.strftime("%Y-%m-%d")
    else:
        date_str = target_date
    base_url = "https://disclosure.edinet-fsa.go.jp/api/v2/documents.json"
    params = {'date': date_str, 'type': 2,'Subscription-Key':EDINET_API_KEY}
    r = requests.get(base_url, params=params)
    r.raise_for_status()
    data = r.json()
    results = data.get('results', [])

    docs = []


    for d in results:
        if d.get('formCode') == doc_type and d.get('docTypeCode') == '120':
            docs.append(d)

    return docs

def download_xbrl_file(doc_id,output_dir = "./xbrl/"):
    """

    """
    path = output_dir + doc_id + '/'
    
    base_url = "https://disclosure.edinet-fsa.go.jp/api/v2/documents"
    params = {
        'type': 1,
        'Subscription-Key': EDINET_API_KEY
    }
    
    try:
        response = requests.get(f"{base_url}/{doc_id}", params=params, stream=True)
        response.raise_for_status()
    except Exception as e:
        logging.error("EDINET APIからのダウンロードに失敗しました: %s", e)
        return None
    
    # try:
    # ダウンロードしたZIPアーカイブをメモリ上で読み込む
    
    z = zipfile.ZipFile(io.BytesIO(response.content))
    # 出力先ディレクトリの作成
    if not os.path.exists(path):
        os.makedirs(path)
            
    filename = doc_id + ".zip"
    with open(path+filename, 'wb') as f:    
        for chunk in response.iter_content(chunk_size=1024):
          f.write(chunk)

    with zipfile.ZipFile(path+filename) as zip_f:
        zip_f.extractall(path)


        # ZIP 内で拡張子が .xbrl のファイルを検索（大文字小文字区別しない）
        xbrl_files = [f for f in zip_f.namelist() if f.lower().endswith('.xbrl')]
        if not xbrl_files:
            logging.warning("doc_id=%s のZIP内にXBRLファイルが見つかりませんでした", doc_id)
            return None
        
        # 例として最初に見つかった XBRL ファイルの絶対パスを返す
        xbrl_file_rel_path = xbrl_files[0]
        current_directory = os.getcwd()
        xbrl_file_abs_path = os.path.join(current_directory + path[1:], xbrl_file_rel_path)
        
    return xbrl_file_abs_path

def extract_financial_data(xbrl_file):
    # Arelle のコントローラ作成（ログ出力は標準出力に設定）
    cntlr = Cntlr.Cntlr(logFileName='logToPrint')
    
    # XBRL ファイルを読み込み
    modelXbrl = cntlr.modelManager.load(xbrl_file)
    
    # 抽出データを格納するリスト
    data = []
    
    # 各 fact から情報を抽出
    for fact in modelXbrl.facts:
        # 必要な情報例: コンセプト、値、単位、コンテキストID
        row = {
            'concept': fact.concept.qname.localName,
            'concept_jp': fact.concept.label(preferredLabel=None, lang='ja', linkroleHint=None), 
            'value': fact.value,
            'unit': fact.unitID if fact.unitID else '',
            'context': fact.contextID,
        }
        data.append(row)
    
    # リストを pandas DataFrame に変換
    df = pd.DataFrame(data)
    return df

def get_year_from_context(context_str, periodEnd_date):
    """
    context の文字列に含まれるキーワードに基づいて、
    対象期を periodEnd から何年前か計算し、'YYYY' 形式で返す。
    """
    if "CurrentYear" in context_str:
        target_date = periodEnd_date
    elif "Prior1Year" in context_str:
        target_date = periodEnd_date.replace(year=periodEnd_date.year - 1)
    elif "Prior2Year" in context_str:
        target_date = periodEnd_date.replace(year=periodEnd_date.year - 2)
    elif "Prior3Year" in context_str:
        target_date = periodEnd_date.replace(year=periodEnd_date.year - 3)
    elif "Prior4Year" in context_str:
        target_date = periodEnd_date.replace(year=periodEnd_date.year - 4)
    else:
        # 対象外の場合は None を返す
        return None
    
    return target_date.strftime("%Y")

def is_non_consolidated(context_str):
    """
    context の文字列に含まれるキーワードに基づいて、
    連結か非連結（単独）かを判断する。
    """
    return "NonConsolidatedMember" in context_str

def remove_html_tags(df, column='value', method='advanced', remove_whitespace=True):
    """
    DataFrameの列からHTMLタグや属性を削除する関数
    
    パラメータ:
    df (pandas.DataFrame): HTML内容を含む列を持つDataFrame
    column (str): HTML内容を含む列名 (デフォルト: 'value')
    method (str): クリーニング方法:
                  - 'simple': 完全なHTMLタグのみを削除
                  - 'advanced': 完全および不完全なHTMLタグを処理（デフォルト）
                  - 'specific': 例で挙げられた特定のタグのみを削除
    remove_whitespace (bool): Trueの場合、余分な空白と改行コードを徹底的に削除（デフォルト: True）
    
    戻り値:
    pandas.DataFrame: クリーニングされた列を持つDataFrame
    """
    # 元のDataFrameを変更しないようにコピーを作成
    cleaned_df = df.copy()
    
    def simple_clean(text):
        if not isinstance(text, str):
            return text
        
        # 完全なHTMLタグを削除
        text = re.sub(r'<[^>]+>', '', text)
        
        # 余分なスペースを削除
        if remove_whitespace:
            # 改行コードを含む全ての空白文字を単一のスペースに置換
            text = re.sub(r'\s+', ' ', text).strip()
            # 全角スペースも標準的なスペースに置換
            text = re.sub(r'　', ' ', text)
        else:
            # 連続する空白のみを単一スペースに置換（改行は保持）
            text = re.sub(r'[ \t]+', ' ', text).strip()
        return text
    
    def advanced_clean(text):
        if not isinstance(text, str):
            return text
        
        # 完全なHTMLタグを削除
        text = re.sub(r'<[^>]+>', '', text)
        
        # 不完全なHTMLタグの開始部分を削除
        text = re.sub(r'<[a-zA-Z][^>]*', '', text)
        
        # 孤立した閉じタグや不完全な閉じタグを削除
        text = re.sub(r'</[^>]*>', '', text)
        text = re.sub(r'</[^>]*', '', text)
        
        # 余分なスペースを削除
        if remove_whitespace:
            # 改行コードを含む全ての空白文字を単一のスペースに置換
            text = re.sub(r'\s+', ' ', text).strip()
            # 全角スペースも標準的なスペースに置換
            text = re.sub(r'　', ' ', text)
            # HTMLエンティティの空白文字を置換
            text = re.sub(r'&nbsp;', ' ', text)
        else:
            # 連続する空白のみを単一スペースに置換（改行は保持）
            text = re.sub(r'[ \t]+', ' ', text).strip()
        return text
    
    def specific_clean(text):
        if not isinstance(text, str):
            return text
        
        # 例で挙げられた特定のタグを削除
        text = re.sub(r'<p class="smt_head3"[^>]*>', '', text)
        text = re.sub(r'<[^>]+style="orphans:0;widows:[^"]*"[^>]*>', '', text)
        
        # 閉じる</p>タグを削除
        text = re.sub(r'</p>', '', text)
        
        # 余分なスペースを削除
        if remove_whitespace:
            # 改行コードを含む全ての空白文字を単一のスペースに置換
            text = re.sub(r'\s+', ' ', text).strip()
            # 全角スペースも標準的なスペースに置換
            text = re.sub(r'　', ' ', text)
            # HTMLエンティティの空白文字を置換
            text = re.sub(r'&nbsp;', ' ', text)
        else:
            # 連続する空白のみを単一スペースに置換（改行は保持）
            text = re.sub(r'[ \t]+', ' ', text).strip()
        return text
    
    # 指定された列に適切なクリーニング関数を適用
    if column in cleaned_df.columns:
        if method == 'simple':
            cleaned_df[column] = cleaned_df[column].apply(simple_clean)
        elif method == 'advanced':
            cleaned_df[column] = cleaned_df[column].apply(advanced_clean)
        elif method == 'specific':
            cleaned_df[column] = cleaned_df[column].apply(specific_clean)
        else:
            raise ValueError("メソッドは'simple'、'advanced'、または'specific'である必要があります")
    else:
        raise ValueError(f"列'{column}'がDataFrameに見つかりません")
    
    return cleaned_df

def process_xbrl_file(xbrl_file_path, periodEnd_date,edinetCode,df_EdinetCodeMapping):
    
    # XBRLデータの抽出
    df = extract_financial_data(xbrl_file_path)
    
    # 各行のコンテキストに対して年度と連結/非連結情報を追加
    df['year'] = df['context'].apply(lambda x: get_year_from_context(x, periodEnd_date))
    df['is_non_consolidated'] = df['context'].apply(is_non_consolidated)
    df['edinetCode'] = edinetCode
    
    df = pd.merge(df,df_EdinetCodeMapping[['ＥＤＩＮＥＴコード', '証券コード']],
    left_on='edinetCode', #dfのカラム名
    right_on='ＥＤＩＮＥＴコード', #df_EdinetCodeMappingのカラム名
    how='left'
)
    df = remove_html_tags(df)
    df = df.drop('ＥＤＩＮＥＴコード', axis=1)
    
    return df


def get_xbrl(YYYY,MM,DD,df_EdinetCodeMapping):
    

    documents = get_documents_by_date(date(YYYY, MM, DD),doc_type='030000')
    results = []
    
    for document in documents:
        doc_id = document['docID']
        edinetCode = document['edinetCode']
        periodEnd_date= date.fromisoformat(document['periodEnd'])
        
        # print(edinetCode)
        # print(list(df_EdinetCodeMapping.loc[:, 'ＥＤＩＮＥＴコード']))
        # print(edinetCode in list(df_EdinetCodeMapping.loc[:, 'ＥＤＩＮＥＴコード']))
        
        # 国内上場銘柄のみ絞って作業する。
        if edinetCode in list(df_EdinetCodeMapping.loc[:, 'ＥＤＩＮＥＴコード']):
            xbrl_path = download_xbrl_file(doc_id,output_dir = "./xbrl/")
            if not os.path.exists(xbrl_path):
                print("XBRL ファイルが見つかりません:", xbrl_path)
                continue  # ファイルが存在しない場合、次のループへ
            
            # ファイルが存在する場合のみ処理
            result_df = process_xbrl_file(xbrl_path, periodEnd_date,edinetCode,df_EdinetCodeMapping)

            results.append(result_df)
        
    return results
    
    
##これはedinetcodeと証券コードをマッピングするための処理
    
import asyncio
import os
import zipfile
import pandas as pd
from typing import Dict, List, Optional, Union
from playwright.async_api import async_playwright, Page
import io
import glob

async def download_edinet_file(
    url: str = "https://disclosure2.edinet-fsa.go.jp/weee0010.aspx",
    download_dir: str = None,
    js_function: str = "onDownloadEdinet()",
    timeout: int = 60000,
    extract: bool = True,
    headless: bool = True,
    encoding: str = "cp932"
) -> Dict[str, pd.DataFrame]:
    """EDINETからファイルをダウンロードし、CSVをデータフレームに変換します"""
    
    # ダウンロードディレクトリの設定
    if download_dir is None:
        download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    # 結果格納用の辞書
    result_dataframes = {}
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()
            
            # サイトにアクセスしてダウンロード
            await page.goto(url)
            download_path = await download_and_wait(page, download_dir, js_function, timeout)
            await browser.close()
            
            if download_path and os.path.exists(download_path):
                # ZIPファイルの処理
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    if extract:
                        # ファイルを解凍してからCSVを読み込む
                        extract_dir = os.path.join(download_dir, "extracted")
                        os.makedirs(extract_dir, exist_ok=True)
                        zip_ref.extractall(path=extract_dir)
                        
                        # CSV検索とデータフレーム変換
                        for csv_file in find_csv_files(extract_dir):
                            df = read_csv_to_dataframe(csv_file, encoding)
                            if df is not None:
                                result_dataframes[os.path.basename(csv_file)] = df
                    else:
                        # ZIP内のCSVを直接読み込む
                        for csv_filename in [f for f in zip_ref.namelist() if f.lower().endswith('.csv')]:
                            with zip_ref.open(csv_filename) as csv_file:
                                content = csv_file.read()
                                try:
                                    df = pd.read_csv(io.BytesIO(content), encoding=encoding, skiprows=1, dtype=str)
                                    result_dataframes[os.path.basename(csv_filename)] = df
                                except Exception:
                                    # エンコーディングを変えて再試行
                                    try:
                                        df = pd.read_csv(io.BytesIO(content), encoding="utf-8", skiprows=1, dtype=str)
                                        result_dataframes[os.path.basename(csv_filename)] = df
                                    except Exception:
                                        pass
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
    
    return result_dataframes

async def download_and_wait(page: Page, download_dir: str, js_function: str, timeout: int) -> Optional[str]:
    """ダウンロードを開始して完了を待つ"""
    try:
        # ダウンロードタスクを作成
        download_future = asyncio.create_task(page.wait_for_event('download', timeout=timeout))
        
        # JavaScriptを実行してダウンロード開始
        await page.evaluate(js_function)
        
        # ダウンロード完了を待つ
        download = await download_future
        save_path = os.path.join(download_dir, download.suggested_filename)
        await download.save_as(save_path)
        return save_path
    except Exception as e:
        print(f"ダウンロード中にエラーが発生しました: {str(e)}")
        return None

def find_csv_files(directory: str) -> List[str]:
    """指定ディレクトリ内のCSVファイルを検索"""
    return glob.glob(os.path.join(directory, "**", "*.csv"), recursive=True)

def read_csv_to_dataframe(csv_path: str, encoding: str = "cp932") -> Optional[pd.DataFrame]:
    """CSVファイルをデータフレームに読み込む（1行目をスキップ）"""
    try:
        try:
            df = pd.read_csv(csv_path, encoding=encoding, skiprows=1, dtype=str)
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, encoding="utf-8", skiprows=1, dtype=str)
        return df
    except Exception:
        return None

async def get_edinet_dataframes():
    """EDINETからCSVをダウンロードしてデータフレームを返す"""
    return await download_edinet_file(
        headless=True,  # 必要に応じてTrue/Falseを切り替え
        extract=True
    )

async def get_first_dataframe():
    """最初のCSVデータフレームのみを返す"""
    dataframes = await get_edinet_dataframes()
    if dataframes:
        # 最初のデータフレームを返す
        return next(iter(dataframes.values()))
    return pd.DataFrame()  # 空のデータフレームを返す

def getEdinetCodeMapping():
    
    dfs = asyncio.run(download_edinet_file())
    dfs_tmp = dfs['EdinetcodeDlInfo.csv']
    df = dfs_tmp[dfs_tmp['上場区分']=='上場']
    df.loc[:, '証券コード'] = df['証券コード'].str.rstrip('0')
    
    return df

if __name__=='__main__':
    
    # 2024年の1月1日から始める
    YYYY = 2024
    start_date = date(YYYY, 4, 11)
    
    df_EdinetCodeMapping = getEdinetCodeMapping()
    
    # 1年分の日数をループ (2024年はうるう年なので366日)
    for day_offset in range(366):
        current_date = start_date + timedelta(days=day_offset)
        
        # 年、月、日を取得
        YYYY = current_date.year
        MM = current_date.month
        DD = current_date.day
        
        # 各日付でget_xbrl関数を呼び出す
        result_df = get_xbrl(YYYY, MM, DD,df_EdinetCodeMapping)
        print(f"{YYYY}年{MM}月{DD}日の結果:{len(result_df)}")
