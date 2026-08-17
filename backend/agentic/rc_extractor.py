"""
fynd(cars) — RC Document Extractor (Gate 3 / Docling layer)
Extracts structured fields from Registration Certificate bytes.

Pipeline:
  1. Docling DocumentStream → Markdown (local, no disk write, no remote calls)
  2. Regex pass for common Indian RC field patterns
  3. LLM structured-extraction fallback if LLM_ENABLED=1 (same OpenRouter provider)

Returns dict with None for any field that could not be read (E12: legacy RC book).

ponytail: no class, single function, regex-first then LLM — cheapest path first.
"""
from __future__ import annotations

import json
import logging
import os
import re
from io import BytesIO

logger = logging.getLogger("fynd(cars)_api")


# ---------------------------------------------------------------------------
# Pre-compiled regex patterns for RC extraction
# ---------------------------------------------------------------------------

_PATTERNS: dict[str, re.Pattern] = {
    "registration_number": re.compile(r"(?:Regn\.?\s*No\.?|Registration\s*No\.?|Reg\.\s*No\.?)[:\s]+([A-Z]{2}[\s-]?\d{2}[\s-]?[A-Z]{1,3}[\s-]?\d{1,4})", re.IGNORECASE),
    "chassis_vin":         re.compile(r"(?:Chassis\s*No\.?|VIN)[:\s]+([A-HJ-NPR-Z0-9]{6,17})", re.IGNORECASE),
    "engine_number":       re.compile(r"(?:Engine\s*No\.?)[:\s]+([A-Z0-9]{6,20})", re.IGNORECASE),
    "make":                re.compile(r"(?:Maker(?:'s)?\s*Name|Make|Manufacturer)[:\s]+([A-Za-z\s\-]+?)(?:\n|,|Model|$)", re.IGNORECASE),
    "model":               re.compile(r"(?:Model)[:\s]+([A-Za-z0-9\s\-/]+?)(?:\n|,|Variant|Fuel|$)", re.IGNORECASE),
    "variant":             re.compile(r"(?:Variant|Version)[:\s]+([A-Za-z0-9\s\-/\.]+?)(?:\n|,|Fuel|Year|$)", re.IGNORECASE),
    "fuel_type":           re.compile(r"(?:Fuel\s*Type|Fuel)[:\s]+(Petrol|Diesel|Electric|CNG|Hybrid|LPG|PNG)", re.IGNORECASE),
    "owner_serial":        re.compile(r"(?:Owner\s*Serial\s*No\.?|Owner\s*No\.?)[:\s]+(\d+)", re.IGNORECASE),
    "registration_date":   re.compile(r"(?:Date\s*of\s*Regn\.?|Registration\s*Date)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.IGNORECASE),
    "year":                re.compile(r"(?:Mfg\.?\s*Year|Year\s*of\s*Mfg\.?|Manufacturing\s*Year)[:\s]+(\d{4})", re.IGNORECASE),
}


def _regex_extract(text: str) -> dict:
    """Fast regex pass over markdown text. Returns partial dict — missing = None."""
    result: dict = {}
    for field, pat in _PATTERNS.items():
        m = pat.search(text)
        result[field] = m.group(1).strip() if m else None

    if result.get("fuel_type"):
        result["fuel_type"] = result["fuel_type"].lower()

    for int_field in ("year", "owner_serial"):
        if result.get(int_field):
            try:
                result[int_field] = int(result[int_field])
            except ValueError:
                result[int_field] = None

    return result


def _llm_extract(markdown: str) -> dict:
    """
    LLM fallback for faded/non-standard RCs.
    One call, JSON-only output, same OpenRouter provider.
    """
    from agentic.llm.providers import build_provider_from_env

    prompt = f"""Extract fields from this vehicle Registration Certificate text.
Return ONLY a JSON object with these keys (use null if a field is absent or unreadable):
registration_number, chassis_vin, engine_number, make, model, variant,
year (integer), fuel_type (one of: petrol diesel electric cng hybrid),
owner_serial (integer), registration_date (YYYY-MM-DD if parseable).

RC text:
\"\"\"
{markdown[:4000]}
\"\"\"

JSON only, no explanation."""

    provider = build_provider_from_env()
    raw = (provider.generate(prompt) or "").strip()

    # Strip markdown fences if the model added them despite instructions
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("RC LLM extraction: JSON parse failed — returning empty dict")
        return {}


def extract_rc_fields(doc_bytes: bytes, filename: str = "document.pdf") -> dict:
    """
    Extract structured RC fields from raw document bytes.

    Args:
        doc_bytes: Raw bytes of the RC document (PDF, image, DOCX, etc.)
        filename:  Original filename hint for Docling format detection.

    Returns:
        Dict with keys: registration_number, chassis_vin, engine_number,
        make, model, variant, year, fuel_type, owner_serial, registration_date.
        Any field that could not be read is None (E12 safe: legacy RC book).

    ponytail: no local file write — uses DocumentStream directly.
    """
    markdown = ""
    try:
        from docling.document_converter import DocumentConverter, DocumentStream

        stream = DocumentStream(name=filename, stream=BytesIO(doc_bytes))
        converter = DocumentConverter()
        result = converter.convert(stream)
        markdown = result.document.export_to_markdown()
        logger.info("Docling extracted %d chars from %s", len(markdown), filename)
    except Exception as e:
        logger.error("Docling extraction failed for %s: %s", filename, e)
        # ponytail: if Docling fails, still attempt LLM on empty string (returns all-None)
        markdown = ""

    # Step 1: regex pass
    extracted = _regex_extract(markdown)

    # Step 2: LLM fallback — only for fields still missing AND LLM enabled
    missing_fields = [k for k, v in extracted.items() if v is None]
    llm_enabled = os.getenv("LLM_ENABLED", "0") == "1"

    if missing_fields and llm_enabled and markdown:
        logger.info("RC regex missed %d fields — running LLM fallback", len(missing_fields))
        try:
            llm_result = _llm_extract(markdown)
            for field in missing_fields:
                if llm_result.get(field) is not None:
                    extracted[field] = llm_result[field]
        except Exception as e:
            logger.error("RC LLM fallback error: %s", e)

    # Normalize name fields to Title Case so they match catalog storage
    # regardless of what case Docling OCR returns (HYUNDAI / hyundai / Hyundai).
    for title_field in ("make", "model", "variant"):
        if extracted.get(title_field):
            extracted[title_field] = extracted[title_field].strip().title()

    # Code fields stay UPPER — they are identifiers, not display names.
    for upper_field in ("registration_number", "chassis_vin", "engine_number"):
        if extracted.get(upper_field):
            extracted[upper_field] = extracted[upper_field].strip().upper()

    logger.info(
        "RC extraction complete — %d/%d fields populated",
        sum(1 for v in extracted.values() if v is not None),
        len(extracted),
    )
    return extracted
