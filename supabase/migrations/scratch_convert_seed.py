"""Convert car_catalogue_1_20_variant_seed.json → migration 008 SQL INSERT."""
import json
from pathlib import Path

SRC = Path("car_catalogue_1_20_variant_seed.json")
OUT = Path("supabase/migrations/008_vehicle_catalog_seed.sql")

data = json.loads(SRC.read_text(encoding="utf-8"))

def pg_array(lst):
    """Convert Python list of strings → Postgres array literal: '{\"a\",\"b\"}'"""
    if not lst:
        return "'{}'"
    escaped = [s.replace("'", "''").replace('"', '\\"') for s in lst]
    inner = ",".join(f'"{v}"' for v in escaped)
    return f"'{{{inner}}}'"

header = """\
-- ============================================================
-- Migration 008: vehicle_catalog seed — batch 1 (284 variants)
-- Researcher-verified data: Maruti Suzuki, Hyundai, Tata, Honda,
-- Kia, Toyota, MG, Mahindra, Volkswagen, Skoda, Jeep, Renault
-- (and more). Progressive batches continue as 009, 010, ...
--
-- ON CONFLICT DO NOTHING: safe to re-run or apply on top of 007.
-- make + model in Title Case — rc_extractor normalizes OCR output
-- to .title() before lookup.
-- ============================================================

insert into public.vehicle_catalog
  (make, model, variant, year_start, year_end,
   body_type, fuel_type, transmission, features, colors)
values
"""

rows = []
for item in data:
    make     = item["make"].replace("'", "''")
    model    = item["model"].replace("'", "''")
    variant  = item["variant"].replace("'", "''")
    ys       = item["year_start"]
    ye       = item["year_end"]
    body     = item["body_type"]
    fuel     = item["fuel_type"]
    trans    = item["transmission"]
    features = pg_array(item.get("features", []))
    colors   = pg_array(item.get("colors", []))

    rows.append(
        f"  ('{make}', '{model}', '{variant}', {ys}, {ye}, "
        f"'{body}', '{fuel}', '{trans}', {features}, {colors})"
    )

footer = "\non conflict (make, model, variant, year_start, year_end) do nothing;\n"

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(header + ",\n".join(rows) + footer, encoding="utf-8")

print(f"Written {len(rows)} rows to {OUT}")
print(f"File size: {OUT.stat().st_size:,} bytes")
