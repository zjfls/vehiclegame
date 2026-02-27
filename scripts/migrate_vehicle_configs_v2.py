#!/usr/bin/env python3
"""Migrate legacy vehicle configs (v1) to the v2 schema.

We overwrite the original files by default, but keep a copy under:
  configs/vehicles/_backup_v1/<id>.json

Usage:
  python scripts/migrate_vehicle_configs_v2.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VEHICLES_DIR = PROJECT_ROOT / "configs" / "vehicles"
BACKUP_DIR = VEHICLES_DIR / "_backup_v1"

# Ensure project root is on sys.path when running as a script.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    from core.vehicle_config_loader import upgrade_v1_to_v2, normalize_v2

    if not VEHICLES_DIR.exists():
        print(f"Vehicle configs dir not found: {VEHICLES_DIR}")
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    migrated = 0
    skipped = 0
    for path in sorted(VEHICLES_DIR.glob("*.json")):
        vehicle_id = path.stem
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"[skip] {vehicle_id}: failed to parse json: {e}")
            skipped += 1
            continue

        if isinstance(raw, dict) and int(raw.get("version", 0) or 0) == 2:
            print(f"[ok]   {vehicle_id}: already v2")
            continue

        # Backup
        try:
            backup_path = BACKUP_DIR / path.name
            backup_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[warn] {vehicle_id}: failed to write backup: {e}")

        try:
            upgraded = upgrade_v1_to_v2(raw, vehicle_id=vehicle_id)
            upgraded = normalize_v2(upgraded)
            path.write_text(json.dumps(upgraded, indent=2, ensure_ascii=False), encoding="utf-8")
            migrated += 1
            print(f"[migr] {vehicle_id}: v1 -> v2")
        except Exception as e:
            print(f"[fail] {vehicle_id}: migration failed: {e}")
            skipped += 1

    print()
    print(f"Done. migrated={migrated}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
