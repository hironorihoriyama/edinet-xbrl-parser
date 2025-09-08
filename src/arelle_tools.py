"""Utilities for extracting and parsing XBRL files (presentation-order, consolidated CY)."""

from pathlib import Path
import zipfile
import re, html
from collections import Counter
from arelle import Cntlr, XbrlConst

# ===== ZIP 展開は既存のまま =====
def extract_xbrl_from_zips(outputs_dir: Path, extracted_dir: Path) -> dict[str, dict[str, str]]:
    """Extract XBRL files from ZIP archives."""
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


# ===== ここから抽出ロジック（あなた採用の仕様に差し替え） =====

# プレゼンテーション（親子）リンク
PARENT_CHILD_ARCROLE = XbrlConst.parentChild

# 表示順を合わせたい ELR コード（必要に応じて 322010 追加可能）
TARGET_ELR_CODES = {
    "310010",  # 連結貸借対照表
    "321010",  # 連結損益(及び包括利益)計算書
    "342010",  # 連結キャッシュ・フロー計算書（間接法）
    # "322010",  # 連結包括利益計算書（使う会社のみ。必要なら有効化）
}

# 値に HTML 断片が混じるのを弾く
_TAG_RE = re.compile(r"<[^>]+>")


def strip_xhtml(s: str | None) -> str:
    if not s:
        return ""
    return html.unescape(_TAG_RE.sub("", s)).replace("\xa0", " ").strip()


# 連結/個別 軸候補
AXIS_CANDIDATES = {
    "ConsolidatedOrNonConsolidatedAxis",
    "ConsolidatedAndNonConsolidatedAxis",
}


def consolidation_from_context(ctx) -> str:
    """文脈の次元から Consolidated / NonConsolidated / Unknown を返す。"""
    if ctx is None:
        return "Unknown"
    for dim_qn, dim_val in getattr(ctx, "qnameDims", {}).items():
        if dim_qn.localName in AXIS_CANDIDATES:
            mem = getattr(dim_val, "memberQname", None)
            if mem is None:
                return "Unknown"
            ln = mem.localName
            if ln == "ConsolidatedMember":
                return "Consolidated"
            if ln == "NonConsolidatedMember":
                return "NonConsolidated"
            return "Unknown"
    return "Unknown"


def extract_code_from_definition(def_text: str) -> str | None:
    """定義文頭の 6桁コードを抽出（例: '310010 連結貸借対照表' -> '310010'）"""
    if not def_text:
        return None
    m = re.match(r"^(\d{6})", def_text.strip())
    return m.group(1) if m else None


def is_target_elr(def_text: str) -> bool:
    code = extract_code_from_definition(def_text or "")
    return code in TARGET_ELR_CODES


def root_order_key(relset, root):
    """root 概念の '直下 arc の最小 order' をキーにして並べる"""
    rels = relset.fromModelObject(root)
    first = min((getattr(r, "order", 0.0) for r in rels), default=0.0)
    return (first, str(root.qname))


def iter_children_ordered(relset, parent):
    """子 arc を (order, QName) でソートして辿る。子の preferredLabel も返す。"""
    rels = relset.fromModelObject(parent)
    for r in sorted(rels, key=lambda r: (getattr(r, "order", 0.0), str(r.toModelObject.qname))):
        yield r, getattr(r, "preferredLabel", None)


def unit_to_str(u):
    """Arellé の unit を人間可読な文字列にする。"""
    if u is None:
        return None
    if hasattr(u, "value") and u.value is not None:
        return str(u.value)
    if hasattr(u, "measures") and u.measures:
        nums = [str(q) for q in (u.measures[0] or [])]
        dens = [str(q) for q in (u.measures[1] or [])]
        if dens:
            return f"{':'.join(nums)}/{':'.join(dens)}"
        return ":".join(nums)
    return None


