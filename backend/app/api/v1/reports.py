from fastapi import APIRouter, HTTPException
from app.modules.reporting.exporters import export_report
from app.modules.reporting.service import get_report_by_id

router = APIRouter()


@router.get("/{report_id}/export")
def export(report_id: int, format: str = "pdf"):
    report = get_report_by_id(report_id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    file_path = export_report(report, format=format)

    return {
        "file_path": file_path
    }