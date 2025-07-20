import os
import zipfile
import pandas as pd
import re
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

def debug_with_xml_parser():
    """XMLパーサーを使用してデバッグ"""
    file_path = "/Users/satoki252595/work/0000_kabulab/0001_MarketableSecuritiesAnalysis/xbrl/S100TA5Q/XBRL/PublicDoc/0104010_honbun_jpcrp030000-asr-001_E00424-000_2024-01-20_01_2024-04-17_ixbrl.htm"
    
    print("=== Testing with XML parser ===")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # lxml parserを使用
        soup = BeautifulSoup(content, 'lxml-xml')
        
        # 全てのix要素を検索
        ix_elements = soup.find_all(['ix:nonNumeric', 'ix:nonFraction'])
        print(f"Found {len(ix_elements)} ix elements with lxml-xml parser")
        
        # SpecifiedInvestment を含む要素を検索
        investment_elements = []
        for elem in ix_elements:
            name_attr = elem.get('name', '')
            if 'SpecifiedInvestment' in name_attr:
                investment_elements.append(elem)
        
        print(f"Found {len(investment_elements)} SpecifiedInvestment elements")
        
        # 詳細を表示
        for i, elem in enumerate(investment_elements[:10]):  # 最初の10個
            print(f"\n{i+1}. Name: {elem.get('name')}")
            print(f"   Content: {elem.get_text(strip=True)}")
            print(f"   contextRef: {elem.get('contextRef')}")
            print(f"   unitRef: {elem.get('unitRef')}")
            
    except Exception as e:
        print(f"Error with lxml-xml parser: {e}")
    
    # html.parserを試す
    print("\n=== Testing with html.parser ===")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # html.parserを使用
        soup = BeautifulSoup(content, 'html.parser')
        
        # 名前空間を考慮せずに検索
        all_elements = soup.find_all(['nonNumeric', 'nonFraction'])
        print(f"Found {len(all_elements)} elements without namespace")
        
        # name属性にSpecifiedInvestmentを含む要素を検索
        investment_elements = []
        for elem in all_elements:
            name_attr = elem.get('name', '')
            if 'SpecifiedInvestment' in name_attr:
                investment_elements.append(elem)
        
        print(f"Found {len(investment_elements)} SpecifiedInvestment elements")
        
        # 詳細を表示
        for i, elem in enumerate(investment_elements[:10]):  # 最初の10個
            print(f"\n{i+1}. Name: {elem.get('name')}")
            print(f"   Content: {elem.get_text(strip=True)}")
            print(f"   contextRef: {elem.get('contextRef')}")
            
    except Exception as e:
        print(f"Error with html.parser: {e}")
        
    # 正規表現で直接検索
    print("\n=== Testing with regex ===")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # SpecifiedInvestmentを含む行を検索
        lines = content.split('\n')
        investment_lines = [line for line in lines if 'SpecifiedInvestment' in line]
        
        print(f"Found {len(investment_lines)} lines containing SpecifiedInvestment")
        
        # 最初の5行を表示
        for i, line in enumerate(investment_lines[:5]):
            print(f"{i+1}. {line.strip()}")
            
    except Exception as e:
        print(f"Error with regex: {e}")

if __name__ == "__main__":
    debug_with_xml_parser()