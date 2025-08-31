"""Utilities for extracting and parsing XBRL files."""

from pathlib import Path
import zipfile
from arelle import Cntlr


def extract_xbrl_from_zips(outputs_dir: Path, extracted_dir: Path) -> dict[str, dict[str, str]]:
    """Extract XBRL files from ZIP archives.

    Args:
        outputs_dir (Path): Directory containing ZIP files.
        extracted_dir (Path): Destination directory for extracted files.

    Returns:
        dict[str, dict[str, str]]: Mapping of archive name to paths for the
        extracted XBRL file and its base directory.
    """
    xbrl_paths: dict[str, dict[str, str]] = {}

    for zip_path in outputs_dir.glob("*.zip"):
        zip_name = zip_path.stem
        extract_to = extracted_dir / zip_name

        extract_to.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)

        public_doc_path = extract_to / "XBRL" / "PublicDoc"
        xbrl_files = list(public_doc_path.glob("*.xbrl"))
        if xbrl_files:
            xbrl_paths[zip_name] = {
                "xbrl_path": str(xbrl_files[0].resolve()),
                "base_dir": str(extract_to.resolve()),
            }

    return xbrl_paths

def parse_xbrl(
    xbrl_file: Path,
) -> tuple[
    dict[str, str | None],
    list[
        tuple[
            str,
            str,
            str,
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
        ]
    ],
]:
    """Parse a single XBRL file and collect facts.

    The XBRL is iterated once to extract metadata and all facts. Metadata
    consists of the company name and net sales. Each fact is stored as an
    8-element tuple containing labels, value, context, period information, and
    decimals.

    Args:
        xbrl_file (Path): Path to the XBRL file.

    Returns:
        tuple[dict[str, str | None], list[tuple[str, str, str, str | None,
        str | None, str | None, str | None, str | None]]]:
        Metadata dictionary and a list of fact tuples.
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

        facts_list.append(
            (
                label_ja,
                label_en,
                value,
                context_id,
                start_date,
                end_date,
                instant_date,
                decimals,
            )
        )

    return meta, facts_list
