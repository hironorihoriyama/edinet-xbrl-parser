import os
import zipfile
import pandas as pd
import xml.etree.ElementTree as ET

# 抽出したい代表的なタグ（localname）のセット
BS_TAGS = {
    "Assets", "Liabilities", "Equity", "NetAssets",
    "CurrentAssets", "NoncurrentAssets",
    "CurrentLiabilities", "NoncurrentLiabilities",
    "RetainedEarnings", "NetAssetsAttributableToOwnersOfParent"
}
PL_TAGS = {
    "Revenue", "OperatingIncome", "ProfitLoss",
    "ProfitLossBeforeTax", "ProfitLossAttributableToOwnersOfParent",
    "ComprehensiveIncome"
}
CF_TAGS = {
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInInvestingActivities",
    "NetCashProvidedByUsedInFinancingActivities",
    "NetIncreaseDecreaseInCashAndCashEquivalents"
}

# XBRL の namespace を許容（タグ解析に利用）
def _localname(tag: str) -> str:
    # "{namespace}Local" -> "Local"
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def parse_xbrl(file_bytes: bytes):
    """
    XBRLファイル(バイト列)を解析し、DataFrameを返す。
    """
    tree = ET.fromstring(file_bytes)

    # 1. context を収集
    contexts = {}
    for ctx in tree.findall(".//{*}context"):
        ctx_id = ctx.get("id")
        if not ctx_id:
            continue
        period = ctx.find("./{*}period")
        end_date = None
        # duration: startDate + endDate
        if period is not None:
            end_el = period.find("./{*}endDate")
            inst_el = period.find("./{*}instant")
            if end_el is not None:
                end_date = end_el.text
            elif inst_el is not None:
                end_date = inst_el.text
        contexts[ctx_id] = end_date

    records = []

    # 2. すべての要素を走査し、対象タグだけ抽出
    for elem in tree.iter():
        lname = _localname(elem.tag)
        if lname not in BS_TAGS | PL_TAGS | CF_TAGS:
            continue
        text = (elem.text or "").strip()
        if text == "":
            continue
        # 数値のみ対象（単位変換などは簡略）
        try:
            value = float(text.replace(",", ""))
        except ValueError:
            continue

        ctx_ref = elem.get("contextRef")
        period_end = contexts.get(ctx_ref)
        if not period_end:
            continue

        if lname in BS_TAGS:
            statement = "B/S"
        elif lname in PL_TAGS:
            statement = "P/L"
        else:
            statement = "C/F"

        records.append(
            {
                "PeriodEnd": period_end,
                "Statement": statement,
                "Account": lname,
                "Value": value,
            }
        )

    if not records:
        return pd.DataFrame(columns=["PeriodEnd", "Statement", "Account", "Value"])
    return pd.DataFrame(records)

def process_zip(zip_path: str) -> pd.DataFrame:
    """
    ZIP内の .xbrl ファイルを探してまとめて DataFrame へ。
    （最初に見つかった主ファイルのみ使いたい場合は break しても良い）
    """
    dfs = []
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if name.lower().endswith(".xbrl"):
                with z.open(name) as f:
                    try:
                        df = parse_xbrl(f.read())
                        if not df.empty:
                            dfs.append(df)
                    except Exception as e:
                        print(f"[WARN] {zip_path} の {name} 解析失敗: {e}")
    if not dfs:
        return pd.DataFrame(columns=["PeriodEnd", "Statement", "Account", "Value"])
    # 同一ZIP内に複数XBRLがある場合は結合
    return pd.concat(dfs, ignore_index=True)

def write_to_excel(edinet_code: str, df: pd.DataFrame, result_path: str):
    """
    result.xlsx に EDINETコードをシート名として書き込む（追記）。
    既存ファイルがあれば読み込み→該当シートを上書き。
    """
    sheet_name = edinet_code
    if os.path.exists(result_path):
        # 既存ブックに追記
        with pd.ExcelWriter(result_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        with pd.ExcelWriter(result_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

def main():
    src_dir = os.path.dirname(__file__)
    project_dir = os.path.abspath(os.path.join(src_dir, os.pardir))
    output_dir = os.path.join(project_dir, "outputs")
    result_path = os.path.join(output_dir, "result.xlsx")

    all_processed = False
    for fname in os.listdir(output_dir):
        if not fname.lower().endswith(".zip"):
            continue
        zip_path = os.path.join(output_dir, fname)
        # ファイル名の先頭部分を EDINET ID とみなす（例: E04539_2025-03.zip）
        edinet_code = fname.split("_")[0]

        print(f"Processing {fname} ...")
        df = process_zip(zip_path)
        if df.empty:
            print(f"  -> 有効な数値タグがありませんでした。")
            continue
        write_to_excel(edinet_code, df, result_path)
        all_processed = True
        print(f"  -> {len(df)} 行を書き込みました。")

    if not all_processed:
        print("XBRL ZIP が見つからないか、抽出できるデータがありませんでした。")
    else:
        print(f"\n完了しました。{result_path} を確認してください。")

if __name__ == "__main__":
    main()
