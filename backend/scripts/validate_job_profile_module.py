from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.job_profile.cleaning import clean_job_record, parse_salary_range, project_source_record
from app.modules.job_profile.data_loader import discover_latest_source_file, load_source_records, resolve_input_path


REPO_ROOT = BACKEND_ROOT.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "official"



def main() -> None:
    resolved = resolve_input_path(None, RAW_DIR)
    assert resolved.exists(), "official source file was not resolved"
    assert discover_latest_source_file(RAW_DIR) == resolved

    source_format, records = load_source_records(resolved)
    assert source_format in {"csv", "xls", "xlsx"}
    assert records, "no records loaded from official source file"

    projected = project_source_record(records[0], source_row_number=1)
    cleaned, _ = clean_job_record(projected)
    assert cleaned.position_name
    assert cleaned.company_full_name
    assert cleaned.work_city
    assert isinstance(cleaned.job_tags, list)

    salary = parse_salary_range("20-30万/年")
    assert salary.salary_min_monthly == 16667
    assert salary.salary_max_monthly == 25000

    print("job profile module validation passed")
    print(f"resolved_input={resolved}")
    print(f"records_loaded={len(records)}")


if __name__ == "__main__":
    main()

