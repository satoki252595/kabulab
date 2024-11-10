import requests
import os
import zipfile
import shutil
import glob
import sys
from datetime import date, timedelta
import os
from dotenv import load_dotenv

'''退役処理は後から考える'''


def getDocument(date: str):
    '''
    date:yyyy-mm-dd
    '''

    # APIの仕様書など（ → https://disclosure.edinet-fsa.go.jp/EKW0EZ0015.html ）
    DOCUMENT_JSON = 'https://disclosure.edinet-fsa.go.jp/api/v2/documents.json?date=' + \
        date+'&type=2&Subscription-Key=' + EDINET_API_KEY
    GET_DOCUMENT = 'https://disclosure.edinet-fsa.go.jp/api/v2/documents/'  # S100L6MR?type=2

    documents_json = requests.get(DOCUMENT_JSON)
    results = documents_json.json()['results']

    # 個別銘柄の有価証券報告書を取得する。

    marketableSecuritieLists = []

    for result in results:
        l = []
        if result['docTypeCode'] == '120' and result['secCode'] != None:
            l.append(result['docID'])
            l.append(result['secCode'][0:4])
            marketableSecuritieLists.append(l)

    for marketableSecuritieList in marketableSecuritieLists:

        url = GET_DOCUMENT + \
            marketableSecuritieList[0] + \
            '?type=1&Subscription-Key=' + EDINET_API_KEY
        fileName = date + '_' + str(marketableSecuritieList[1])

        r = requests.get(url, stream=True)

        try:

            with open(OUTPUT + fileName + '.zip', 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

            with zipfile.ZipFile(OUTPUT + fileName+'.zip') as existing_zip:
                existing_zip.extractall(OUTPUT)

        except:
            continue

        # xbrlファイルが複数あった場合のために、添字iをファイル名に付与する。
        i = 0
        for file in glob.glob(OUTPUT + r'XBRL/PublicDoc/' + r'*.xbrl'):
            shutil.copy(file, OUTPUT)
            os.rename(file, OUTPUT + fileName + '_' + str(i) + '.xbrl')
            i = i + 1

    # 不要なフォルダやファイルを削除
    try:
        shutil.rmtree(OUTPUT + 'XBRL/')
    except:
        print('対象ファイルなし')

    for file in glob.glob(OUTPUT + '*.zip'):
        os.remove(file)

    for file in glob.glob(OUTPUT + '*' + date + '.xbrl'):
        os.remove(file)

    for file in glob.glob(OUTPUT + 'jpcrp' + '*.xbrl'):
        os.remove(file)


if __name__ == '__main__':

    args = sys.argv
    arg = str(args[1])

    OUTPUT = './edinet/'

    load_dotenv()
    EDINET_API_KEY = os.getenv('EDINET_API_KEY')

    getDocument(arg)

    date = date(year=int(arg[0:4]), month=int(arg[5:7]), day=int(arg[8:10]))
    td = timedelta(days=1)

    for i in range(1000):
        print(date + td)
        getDocument(str(date))
        date = date + td