def extract_consolidation_info(model_xbrl):
    """見出し側（parent-child 木）の Axis/Member から 'Consolidated/NonConsolidated/Unknown' を粗く推定。"""
    consolidation_paths = {}

    def traverse(relationship, current_path=None, passed_axis=None):
        if current_path is None:
            current_path = []
        to_qname = relationship.toModelObject.qname.localName
        if "Axis" in to_qname:
            passed_axis = to_qname
        new_path = current_path + [to_qname]
        if "Member" in to_qname and passed_axis == "ConsolidatedOrNonConsolidatedAxis":
            consolidation_paths[current_path[0]] = new_path
        for innerRel in relationshipset.modelRelationships:
            if innerRel.fromModelObject.qname.localName == to_qname:
                traverse(innerRel, new_path, passed_axis)

    for linkrole_uri in model_xbrl.relationshipSet(PARENT_CHILD_ARCROLE).linkRoleUris:
        relationshipset = model_xbrl.relationshipSet(PARENT_CHILD_ARCROLE, linkrole=linkrole_uri)
        for rel in relationshipset.modelRelationships:
            if "Heading" in rel.fromModelObject.qname.localName:
                traverse(rel, [rel.fromModelObject.qname.localName])

    consolidation_info = {}
    for heading, path in consolidation_paths.items():
        if "NonConsolidatedMember" in path[-1]:
            consolidation_info[heading] = "NonConsolidated"
        elif "ConsolidatedMember" in path[-1]:
            consolidation_info[heading] = "Consolidated"
        else:
            consolidation_info[heading] = "Unknown"
    return consolidation_info


def append_fact_row(
    rows: list[list[object]],
    fact,
    default_label: str,
    preferred_label: str,
    qname: str,
    current_label_path: str,
    current_qname_path: str,
    linkrole_definition: str,
    consolidation_status: str,
    mismatch_status: str,
):
    """CSV に 1 行追加。見出し行では fact=None を許容。"""
    if fact is None:
        # 見出し（abstract）行：値や文脈は空
        rows.append([
            qname, default_label, preferred_label, current_label_path, current_qname_path,
            linkrole_definition, "", "", "", "", "", "", "", consolidation_status, mismatch_status
        ])
        return

    value = fact.xValue
    context_id = fact.contextID
    ctx = fact.context
    start_date = ctx.startDatetime   if (ctx is not None and ctx.startDatetime   is not None) else None
    end_date = ctx.endDatetime       if (ctx is not None and ctx.endDatetime     is not None) else None
    instant_date = ctx.instantDatetime if (ctx is not None and ctx.instantDatetime is not None) else None
    decimals = fact.decimals if fact.isNumeric else 'N/A'
    unit = unit_to_str(getattr(fact, "unit", None))

    rows.append([
        qname, default_label, preferred_label, current_label_path, current_qname_path,
        linkrole_definition, value, context_id, start_date, end_date, instant_date,
        decimals, unit, consolidation_status, mismatch_status
    ])


