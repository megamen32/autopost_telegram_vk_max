from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_container, get_session
from app.domain.enums import Platform
from app.repositories.dashboard_repo import DashboardRepo
from app.repositories.delivery_jobs_repo import DeliveryJobsRepo
from app.repositories.message_links_repo import MessageLinksRepo
from app.repositories.routes_repo import RoutesRepo
from app.repositories.rules_repo import RulesRepo
from app.services.platform_settings_service import build_platform_status, load_platform_settings_from_db

router = APIRouter(tags=["dashboard"])

WEBUI_DIR = Path(__file__).resolve().parent.parent / "webui"
INDEX_FILE = WEBUI_DIR / "index.html"


@router.get("/")
async def webui_index():
    return FileResponse(INDEX_FILE)


@router.get("/api/dashboard/overview")
async def dashboard_overview(container=Depends(get_container), session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    repo = DashboardRepo(session)
    overview = await repo.get_overview()
    effective = await load_platform_settings_from_db(container.session_factory, settings.secrets_encryption_key)
    overview["platform_status"] = build_platform_status(effective)
    overview["available_platforms"] = container.adapter_registry.list_platforms()
    return overview


@router.get("/api/dashboard/rules")
async def dashboard_rules(session: AsyncSession = Depends(get_session)):
    return await RulesRepo(session).list_all()


@router.get("/api/dashboard/routes")
async def dashboard_routes(session: AsyncSession = Depends(get_session)):
    return await RoutesRepo(session).list_all()


@router.get("/api/dashboard/jobs")
async def dashboard_jobs(limit: int = Query(default=100, ge=1, le=500), session: AsyncSession = Depends(get_session)):
    jobs = await DeliveryJobsRepo(session).list_all()
    return list(reversed(jobs))[:limit]


@router.get("/api/dashboard/message-links")
async def dashboard_message_links(limit: int = Query(default=100, ge=1, le=500), session: AsyncSession = Depends(get_session)):
    links = await MessageLinksRepo(session).list_all()
    return list(reversed(links))[:limit]


@router.post("/api/dashboard/jobs/{job_id}/requeue")
async def dashboard_requeue_job(job_id: int, session: AsyncSession = Depends(get_session)):
    repo = DeliveryJobsRepo(session)
    ok = await repo.requeue_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    await session.commit()
    return {"ok": True}


@router.post("/api/dashboard/platforms/{platform}/toggle-updates")
async def dashboard_toggle_platform_updates(platform: Platform, enabled: bool):
    raise HTTPException(
        status_code=501,
        detail=(
            f"Runtime editing of platform adapter settings for {platform.value} is not implemented yet. "
            "Runtime adapter reload is not implemented yet. Platform settings are stored in DB and applied on restart."
        ),
    )
