import os
from pathlib import Path

from app.modules.job_profile.data_loader import (
    detect_source_format,
    discover_latest_source_file,
    load_source_records,
    resolve_input_path,
)



def test_detect_source_format_supports_xls_and_xlsx():
    assert detect_source_format("official_jobs.xls") == "xls"
    assert detect_source_format("official_jobs.xlsx") == "xlsx"
    assert detect_source_format("official_jobs.csv") == "csv"



def test_discover_latest_source_file_prefers_newest_supported_file(tmp_path: Path):
    older = tmp_path / "official_older.csv"
    older.write_text("职位名称,公司全称\n数据分析师,甲公司\n", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))

    newer = tmp_path / "official_newer.xlsx"
    newer.write_text("placeholder", encoding="utf-8")
    os.utime(newer, (1_700_000_100, 1_700_000_100))

    assert discover_latest_source_file(tmp_path) == newer.resolve()



def test_resolve_input_path_defaults_to_raw_dir(tmp_path: Path):
    source = tmp_path / "official_jobs.csv"
    source.write_text("职位名称,公司全称\nPython开发工程师,乙公司\n", encoding="utf-8")

    assert resolve_input_path(None, tmp_path) == source.resolve()



def test_load_source_records_reads_csv(tmp_path: Path):
    source = tmp_path / "official_jobs.csv"
    source.write_text(
        "职位名称,工作地址,薪资范围,公司全称\nPython开发工程师,上海市浦东新区,15K-25K,上海星云数据科技有限公司\n",
        encoding="utf-8",
    )

    source_format, records = load_source_records(source)

    assert source_format == "csv"
    assert len(records) == 1
    assert records[0]["职位名称"] == "Python开发工程师"