def output_fact_with_hierarchy(
    model_xbrl,
    relationshipset,
    concept,
    path,
    qname_path,
    rows: list[list[object]],
    linkrole_definition: str,
    preferred_label_dict: dict,
    consolidation_info: dict[str, str],
    seen_qnames: set[str],
):
    """1つの概念（ノード）を処理：見出し行→当期連結の fact → 子を order 順に再帰。"""
    if concept is None:
        return

    default_label = strip_xhtml(concept.label(lang='ja')) or str(concept.qname)
    # ひとつ前の arc で決まった preferredLabel を優先
    preferred_label = preferred_label_dict.get(concept.qname, default_label)

    qname = str(concept.qname)
    current_label_path = ' > '.join(path + [preferred_label])
    current_qname_path = ' > '.join(qname_path + [qname])

    # 1) 見出し(abstract)は必ず 1 行出力
    if getattr(concept, "isAbstract", False):
        append_fact_row(
            rows, None, default_label, preferred_label, qname,
            current_label_path, current_qname_path, linkrole_definition,
            "Heading", ""
        )

    # 2) 概念に紐づく "当期連結" の値を 1 件だけ出力（CurrentYear* ヒューリスティック）
    for fact in model_xbrl.facts:
        if fact.concept.qname != concept.qname:
            continue

        heading_qname = current_qname_path.split(" > ")[0]
        prefix_removed_heading_qname = heading_qname.split(":")[-1]
        lr_status = consolidation_info.get(prefix_removed_heading_qname, "Unknown")

        context = model_xbrl.contexts.get(fact.contextID)
        ctx_cons = consolidation_from_context(context)

        effective_cons = ctx_cons if ctx_cons != "Unknown" else lr_status
        if effective_cons != "Consolidated":
            continue

        cid = fact.contextID or ""
        is_cy_duration = cid.startswith("CurrentYearDuration")
        is_cy_instant  = cid.startswith("CurrentYearInstant")
        if not (is_cy_duration or is_cy_instant):
            continue

        val = fact.xValue
        if isinstance(val, str) and _TAG_RE.search(val):
            continue

        # 同一概念の重複出力を避ける（最初の 1 件のみ）
        if qname in seen_qnames:
            continue
        seen_qnames.add(qname)

        mismatch_status = (
            "Match" if (lr_status in ("Consolidated", "NonConsolidated")
                        and ctx_cons in ("Consolidated", "NonConsolidated")
                        and lr_status == ctx_cons)
            else ("Mismatch" if lr_status in ("Consolidated", "NonConsolidated")
                  and ctx_cons in ("Consolidated", "NonConsolidated")
                  else "Unknown")
        )

        append_fact_row(
            rows, fact, default_label, preferred_label, qname,
            current_label_path, current_qname_path, linkrole_definition,
            effective_cons, mismatch_status
        )
        # 1 概念 1 行の方針なので break
        break

    # 3) 子（order 順）へ
    for r, child_pref_role in iter_children_ordered(relationshipset, concept):
        child = r.toModelObject
        # 子の表示名：preferredLabel を優先
        if child_pref_role:
            child_label = strip_xhtml(child.label(lang='ja', preferredLabel=child_pref_role)) \
                          or strip_xhtml(child.label(lang='en', preferredLabel=child_pref_role)) \
                          or str(child.qname)
        else:
            child_label = strip_xhtml(child.label(lang='ja')) \
                          or strip_xhtml(child.label(lang='en')) \
                          or str(child.qname)
        preferred_label_dict[child.qname] = child_label

        output_fact_with_hierarchy(
            model_xbrl, relationshipset, child, path + [preferred_label],
            qname_path + [qname], rows, linkrole_definition,
            preferred_label_dict, consolidation_info, seen_qnames
        )


def parse_xbrl(
    xbrl_file: Path,
):
    """
    XBRL から『当期の連結財務諸表（BS/PL/CF）を、PDFと同じ表示順』で取り出し、
    次の 15 列で返します（見出し行も含む）:

      ['QName(ID)','Label(ja)','Label(Preferred)','Label Path','QName Path',
       'Linkrole Definition','値','contextID','期首','期末','時点(期末)',
       'decimals','単位','Consolidation Info','Match Status']
    """
    ctrl = Cntlr.Cntlr(logFileName="logToPrint")
    model_xbrl = ctrl.modelManager.load(str(xbrl_file))

    # ---- メタ情報（既存のまま） ----
    meta = {"company_name": None, "netsales": None}
    for fact in model_xbrl.facts:
        ln = fact.concept.qname.localName
        if ln == "CompanyNameCoverPage":
            meta["company_name"] = fact.value
        elif ln == "NetSales":
            meta["netsales"] = fact.value

    # ---- プレゼン木の準備 ----
    consolidation_info = extract_consolidation_info(model_xbrl)

    # 対象 ELR を抽出
    targets: list[tuple[str, str, str]] = []
    for linkrole_uri in model_xbrl.relationshipSet(PARENT_CHILD_ARCROLE).linkRoleUris:
        role_types = model_xbrl.roleTypes.get(linkrole_uri)
        definition = strip_xhtml(role_types[0].definition) if role_types else ""
        if is_target_elr(definition):
            code = extract_code_from_definition(definition) or ""
            targets.append((code, linkrole_uri, definition))

    rows: list[list[object]] = []
    preferred_label_dict: dict = {}
    seen_qnames: set[str] = set()

    # コード順で処理（310010 -> 321010 -> 342010）
    for code, linkrole_uri, linkrole_definition in sorted(targets, key=lambda t: (t[0], t[2])):
        relset = model_xbrl.relationshipSet(PARENT_CHILD_ARCROLE, linkrole=linkrole_uri)
        roots = sorted(relset.rootConcepts, key=lambda c: root_order_key(relset, c))
        for root in roots:
            output_fact_with_hierarchy(
                model_xbrl, relset, root, [], [],
                rows, linkrole_definition, preferred_label_dict, consolidation_info, seen_qnames
            )

    # rows はプレゼン順のまま返す（最後に sort はしない）
    return meta, [tuple(r) for r in rows]
