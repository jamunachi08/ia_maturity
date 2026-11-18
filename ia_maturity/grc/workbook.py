"""Versioned GRC workbook content and policy, independent of IA20.

The parser reads OOXML values only. It never runs Excel formulas or macros.
Published instruments and assessments retain the source hash and cell locators.
"""
from collections import Counter
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

SOURCE_HASH = "0b3da727eab7fd9042f5cadcc26dc43c30d3a8f774ffac759f4b24fd03867ab8"
SEED_PATH = Path(__file__).parent.parent / "setup_data" / "grc_maturity_v1.json"
TEMPLATE_NAME = "GRC Maturity Assessment (46Q) v1.0"
SECTIONS = {"GRC Maturity Awareness": "Awareness", "Governance": "Governance", "Risk": "Risk", "Compliance": "Compliance"}
EXPECTED_COUNTS = {"Awareness": 2, "Governance": 14, "Risk": 17, "Compliance": 13}
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REQUIRED_SHEETS = ("Instructions", "Questionnaire", "Profile", "Results", "Lists", "Regulators", "SectorRegulators", "Config", "IT_Spec")


def parse_workbook(source):
    """Read an authorized local workbook or uploaded bytes into a reviewable instrument."""
    raw = source if isinstance(source, bytes) else Path(source).read_bytes()
    if len(raw) > 20 * 1024 * 1024:
        raise ValueError("Workbook exceeds 20 MB.")
    with ZipFile(BytesIO(raw)) as archive:
        if sum(i.file_size for i in archive.infolist()) > 100 * 1024 * 1024:
            raise ValueError("Expanded workbook exceeds 100 MB.")
        if any("vbaProject" in i.filename for i in archive.infolist()):
            raise ValueError("Macro-enabled workbooks are not supported.")
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(e.itertext()) for e in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        relationships = {e.get("Id"): e.get("Target") for e in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        sheets, manifest = {}, {}
        for sheet in ET.fromstring(archive.read("xl/workbook.xml")).findall("s:sheets/s:sheet", NS):
            target = relationships[sheet.get("{" + REL + "}id")]
            path = target.lstrip("/") if target.startswith("/") else "xl/" + target
            if ".." in Path(path).parts:
                raise ValueError("Invalid worksheet path.")
            xml = ET.fromstring(archive.read(path)); cells = {}; formulas = 0
            for cell in xml.findall(".//s:sheetData/s:row/s:c", NS):
                value = cell.find("s:v", NS)
                text = value.text or "" if value is not None else ""
                if cell.get("t") == "s" and text:
                    text = strings[int(text)]
                elif cell.get("t") == "inlineStr":
                    text = "".join(cell.find("s:is", NS).itertext())
                cells[cell.get("r")] = text
                formulas += cell.find("s:f", NS) is not None
            sheets[sheet.get("name")] = cells
            manifest[sheet.get("name")] = {"nonempty_cells": sum(bool(v) for v in cells.values()), "formula_count": formulas}
    if set(sheets) != set(REQUIRED_SHEETS):
        raise ValueError("Expected the nine GRC workbook sheets.")
    cells = sheets["Questionnaire"]; questions = []; topics = {}
    for ref, code in cells.items():
        if not re.fullmatch(r"A[0-9]+", ref) or not re.fullmatch(r"Q[0-9]+", code):
            continue
        row = ref[1:]; section = cells.get("B" + row, "")
        if section not in SECTIONS:
            raise ValueError("Unknown questionnaire section: " + section)
        topic = cells.get("C" + row, "")
        topic = "" if topic in ("", "—", "-") else topic
        if topic:
            topics.setdefault((SECTIONS[section], topic), "T" + str(len(topics) + 1))
        questions.append({"question_code": code, "section_code": SECTIONS[section], "topic_code": topics.get((SECTIONS[section], topic), ""),
            "topic_title": topic, "question_text": cells.get("D" + row, ""), "source_ref": "Questionnaire!A" + row + ":H" + row,
            **{"option_" + letter.lower(): cells.get(col + row, "") for letter, col in zip("ABCD", "EFGH")}})
    questions.sort(key=lambda q: int(q["question_code"][1:]))
    config = sheets["Config"]
    bands = []
    for ref, value in config.items():
        if re.fullmatch(r"A[0-9]+", ref) and value in ("Critical", "Low", "Medium", "High", "Leading"):
            row = ref[1:]
            if config.get("B" + row) and config.get("C" + row):
                bands.append({"level_name": value, "min_score": float(config["B" + row]), "max_score": float(config["C" + row]), "interpretation": config.get("D" + row, "")})
    bands.sort(key=lambda b: b["min_score"])
    instrument = {"schema_version": 1, "source": {"filename": "GRC_Maturity_Questionnaire V1.0.xlsx", "sha256": hashlib.sha256(raw).hexdigest(), "sheets": manifest},
        "title": "GRC Maturity Assessment", "version": "1.0", "questions": questions,
        "sections": [{"section_code": code, "section_title": "GRC General Maturity Awareness" if code == "Awareness" else title,
            "scope_requirement": "Mandatory" if code == "Awareness" else "Optional", "weight": 1} for title, code in SECTIONS.items()],
        "bands": bands,
        "instructions": {key: sheets["Instructions"].get(key, "") for key in ("B3", "B4", "B5", "B6", "B7", "B8", "B9")},
        "arabic_content_approved": False}
    validate_instrument(instrument)
    return instrument


def validate_instrument(data):
    """Fail closed before creating or publishing malformed source content."""
    questions = data.get("questions", [])
    if [q.get("question_code") for q in questions] != ["Q" + str(i) for i in range(1, 47)]:
        raise ValueError("The workbook must contain ordered, unique Q1-Q46.")
    if dict(Counter(q.get("section_code") for q in questions)) != EXPECTED_COUNTS:
        raise ValueError("GRC section counts must be 2, 14, 17 and 13.")
    if len({q["topic_code"] for q in questions if q.get("topic_code")}) != 13:
        raise ValueError("The workbook must contain 13 named topics.")
    for q in questions:
        if not q.get("question_text") or any(not q.get("option_" + v) for v in "abcd"):
            raise ValueError("Question " + q["question_code"] + " is missing text or an answer statement.")
    if [b.get("min_score") for b in data.get("bands", [])] != [0, 35, 55, 75, 90]:
        raise ValueError("Unexpected workbook maturity thresholds.")
    if not re.fullmatch(r"[0-9a-f]{64}", data.get("source", {}).get("sha256", "")):
        raise ValueError("Workbook source hash is required.")
    return data


def instrument():
    return validate_instrument(json.loads(SEED_PATH.read_text(encoding="utf-8")))


def published_policy(template=None):
    """GRC policy belongs to this instrument; never inherit IA settings or issue gates."""
    data = instrument()
    palette = ["#B42318", "#BF530B", "#9A6F00", "#2D7A33", "#1C5CA3"]
    bands = [{**deepcopy(b), "color": palette[i], "level_name_ar": "", "interpretation_ar": ""} for i, b in enumerate(data["bands"])]
    return {"points": {"A": 25, "B": 50, "C": 75, "D": 100}, "max_points": 100, "bands": bands,
        "create_actions_for": "A and B", "evidence_required_from": "", "issues": {"lock_auto_answers": 0},
        "weighting_method": "Points (each question equal)", "template_version": template.version if template else data["version"],
        "instrument": "GRC", "framework": "Governance, Risk and Compliance maturity", "source_sha256": data["source"]["sha256"], "gating_enabled": False}


def preview_import(source, current=None):
    candidate = parse_workbook(source)
    previous = current or instrument()
    old = {q["question_code"]: q for q in previous["questions"]}
    changed = [q["question_code"] for q in candidate["questions"] if old.get(q["question_code"]) != q]
    return {"source": candidate["source"], "question_count": len(candidate["questions"]), "changed_questions": changed,
        "policy_changed": candidate["bands"] != previous["bands"], "instrument": candidate}


def install_grc_template():
    """Idempotent site-scoped seed; never replace IA20 or rewrite a published version."""
    import frappe
    from ia_maturity.grc import security as sec
    from ia_maturity.grc.assessments import publish
    if not sec.enabled():
        return None
    data = instrument()
    # Cloned draft versions retain provenance. Their hash is not authorization
    # for setup to publish them; only this canonical seed may be resumed here.
    existing = frappe.db.get_value("IA Maturity Template", {"name": TEMPLATE_NAME,
        "grc_source_sha256": data["source"]["sha256"], "assessment_type": "GRC"}, "name")
    if existing:
        with sec.service_write():
            publish(existing)
            _ensure_scope(existing)
        return existing
    if frappe.db.exists("IA Maturity Template", TEMPLATE_NAME):
        frappe.throw("The GRC seed name is occupied by another source. Publish a new version explicitly.")
    values = {"doctype": "IA Maturity Template", "template_name": TEMPLATE_NAME, "version": data["version"], "assessment_type": "GRC",
        "framework": "Governance, Risk and Compliance maturity", "weighting_method": "Points (each question equal)", "is_active": 1,
        "introduction": "Assess the selected Governance, Risk and Compliance sections. General Maturity Awareness is always included.",
        "answer_rule": "Choose one answer for every displayed question: A, B, C, D or N/A. N/A is excluded from the score. Save and continue later at any time.",
        "grc_source_sha256": data["source"]["sha256"], "grc_source_manifest": frappe.as_json(data["source"]),
        "sections": data["sections"], "questions": [{**q, "short_label": q["topic_title"] or "GRC maturity awareness", "allow_na": 1, "selection_mode": "Single",
            "is_gating": 0, "auto_source": "", "allow_comment": "Disabled", "allow_attachment": "Disabled"} for q in data["questions"]]}
    with sec.service_write():
        doc = frappe.get_doc(values).insert(ignore_permissions=True)
        publish(doc.name)
        _ensure_scope(doc.name)
    return doc.name


def _ensure_scope(name):
    import frappe
    from ia_maturity.grc import scope
    if not frappe.db.exists(scope.CONFIG, {"template": name, "published": 1}):
        configuration = {"required_sections": ["Awareness"], "packages": [{"code": section, "label": section, "label_ar": "", "description": "Include " + section.lower() + " maturity questions.", "description_ar": "", "sections": [section]} for section in ("Risk", "Compliance", "Governance")]}
        # Portable across v15/v16: v16 rejects SQL functions such as "max(version)" as field strings.
        latest = frappe.get_all(scope.CONFIG, filters={"template": name}, pluck="version",
            order_by="version desc", limit=1)
        version = int(latest[0] if latest else 0) + 1
        with scope.writing():
            frappe.get_doc({"doctype": scope.CONFIG, "template": name, "version": version, "published": 1, "configuration": frappe.as_json(configuration)}).insert(ignore_permissions=True)
    if not frappe.db.exists("IA Maturity Template", {"assessment_type": "GRC", "grc_is_default": 1, "is_active": 1, "grc_published": 1}):
        frappe.db.set_value("IA Maturity Template", name, "grc_is_default", 1)
