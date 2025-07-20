#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高速特定投資株式情報抽出器

解凍済みXBRLファイルから特定投資株式情報を並行処理で高速抽出します。
"""

import os
import re
import pandas as pd
from bs4 import BeautifulSoup
import warnings
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import subprocess
from pathlib import Path
import multiprocessing as mp

warnings.filterwarnings('ignore')

# CPU数の取得
CPU_COUNT = mp.cpu_count()
print(f"利用可能CPU数: {CPU_COUNT}")

def find_xbrl_files():
    """grepを使用して特定投資株式情報を含むファイルを高速検索"""
    xbrl_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl"
    
    # 0104010_honbun ファイルを検索
    cmd = f"find {xbrl_path} -name '*0104010_honbun*.htm' -type f"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"エラー: {result.stderr}")
        return []
    
    files = result.stdout.strip().split('\n')
    files = [f for f in files if f.strip()]
    
    print(f"対象ファイル数: {len(files)}")
    return files

def extract_company_info_from_filename(filepath):
    """ファイルパスから会社情報を抽出"""
    filename = os.path.basename(filepath)
    
    # 例: 0104010_honbun_jpcrp030000-asr-001_E02840-000_2024-03-31_01_2024-06-28_ixbrl.htm
    pattern = r'_([E]\d+)-(\d+)_(\d{4}-\d{2}-\d{2})_'
    match = re.search(pattern, filename)
    
    if match:
        return {
            'filing_company_code': match.group(1),
            'document_id': match.group(2),
            'filing_date': match.group(3),
            'file_path': filepath
        }
    return None

def extract_securities_from_file(filepath):
    """単一ファイルから特定投資株式情報を抽出"""
    try:
        # ファイルから会社情報を抽出
        company_info = extract_company_info_from_filename(filepath)
        if not company_info:
            return []
        
        # ファイルを読み込み
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 特定投資株式情報が含まれているかチェック
        if 'SpecifiedInvestment' not in content:
            return []
        
        soup = BeautifulSoup(content, 'lxml-xml')
        results = []
        
        # 特定投資株式名を検索
        name_patterns = [
            r'NameOfSecuritiesDetailsOfSpecifiedInvestment',
            r'NameOfIssuerDetailsOfSpecifiedInvestment',
            r'NameOfSecurities.*SpecifiedInvestment',
            r'NameOfIssuer.*SpecifiedInvestment'
        ]
        
        name_elements = []
        for pattern in name_patterns:
            elements = soup.find_all('ix:nonNumeric', {'name': re.compile(pattern)})
            name_elements.extend(elements)
        
        # 重複を除去
        unique_contexts = {}
        for elem in name_elements:
            context = elem.get('contextRef', '')
            if context and ('CurrentYear' in context or 'Current' in context or 'Instant' in context):
                if context not in unique_contexts:
                    unique_contexts[context] = elem
        
        # 株式数と貸借対照表計上額を検索
        shares_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'NumberOfSharesHeld.*SpecifiedInvestment')})
        book_value_elements = soup.find_all('ix:nonFraction', {'name': re.compile(r'BookValue.*SpecifiedInvestment')})
        purpose_elements = soup.find_all('ix:nonNumeric', {'name': re.compile(r'PurposeOfShareholding.*SpecifiedInvestment')})
        
        # データを結合
        for context, name_elem in unique_contexts.items():
            security_name = name_elem.get_text(strip=True)
            if not security_name:
                continue
            
            # 対応する株式数を検索
            shares = None
            for shares_elem in shares_elements:
                if shares_elem.get('contextRef') == context:
                    shares = shares_elem.get_text(strip=True).replace(',', '')
                    break
            
            # 対応する簿価を検索
            book_value = None
            for book_elem in book_value_elements:
                if book_elem.get('contextRef') == context:
                    book_value = book_elem.get_text(strip=True).replace(',', '')
                    break
            
            # 保有目的を検索
            purpose = None
            for purpose_elem in purpose_elements:
                if purpose_elem.get('contextRef') == context:
                    purpose = purpose_elem.get_text(strip=True)
                    break
            
            # データが存在する場合のみ追加
            if shares or book_value or purpose:
                # 証券コードを抽出
                stock_code_match = re.search(r'(\d{4})', security_name)
                stock_code = stock_code_match.group(1) if stock_code_match else None
                
                # 数値の安全な変換
                try:
                    shares_int = int(shares) if shares and shares.isdigit() else None
                except:
                    shares_int = None
                
                try:
                    book_value_float = float(book_value) if book_value and book_value.replace('.', '').isdigit() else None
                except:
                    book_value_float = None
                
                result = {
                    'filing_company_code': company_info['filing_company_code'],
                    'filing_company_name': None,  # 簡素化のため省略
                    'filing_stock_code': None,    # 簡素化のため省略
                    'filing_date': company_info['filing_date'],
                    'document_id': company_info['document_id'],
                    'held_security_name': security_name,
                    'held_stock_code': stock_code,
                    'held_shares': shares_int,
                    'book_value_million_yen': book_value_float,
                    'holding_purpose': purpose if purpose else 'N/A'
                }
                results.append(result)
        
        return results
        
    except Exception as e:
        print(f"エラー処理中 {filepath}: {str(e)}")
        return []

def process_files_parallel(files, max_workers=None):
    """並行処理でファイルを処理"""
    if max_workers is None:
        max_workers = min(CPU_COUNT, len(files))
    
    print(f"並行処理開始: {max_workers} workers")
    
    all_results = []
    processed = 0
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 全ファイルを並行処理にサブミット
        future_to_file = {executor.submit(extract_securities_from_file, file): file for file in files}
        
        # 完了したタスクから結果を取得
        for future in as_completed(future_to_file):
            file = future_to_file[future]
            try:
                result = future.result()
                all_results.extend(result)
                processed += 1
                
                # 進捗表示
                if processed % 500 == 0:
                    print(f"処理済み: {processed}/{len(files)} ファイル, 抽出レコード数: {len(all_results)}")
                    
            except Exception as e:
                print(f"処理エラー {file}: {str(e)}")
    
    print(f"並行処理完了: {processed} ファイル処理, {len(all_results)} レコード抽出")
    return all_results

def main():
    """メイン処理"""
    # 開始時刻を記録
    start_time = datetime.now()
    print(f"処理開始: {start_time}")
    
    # 対象ファイル検索
    target_files = find_xbrl_files()
    
    if not target_files:
        print("対象ファイルが見つかりません")
        return
    
    # 並行処理で抽出実行
    results = process_files_parallel(target_files)
    
    # 終了時刻を記録
    end_time = datetime.now()
    processing_time = end_time - start_time
    
    print(f"\n=== 処理完了 ===")
    print(f"処理時間: {processing_time}")
    print(f"抽出レコード数: {len(results)}")
    
    if results:
        unique_companies = len(set(r['filing_company_code'] for r in results))
        print(f"提出会社数: {unique_companies}")
        
        # DataFrameに変換
        df = pd.DataFrame(results)
        
        # CSVファイルに保存
        output_filename = f'fast_marketable_securities_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df.to_csv(output_filename, index=False, encoding='utf-8-sig')
        
        print(f"\n=== 保存完了 ===")
        print(f"ファイル名: {output_filename}")
        print(f"レコード数: {len(df)}")
        print(f"提出会社数: {df['filing_company_code'].nunique()}")
        
        # 基本統計
        print(f"\n=== 基本統計 ===")
        print(f"保有証券数: {df['held_security_name'].nunique()}")
        
        # 保有金額の統計
        book_values = df['book_value_million_yen'].dropna()
        if not book_values.empty:
            print(f"総保有金額: {book_values.sum():,.0f} 百万円")
            print(f"平均保有金額: {book_values.mean():,.0f} 百万円")
        
        # 上位保有会社
        top_companies = df.groupby('filing_company_code').size().sort_values(ascending=False).head(10)
        print(f"\n=== 上位保有会社 ===")
        print(top_companies)
        
        # データサンプル表示
        print(f"\n=== データサンプル ===")
        print(df[['filing_company_code', 'held_security_name', 'book_value_million_yen']].head(10))
        
        print(f"\n=== 最終処理結果 ===")
        print(f"開始時刻: {start_time}")
        print(f"終了時刻: {end_time}")
        print(f"処理時間: {processing_time}")
        print(f"処理ファイル数: {len(target_files)}")
        print(f"抽出レコード数: {len(results)}")
        print(f"CPU使用数: {CPU_COUNT}")
        print(f"出力ファイル: {output_filename}")
        print("\n処理完了！")
        
    else:
        print("抽出されたデータがありません")

if __name__ == "__main__":
    main()