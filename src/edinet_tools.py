# src/edinet_tools.py

import datetime
import json
import os # os.path.join など、必要に応じて残す
import urllib.parse
import urllib.request
from typing import List, Dict, Union

# 注意: APIキーの読み込み (load_dotenv, EDINET_API_KEY) は
# このファイルではなく、メインのスクリプト (例: main_edinet_tool.py) で行います。

def filter_by_codes(
    docs: List[Dict],
    edinet_codes: Union[List[str], str] = [],
    doc_type_codes: Union[List[str], str] = []
) -> List[Dict]:
    """
    EDINET コードと帳票種別コードで開示書類リストをフィルタリングします。
    [1]
    """
    if len(edinet_codes) == 0:
        # edinet_codesが指定されていない場合、全てのedinetCodeを対象とする
        edinet_codes = [doc['edinetCode'] for doc in docs if 'edinetCode' in doc and doc['edinetCode'] is not None]
    elif isinstance(edinet_codes, str):
        edinet_codes = [edinet_codes]

    if len(doc_type_codes) == 0:
        # doc_type_codesが指定されていない場合、全てのdocTypeCodeを対象とする
        doc_type_codes = [doc['docTypeCode'] for doc in docs if 'docTypeCode' in doc and doc['docTypeCode'] is not None]
    elif isinstance(doc_type_codes, str):
        doc_type_codes = [doc_type_codes]

    # フィルタリングされた書類のリストを返す
    return [
        doc
        for doc in docs
        if doc.get('edinetCode') in edinet_codes and doc.get('docTypeCode') in doc_type_codes
    ]

def disclosure_documents(date: Union[str, datetime.date], api_key: str, type: int = 2) -> Dict:
    """
    指定日の開示書類メタデータをEDINET APIから取得します。
    [2, 3]
    """
    if isinstance(date, str):
        try:
            datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid date string. Use format 'YYYY-MM-DD'")
        date_str = date
    elif isinstance(date, datetime.date):
        date_str = date.strftime('%Y-%m-%d')
    else:
        raise TypeError("Date must be a string ('YYYY-MM-DD') or datetime.date")

    # EDINET 書類一覧APIのエンドポイントURL [3]
    url = "https://disclosure.edinet-fsa.go.jp/api/v2/documents.json"
    params = {
        "date": date_str,
        "type": type,  # '2' でメタデータと本文を取得 [3]
        "Subscription-Key": api_key,
    }

    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"

    with urllib.request.urlopen(full_url) as response:
        return json.loads(response.read().decode('utf-8'))

def get_document(doc_id: str, api_key: str) -> urllib.request.urlopen:
    """
    書類ID (doc_id) を指定して本文（ZIP/CSV等）を取得します。
    [4, 5]
    """
    # EDINET 書類取得APIのエンドポイントURL [4]
    url = f'https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}'
    params = {
        "type": 1,  # '1': XBRL形式, '5': CSV形式
        "Subscription-Key": api_key,
    }

    query_string = urllib.parse.urlencode(params)
    full_url = f'{url}?{query_string}'

    return urllib.request.urlopen(full_url)

def save_document(doc_res: urllib.request.urlopen, output_path: str) -> None:
    """
    ダウンロードした内容をファイルに保存します。
    [6]
    """
    with open(output_path, 'wb') as file_out:
        file_out.write(doc_res.read())
    print(f'Saved: {output_path}')

def get_documents_for_date_range(
    start_date: datetime.date,
    end_date: datetime.date,
    api_key: str, # APIキーを受け取る
    edinet_codes: List[str] = [],
    doc_type_codes: List[str] = []
) -> List[Dict]:
    """
    指定された日付範囲で開示書類を取得し、EDINETコードと書類種別コードでフィルタリングします。
    [6]
    """
    matching_docs = []
    current_date = start_date

    while current_date <= end_date:
        # disclosure_documents関数にAPIキーを渡す
        docs_res = disclosure_documents(date=current_date, api_key=api_key)
        if docs_res.get('results'): # 'results' キーが存在し、かつ内容があるか確認
            # filter_by_codesはAPIキーを必要としない
            filtered_docs = filter_by_codes(docs_res['results'], edinet_codes, doc_type_codes)
            matching_docs.extend(filtered_docs)
        current_date += datetime.timedelta(days=1)
    return matching_docs