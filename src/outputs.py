# src/outputs.py

import os
from pathlib import Path
import zipfile
import pandas as pd

def aggregate_outputs(
    output_dir: str,
    result_path: str,
    sheet_name: str = "data"
):
    # 全 ZIP を探索
    dfs = []
    for fname in os.listdir(output_dir):
        if not fname.lower().endswith(".zip"):
            continue
        zip_path = os.path.join(output_dir, fname)
        # ZIP 名から年度ラベルを抽出（拡張子なし）
        label = os.path.splitext(fname)[0]

        with zipfile.ZipFile(zip_path, "r") as z:
            # XBRL_TO_CSV フォルダ内の jpcrp*.csv をすべて読み込む
            for member in z.namelist():
                if member.startswith("XBRL_TO_CSV/jpcrp") and member.endswith(".csv"):
                    with z.open(member) as f:
                        # UTF-16LE + タブ区切り
                        df = pd.read_csv(f, sep="\t", encoding="utf-16")
                        # 左端に「年度」列を追加
                        df.insert(0, "年度", label)
                        # フィルタ処理
                        valid_periods = ["当期", "当期末"]
                        df = df[
                            df["相対年度"].isin(valid_periods) & (df["連結・個別"] == "連結")
                        ]
                        if not df.empty:
                            dfs.append(df)

    if not dfs:
        print("No jpcrp CSV files found.")
        return

    # ヘッダーは全ファイル同一なのでそのまま concat
    result_df = pd.concat(dfs, ignore_index=True)

    # Excel に書き出し
    with pd.ExcelWriter(result_path, engine="openpyxl") as writer:
        result_df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Written {len(result_df)} rows to {result_path} (sheet: {sheet_name})")

def main() -> None:
    outdir = Path(os.getenv("EDINET_OUTPUT_DIR", Path.cwd() / "outputs")).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    resfile = outdir / "result.xlsx"
    aggregate_outputs(str(outdir), str(resfile))

if __name__ == "__main__":
    main()