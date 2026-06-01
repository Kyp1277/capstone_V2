import logging
import os
from tempfile import NamedTemporaryFile
from typing import Optional

from modules import config as _config  # noqa: F401
from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile

from modules import analysis_service, auth_service, database
from modules.config import MAX_UPLOAD_SIZE
from modules.rate_limit import enforce_rate_limit


logger = logging.getLogger("jobfit.routes.analyses")
router = APIRouter(prefix="/api/analyses")


@router.get("")
def list_analyses(authorization: Optional[str] = Header(None)):
    user = auth_service.require_authenticated_user(authorization)

    try:
        return {"analyses": database.list_user_analyses(user["id"])}
    except Exception as error:
        logger.exception("Failed to list analyses.")
        raise HTTPException(status_code=500, detail="Riwayat analisis gagal dimuat.") from error


@router.get("/titles")
def autocomplete_titles(q: Optional[str] = ""):
    from modules import jobs_service
    jobs = jobs_service.load_jobs_once()
    query = (q or "").strip().lower()

    if not query:
        # Ambil list judul pekerjaan unik secara default
        titles = sorted(list(set(str(j.get("title", "")) for j in jobs if j.get("title"))))[:20]
        return {"titles": titles}

    matching = set()
    for j in jobs:
        title = str(j.get("title", ""))
        if title and query in title.lower():
            matching.add(title)
            if len(matching) >= 20:
                break
    return {"titles": sorted(list(matching))}


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str, authorization: Optional[str] = Header(None)):
    user = auth_service.require_authenticated_user(authorization)

    try:
        analysis = database.get_user_analysis(user["id"], analysis_id)
    except Exception as error:
        logger.exception("Failed to load analysis detail.")
        raise HTTPException(status_code=500, detail="Detail analisis gagal dimuat.") from error

    if not analysis:
        raise HTTPException(status_code=404, detail="Hasil analisis tidak ditemukan.")

    return analysis


@router.post("")
async def create_analysis(
    cv: UploadFile = File(...),
    targetRole: Optional[str] = Form(None),
    analysisMode: str = Form("targeted"),
    authorization: Optional[str] = Header(None),
    request: Request = None,
):
    mode = analysisMode.strip().lower()
    token = auth_service.bearer_token(authorization)
    enforce_rate_limit("analysis", rate_limit_identifier(request, token), limit=8, window_seconds=10 * 60)
    if mode not in {"targeted", "auto"}:
        raise HTTPException(status_code=400, detail="Mode analisis tidak valid.")

    target_role = (targetRole or "").strip()

    if mode == "targeted" and len(target_role) < 3:
        raise HTTPException(status_code=400, detail="Target pekerjaan wajib diisi minimal 3 karakter.")

    filename = cv.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File harus berformat PDF.")

    user = auth_service.optional_authenticated_user(authorization)
    content = await read_upload_content(cv)
    if not content:
        raise HTTPException(status_code=400, detail="File CV kosong.")

    temp_path: Optional[str] = None

    try:
        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        result = analysis_service.analyze_cv_file(temp_path, target_role, mode)
        cv_text = result.pop("_cvText", "")

        if user:
            try:
                result = database.save_analysis(user["id"], result, cv_text)
            except Exception:
                logger.exception("Failed to persist analysis.")

        return result
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("CV analysis failed.")
        raise HTTPException(status_code=500, detail="Analisis gagal diproses. Coba beberapa saat lagi.") from error
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def rate_limit_identifier(request: Optional[Request], token: str):
    if token:
        return f"token:{token}"

    forwarded_for = ""
    if request:
        forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    client_host = request.client.host if request and request.client else ""
    return f"ip:{forwarded_for or client_host or 'anonymous'}"


async def read_upload_content(cv: UploadFile):
    content = bytearray()
    chunk_size = 1024 * 1024

    while True:
        legacy_full_read = False
        try:
            chunk = await cv.read(chunk_size)
        except TypeError:
            chunk = await cv.read()
            legacy_full_read = True
        if not chunk:
            break

        content.extend(chunk)
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Ukuran file maksimal 5 MB.")

        if legacy_full_read or len(chunk) < chunk_size:
            break

    return bytes(content)
