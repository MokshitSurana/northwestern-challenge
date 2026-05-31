# Archived scripts

Earlier scripts kept for transparency / git history. Not part of any active
skill or test path. Safe to delete; left in place so reviewers can see the
discovery process behind the current pipeline.

| File | Why archived |
|------|--------------|
| `02_revolving_door_scan.py`  | Superseded by `scripts/03_agency_concentration.py` (the `scan` skill implementation). The original broad-candidate scan was a stepping stone to the agency-concentration analysis; output is no longer used. |
| `_rebuild_lobbyists.py`      | One-shot helper used during the House parser fix in May 2026. Replaced by `scripts/01c_rebuild_house_all.py`. |

Diagnostic scripts (one-shot data-quality probes used while building the
test suite) live alongside the active scripts under `scripts/_diagnose_*.py`
and remain runnable.
