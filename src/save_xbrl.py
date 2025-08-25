# src/save_xbrl.py

import datetime
import os
import shutil
import sys
from typing import List, Dict

from dotenv import load_dotenv
from tqdm import tqdm            # ★ 進捗バー

# 自作モジュール
from edinet_tools import (
    filter_by_codes,
    disclosure_documents,
    get_document,
    save_document,
)

# --------------------------------------------------------------------------- #
# 1. API キー読み込み
# --------------------------------------------------------------------------- #
load_dotenv()
EDINET_API_KEY = os.getenv("EDINET_API_KEY")
if not EDINET_API_KEY:
    sys.exit(
        "EDINET_API_KEY が設定されていません。.env を確認してください。\n"
        "例)  EDINET_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx"
    )

# --------------------------------------------------------------------------- #
# 2. 取得条件（企業・書類種別・期間）
# --------------------------------------------------------------------------- #
TARGETS = {              # 他社を増やすときはここに追記
    "E04539": "Imperial Hotel, Ltd.",
}
DOC_TYPE_CODES = ["120"]          # 有価証券報告書 + 訂正
END_DATE = datetime.date.today()
START_DATE = END_DATE.replace(year=END_DATE.year - 2)  # 直近x年（最大10年）

# 保存先
from pathlib import Path
OUTPUT_DIR = str(
    Path(os.getenv("EDINET_OUTPUT_DIR", Path.cwd() / "outputs")).resolve()
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------------------------------------------------- #
# 3. メイン処理
# --------------------------------------------------------------------------- #
def run() -> None:
    # -------- 3‑0. outputs ディレクトリの初期化 -------- #
    if os.path.isdir(OUTPUT_DIR):
        for name in os.listdir(OUTPUT_DIR):
            path = os.path.join(OUTPUT_DIR, name)
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception as e:
                print(f"[WARN] {path} の削除に失敗 ({e})")

    # -------- 3‑1. 日次ループで docID を収集（メタデータと本文を取得） -------- #
    print(
        f"\n* EDINET Downloader *\n"
        f"企業: {', '.join(TARGETS.values())}\n"
        f"書類種別: {DOC_TYPE_CODES}\n"
        f"期間: {START_DATE} ～ {END_DATE}\n"
        f"保存先: {os.path.abspath(OUTPUT_DIR)}\n"
    )

    total_days = (END_DATE - START_DATE).days + 1
    hits: List[Dict] = []

    for offset in tqdm(range(total_days), desc="メタデータ取得", unit="day"):
        current = START_DATE + datetime.timedelta(days=offset)
        try:
            meta = disclosure_documents(
                current, api_key=EDINET_API_KEY
            )
            if meta.get("results"):
                filtered = filter_by_codes(
                    meta["results"],
                    edinet_codes=list(TARGETS.keys()),
                    doc_type_codes=DOC_TYPE_CODES,
                )
                hits.extend(filtered)
        except Exception as e:
            # 通信エラーなどを無視して次の日へ
            print(f"\n[WARN] {current} 取得失敗 ({e})")

    print(f"\nヒット件数: {len(hits)} 件\n")

    # -------- 3‑2. 各 docID を XBRL ZIP として保存 -------- #
    for idx, doc in enumerate(tqdm(hits, desc="ファイルダウンロード"), start=1):
        doc_id       = doc["docID"]
        edinet_code  = doc["edinetCode"]
        doc_type     = doc["docTypeCode"]
        filer_name   = TARGETS.get(edinet_code, "Unknown").replace(" ", "")
        period_end = doc.get("periodEnd", "")
        report_period = period_end[:7]
        save_name    = f"{edinet_code}_{report_period}.zip"
        save_path    = os.path.join(OUTPUT_DIR, save_name)

        try:
            res = get_document(doc_id, EDINET_API_KEY)  # type=1 固定 → XBRL ZIP
            save_document(res, save_path)
        except Exception as e:
            print(f"[ERROR] {doc_id} ダウンロード失敗 ({e})")
            continue

    print("\n完了しました。outputs フォルダを確認してください。")


if __name__ == "__main__":
    run()
