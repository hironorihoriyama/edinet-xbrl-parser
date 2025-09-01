"""Download XBRL files from EDINET based on specified criteria."""

import datetime
import os
import shutil
import sys
from typing import List, Dict

from dotenv import load_dotenv
from tqdm import tqdm  # Progress bar.

# Local modules.
from edinet_tools import (
    filter_by_codes,
    disclosure_documents,
    get_document,
    save_document,
)

# --------------------------------------------------------------------------- #
# 1. Load API key
# --------------------------------------------------------------------------- #
load_dotenv()
EDINET_API_KEY = os.getenv("EDINET_API_KEY")
if not EDINET_API_KEY:
    sys.exit(
        "EDINET_API_KEY is not set. Check the .env file.\n"
        "Example: EDINET_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx"
    )

# --------------------------------------------------------------------------- #
# 2. Retrieval conditions (companies, document types, period)
# --------------------------------------------------------------------------- #
TARGETS = {  # Add more companies here as needed.
    "E04539": "Imperial Hotel, Ltd.",
}
DOC_TYPE_CODES = ["120"]  # Securities report + amendments.
END_DATE = datetime.date.today()
START_DATE = END_DATE.replace(year=END_DATE.year - 2)  # Recent x years (max 10).

# Output directory.
from pathlib import Path
OUTPUT_DIR = str(
    Path(os.getenv("EDINET_OUTPUT_DIR", Path.cwd() / "outputs")).resolve()
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------------------------------------------------- #
# 3. Main processing
# --------------------------------------------------------------------------- #
def run() -> None:
    """Download XBRL files that match the configured criteria."""
    # -------- 3-0. Initialize outputs directory -------- #
    if os.path.isdir(OUTPUT_DIR):
        for name in os.listdir(OUTPUT_DIR):
            path = os.path.join(OUTPUT_DIR, name)
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception as e:
                print(f"[WARN] Failed to remove {path} ({e})")

    # -------- 3-1. Collect docIDs by iterating over dates -------- #
    print(
        f"\n* EDINET Downloader *\n"
        f"Companies: {', '.join(TARGETS.values())}\n"
        f"Document types: {DOC_TYPE_CODES}\n"
        f"Period: {START_DATE} ~ {END_DATE}\n"
        f"Output: {os.path.abspath(OUTPUT_DIR)}\n"
    )

    total_days = (END_DATE - START_DATE).days + 1
    hits: List[Dict] = []

    for offset in tqdm(range(total_days), desc="Fetch metadata", unit="day"):
        current = START_DATE + datetime.timedelta(days=offset)
        try:
            meta = disclosure_documents(current, api_key=EDINET_API_KEY)
            if meta.get("results"):
                filtered = filter_by_codes(
                    meta["results"],
                    edinet_codes=list(TARGETS.keys()),
                    doc_type_codes=DOC_TYPE_CODES,
                )
                hits.extend(filtered)
        except Exception as e:
            # Ignore communication errors and continue with the next day.
            print(f"\n[WARN] Failed to fetch {current} ({e})")

    print(f"\nHit count: {len(hits)} documents\n")

    # -------- 3-2. Save each docID as an XBRL ZIP -------- #
    for idx, doc in enumerate(tqdm(hits, desc="Download files"), start=1):
        doc_id = doc["docID"]
        edinet_code = doc["edinetCode"]
        doc_type = doc["docTypeCode"]
        filer_name = TARGETS.get(edinet_code, "Unknown").replace(" ", "")
        period_end = doc.get("periodEnd", "")
        report_period = period_end[:7]
        save_name = f"{edinet_code}_{report_period}.zip"
        save_path = os.path.join(OUTPUT_DIR, save_name)

        try:
            res = get_document(doc_id, EDINET_API_KEY)  # type=1 fixed → XBRL ZIP
            save_document(res, save_path)
        except Exception as e:
            print(f"[ERROR] Failed to download {doc_id} ({e})")
            continue

    print("\nFinished. Please check the outputs folder.")


if __name__ == "__main__":
    run()

