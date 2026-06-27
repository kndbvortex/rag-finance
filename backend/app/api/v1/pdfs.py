from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/v1/pdfs", tags=["pdfs"])

_DATA_DIR = Path("data/raw_pdfs")


@router.get("/{url_hash}")
async def get_pdf(url_hash: str) -> FileResponse:
    if not url_hash.isalnum() or len(url_hash) != 64:
        raise HTTPException(status_code=400, detail="Invalid hash")

    matches = list(_DATA_DIR.glob(f"*/{url_hash}.pdf"))
    if not matches:
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        matches[0],
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )
