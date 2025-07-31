# src/arelle_tools.py

from pathlib import Path
import zipfile
from arelle import Cntlr

def extract_xbrl_from_zips(outputs_dir: Path, extracted_dir: Path) -> dict[str, dict[str, str]]:
    """
    outputs_dir内のzipを解凍し、各xbrlファイルのパス辞書を返す。
    """
    xbrl_paths = {}

    for zip_path in outputs_dir.glob("*.zip"):
        zip_name = zip_path.stem
        extract_to = extracted_dir / zip_name

        extract_to.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

        public_doc_path = extract_to / "XBRL" / "PublicDoc"
        xbrl_files = list(public_doc_path.glob("*.xbrl"))
        if xbrl_files:
            xbrl_paths[zip_name] = {
                "xbrl_path": str(xbrl_files[0].resolve()),
                "base_dir": str(extract_to.resolve())
            }

    return xbrl_paths

def parse_xbrl(xbrl_file: Path) -> tuple[dict[str, str | None], list[tuple[str, str, str]]]:
    """
    XBRL を 1 度だけループして
      ・会社名 / 売上高 を meta 辞書で返す
      ・全 Fact を [(label_ja, label_en, value), ...] のリストで返す
    """
    ctrl = Cntlr.Cntlr(logFileName="logToPrint")
    model = ctrl.modelManager.load(str(xbrl_file))

    meta = {"company_name": None, "netsales": None}
    facts_list: list[tuple[str, str, str, str | None, str | None, str | None, str | None, str | None]] = []

    for fact in model.facts:
        ln = fact.concept.qname.localName
        if ln == "CompanyNameCoverPage":
            meta["company_name"] = fact.value
        elif ln == "NetSales":
            meta["netsales"] = fact.value
        
        label_ja = fact.concept.label(lang="ja")
        label_en = fact.concept.label(lang="en")
        value = str(fact.xValue)

        ctx = fact.context
        context_id = fact.contextID
        start_date = (
            ctx.startDatetime.isoformat()
            if ctx is not None and ctx.startDatetime is not None
            else None
        )
        end_date = (
            ctx.endDatetime.isoformat()
            if ctx is not None and ctx.endDatetime is not None
            else None
        )
        instant_date = (
            ctx.instantDatetime.isoformat()
            if ctx is not None and ctx.instantDatetime is not None
            else None
        )
        decimals = str(fact.decimals) if fact.isNumeric else None

        facts_list.append((
            label_ja, label_en, value,
            context_id, start_date, end_date, instant_date, decimals
        ))

    return meta, facts_list