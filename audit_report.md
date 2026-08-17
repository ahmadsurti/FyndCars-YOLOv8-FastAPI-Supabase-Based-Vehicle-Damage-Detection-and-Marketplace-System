# fynd(cars) — Fourth-Pass Ponytail Audit (Post-Cleanup State)

> Applied 2026-08-17. Every cut below is already executed and verified: 22/22 tests pass,
> all routers mount, CV + policy agent load. Backup of the pre-cleanup tree:
> `../fynd(cars)-main-ZCODE.backup-2026-08-17.zip`

---

## ✂️ WHAT WAS CUT AND WHY

| Cut | Lines | Reason |
|---|---|---|
| `supabase/migrations/000_full_schema.sql` | -782 | 100% duplicate of migrations 001–005 (same tables, policies, indexes). 001–005 additionally create the storage buckets 000 lacked. Versioned migrations are the single source of truth now. |
| `backend/agentic/vision/` (inpaint package) | -136 | `make_after_preview()` had zero callers. Phase-3 feature; re-add from backup when a route actually wires it. |
| `backend/agentic/explainer.py` | -56 | `build_customer_explanation` / `format_kb_insights` had zero callers; `/assess` already returns `expert_commentary` covering the same UX ground. |
| `backend/agentic/trace.py` | -57 | `build_decision_trace()` had zero callers; `/assess` already returns `decision_trace`. |
| `utils.enhance_image()` | -17 | Zero callers. |
| `CarDamageDetector.annotate_image()` | -14 | Zero callers; frontend draws bboxes client-side from the bbox JSON. |
| `Decision.kb_evidence`, `DamageSignal.notes` | -4 | Never set, never read. |
| `_utils.as_float`, `decision_agent._sig_get` | -15 | Dead after the above; `_sig_get` duplicated `_utils.pick`. |
| Notebook embedded outputs | -546 | 3.68 MB of training plots/logs wrapped around 228 chars of code. Code cells kept. |
| `requirements-dev.txt`: httpx line | -1 | Already in `requirements.txt`. |
| `__pycache__/`, `.pytest_cache/` | — | Build junk on disk. |

## 🔀 DEDUPLICATION (the big one)

`POST /listings/{id}/images` re-implemented the entire `/assess` pipeline inline (~75 lines)
and imported `api.py` from inside a route function to dodge a circular import. Both smells are gone:

- **New `backend/assessment.py`** — the single pipeline: lazy detector/agent singletons +
  `run_assessment(image_bytes) -> dict` (detect → normalize → policy decision → stats → commentary).
- `api.py /assess` is now validation + one call. 297 → 192 lines.
- `routes/listings.py` image upload is now fetch-bytes + one call. 359 → 262 lines.
- Side effect: both paths now return the **same damage shape** (`damage_type`-keyed) —
  previously `/assess` returned `damage_type` while the listing path stored `type`-keyed rows.

## 🐛 LOGIC BUGS FIXED

1. **`calculate_damage_stats` key mismatch** — read `d.get("type")` but was fed
   `damage_type`-keyed dicts → `damage_types` and `most_common_damage` were always
   `"unknown"`. Now reads `damage_type` (with `type` tolerated).
2. **`MODEL_PATH` env var documented but never read** — `.env.example` advertised it;
   the detector hardcoded `models/best.pt`. `assessment.py` now wires `os.getenv("MODEL_PATH")`.
3. **LLM prompt dropped the damage type** on the unified pipeline shape
   (`det.get("type")` → `None`); now falls back to `damage_type`.
4. **DB-insert collision risk removed** — the listing path now inserts only
   `ASSESSMENT_DB_FIELDS` (damage_stats / expert_commentary are response-only; the
   `assessments` table has no such columns — previously would have been a silent 400
   from PostgREST once unified naively; guarded explicitly).

## 🏷️ NEW PONYTAIL DEBT (deliberate ceilings)

- `routes/admin.py:get_platform_stats` — `ponytail: naive full-scan aggregation, upgrade to SQL RPC (GROUP BY) if listings > ~500`.

## 📋 REMAINING OPEN QUESTIONS (unchanged, pre-frontend)

- Q2 from the prior audit is **resolved**: `POST /listings/{id}/images` exists and runs the
  full auto-assess flow (URL or `bucket/path` storage fetch → assess → DB row → ESCALATE flips status).
- Before/after repair preview (`make_after_preview`) is deleted, not wired — decide at Phase 3
  whether the frontend needs it; restore from backup then.
- `middleware/auth.py` dev fallback (unverified JWT when `SUPABASE_JWT_SECRET` unset) is
  dev-only; production MUST set `SUPABASE_JWT_SECRET`.

## 📊 NET

```
Python:        ~2,290 → ~2,050 lines (-240, one new 120-line module replacing ~200 duplicated)
SQL:           1,882 → 1,100 lines (-782)
Notebook:      1,144 → 598 lines (-546)
Docs:          audit_report regenerated to current state
Total repo:    ~6,700 → ~4,700 lines (-~2,000, -30%)
Dependencies:  unchanged (0 removed from runtime — the dead ones were already gone in pass 3)
Tests:         22/22 passing before and after.
```

Lean enough to ship the next phase. Remaining known ceiling: admin stats aggregation (tagged above).
