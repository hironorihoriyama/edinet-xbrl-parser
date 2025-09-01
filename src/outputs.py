"""Aggregate converted CSV outputs into a single Excel file."""

import os
from pathlib import Path
import zipfile
import pandas as pd


def aggregate_outputs(
    output_dir: str,
    result_path: str,
    sheet_name: str = "data",
):
    """Collect jpcrp CSV files from ZIP archives and merge into Excel."""
    # Scan all ZIP files in the output directory.
    dfs = []
    for fname in os.listdir(output_dir):
        if not fname.lower().endswith(".zip"):
            continue
        zip_path = os.path.join(output_dir, fname)
        # Derive the year label from the ZIP name.
        label = os.path.splitext(fname)[0]

        with zipfile.ZipFile(zip_path, "r") as z:
            # Read all jpcrp*.csv files under XBRL_TO_CSV.
            for member in z.namelist():
                if member.startswith("XBRL_TO_CSV/jpcrp") and member.endswith(".csv"):
                    with z.open(member) as f:
                        # UTF-16LE with tab separation.
                        df = pd.read_csv(f, sep="\t", encoding="utf-16")
                        # Insert a "年度" column at the start.
                        df.insert(0, "年度", label)
                        # Filter for consolidated current period values.
                        valid_periods = ["当期", "当期末"]
                        df = df[
                            df["相対年度"].isin(valid_periods)
                            & (df["連結・個別"] == "連結")
                        ]
                        if not df.empty:
                            dfs.append(df)

    if not dfs:
        print("No jpcrp CSV files found.")
        return

    # Headers are identical across files, so simply concatenate.
    result_df = pd.concat(dfs, ignore_index=True)

    # Write to Excel.
    with pd.ExcelWriter(result_path, engine="openpyxl") as writer:
        result_df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Written {len(result_df)} rows to {result_path} (sheet: {sheet_name})")


def main() -> None:
    """Entry point for command-line execution."""
    outdir = Path(os.getenv("EDINET_OUTPUT_DIR", Path.cwd() / "outputs")).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    resfile = outdir / "result.xlsx"
    aggregate_outputs(str(outdir), str(resfile))


if __name__ == "__main__":
    main()

