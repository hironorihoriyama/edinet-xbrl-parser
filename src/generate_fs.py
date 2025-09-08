"""Aggregate facts from XBRL files into a single CSV."""

from pathlib import Path
import os
from arelle_tools import extract_xbrl_from_zips, parse_xbrl
import shutil
import csv


def main() -> None:
    """Extract XBRL archives and generate a consolidated CSV."""
    outputs = Path(os.getenv("EDINET_OUTPUT_DIR", Path.cwd() / "outputs")).resolve()
    extracted = outputs / "extracted"
    merged_csv = outputs / "all_facts.csv"

    # Re-init working dir
    if extracted.exists():
        shutil.rmtree(extracted)
    extracted.mkdir(parents=True, exist_ok=True)

    # Gather XBRLs
    xbrl_paths = extract_xbrl_from_zips(outputs, extracted)

    aggregated: list[list[object]] = []

    print("✅ Start parsing:")
    for zip_name, info in xbrl_paths.items():
        xbrl_path = Path(info["xbrl_path"])
        meta, facts = parse_xbrl(xbrl_path)

        print(f"📁 {zip_name} Company:{meta['company_name']}  Net sales:{meta['netsales']}")
        aggregated.extend(facts)

    # ---------- Write aggregated facts to CSV (15 columns) ----------
    merged_csv.parent.mkdir(exist_ok=True, parents=True)
    with merged_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "QName(ID)",
                "Label(ja)",
                "Label(Preferred)",
                "Label Path",
                "QName Path",
                "Linkrole Definition",
                "値",
                "contextID",
                "期首",
                "期末",
                "時点(期末)",
                "decimals",
                "単位",
                "Consolidation Info",
                "Match Status",
            ]
        )
        writer.writerows(aggregated)

    print(f"\n📦 Saved all facts to a single CSV → {merged_csv}")


if __name__ == "__main__":
    main()
