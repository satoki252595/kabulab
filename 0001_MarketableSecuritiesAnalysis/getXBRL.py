import requests
from datetime import date
import os
from dotenv import load_dotenv
import io
import zipfile
import logging
import pandas as pd
from arelle import Cntlr

load_dotenv()
EDINET_API_KEY = os.getenv('EDINET_API_KEY')

def get_documents_by_date(target_date:str, doc_type='030000'):
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
            'concept_jp':fact.concept.label(preferredLabel=None, lang='ja', linkroleHint=None), 
            'value': fact.value,
            'unit': fact.unitID if fact.unitID else '',
            'context': fact.contextID,

        }
        data.append(row)
    
    # リストを pandas DataFrame に変換
    df = pd.DataFrame(data)
    return df

def set_context_YYYY(context_str:str,periodEnd_date:str):
    """
    context の文字列に含まれるキーワードに基づいて、
    対象期を periodEnd から何年前か計算し、'YYYY' 形式で返す。
    """
    if "CurrentYear" in context_str:
        date = periodEnd_date
    elif "Prior1Year" in context_str:
        date = periodEnd_date.replace(year=periodEnd_date.year - 1)
    elif "Prior2Year" in context_str:
        date = periodEnd_date.replace(year=periodEnd_date.year - 2)
    elif "Prior3Year" in context_str:
        date = periodEnd_date.replace(year=periodEnd_date.year - 3)
    elif "Prior4Year" in context_str:
        date = periodEnd_date.replace(year=periodEnd_date.year - 4)
    else:
        # 対象外の場合は None を返す
        return None
    
    return date.strftime("%Y")

def set_context_NCM(context_str):
    """
    context の文字列に含まれるキーワードに基づいて、
    連結か非連結（単独）かを判断する。
    """
    if "NonConsolidatedMember" in context_str:
        return True
        
    return False

def csv_write(df:pd.core.frame.DataFrame,output_file_name:str,output_dir='csv'):
    
    # 出力先のディレクトリが存在しない場合は作成
    output_dir = 'csv'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # CSVファイルとして出力（index=Falseでインデックス列を除外）
    output_path = os.path.join(output_dir, output_file_name)
    df.to_csv(output_path, index=False, encoding='utf-8')


if __name__=='__main__':
    
    documents  = get_documents_by_date(target_date='2024-06-28')
    for d in documents:
        
        doc_id = d['docID']
        periodStart_date = date.fromisoformat(d['periodStart'])
        periodEnd_date= date.fromisoformat(d['periodEnd'])
        

    
        xbrl_file_abs_path = download_xbrl_file(doc_id)
        
        if os.path.exists(xbrl_file_abs_path):
            df = extract_financial_data(xbrl_file_abs_path)
            
            df = df.copy()
            ##periodEndで年月日をセットしているが誤っているかも？
            df['context_YYYY'] = df['context'].apply(set_context_YYYY)
            df['context_NCM'] = df['context'].apply(set_context_NCM)
            csv_write(df,doc_id)
            
        else:
            print("XBRL ファイルが見つかりません:", xbrl_file_abs_path)
