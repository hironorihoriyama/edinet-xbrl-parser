# src/generate_fs.py

from pathlib import Path
import os
from arelle_tools import extract_xbrl_from_zips, parse_xbrl
import shutil, csv

def main() -> None:
    # 出力先は CWD を既定。EDINET_OUTPUT_DIR があればそれを優先。
    outputs = Path(os.getenv("EDINET_OUTPUT_DIR", Path.cwd() / "outputs")).resolve()
    extracted = outputs / "extracted"
    merged_csv = outputs / "all_facts.csv"

    # 作業ディレクトリを初期化
    if extracted.exists():
        shutil.rmtree(extracted)
    extracted.mkdir(parents=True, exist_ok=True)

    # zip を展開してパス辞書取得
    xbrl_paths = extract_xbrl_from_zips(outputs, extracted)

    aggregated: list[
        tuple[str, str, str, str | None, str | None, str | None, str | None, str | None]
    ] = []

    print("✅ 解析開始:")
    for zip_name, info in xbrl_paths.items():
        xbrl_path = Path(info["xbrl_path"])
        meta, facts = parse_xbrl(xbrl_path)

        print(f"📁 {zip_name} 会社名:{meta['company_name']}  売上高:{meta['netsales']}")

        aggregated.extend(facts)

    # ---------- まとめて CSV 出力 ----------
    merged_csv.parent.mkdir(exist_ok=True, parents=True)
    with merged_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "日本語ラベル", "英語ラベル", "値",
            "contextID", "期首", "期末", "時点(期末)", "decimals"
        ])
        writer.writerows(aggregated)

    print(f"\n📦 全 Fact を 1 つの CSV に保存しました → {merged_csv}")

if __name__ == "__main__":
    main()
