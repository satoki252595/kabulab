from dotenv import load_dotenv
import os
from sshtunnel import SSHTunnelForwarder
from pymongo import MongoClient
from datetime import date, datetime,timedelta

from getXBRL import getEdinetCodeMapping,get_xbrl


# .envファイルをロードして環境変数を読み込む
load_dotenv()

# SSH接続情報（.envから読み込み）
SSH_HOST = os.getenv('SSH_HOST')
SSH_PORT = int(os.getenv('SSH_PORT', 22))
SSH_USERNAME = os.getenv('SSH_USERNAME')
SSH_PASSWORD = os.getenv('SSH_PASSWORD')

# MongoDB接続情報（.envから読み込み）
MONGO_HOST = os.getenv('MONGO_HOST', '127.0.0.1')
MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
DATABASE_NAME = 'test'
COLLECTION_NAME = 'collection'

if __name__ == '__main__':
    
    # 2024年の1月1日から始める
    start_date = date(2024, 4, 11)
    
    df_EdinetCodeMapping = getEdinetCodeMapping()
    
    tunnel = SSHTunnelForwarder(
    (SSH_HOST, SSH_PORT),
    ssh_username=SSH_USERNAME,
    ssh_password=SSH_PASSWORD,
    remote_bind_address=(MONGO_HOST, MONGO_PORT)
    )
    tunnel.start()
    
    try:
        local_port = tunnel.local_bind_port
        
        client = MongoClient('127.0.0.1', local_port)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
    
        # 1年分の日数をループ (2024年はうるう年なので366日)
        for day_offset in range(366):
            current_date = start_date + timedelta(days=day_offset)
            
            # 年、月、日を取得
            YYYY = current_date.year
            MM = current_date.month
            DD = current_date.day
            
            # 各日付でget_xbrl関数を呼び出す
            results_df = get_xbrl(YYYY, MM, DD,df_EdinetCodeMapping)
        
            # ここがmainのinsert処理
            for df in results_df:
                records = df.to_dict(orient='records')
                result = collection.insert_many(records)
                
                #print(result.inserted_ids)
                
    finally:
        tunnel.stop()