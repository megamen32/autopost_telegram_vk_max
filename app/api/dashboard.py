from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_container, get_session
from app.repositories.adapter_instances_repo import AdapterInstancesRepo
from app.repositories.dashboard_repo import DashboardRepo
from app.repositories.delivery_jobs_repo import DeliveryJobsRepo
from app.repositories.message_links_repo import MessageLinksRepo
from app.repositories.routes_repo import RoutesRepo
from app.utils.crypto import SecretBox

router = APIRouter(tags=["dashboard"])

WEBUI_DIR = Path(__file__).resolve().parent.parent / "webui"
INDEX_FILE = WEBUI_DIR / "index.html"


@router.get("/")
async def webui_index():
    return FileResponse(INDEX_FILE)


@router.get("/api/dashboard/overview")
async def dashboard_overview(container=Depends(get_container), session: AsyncSession = Depends(get_session)):
    repo = DashboardRepo(session)
    overview = await repo.get_overview()
    instances_repo = AdapterInstancesRepo(session, SecretBox(container.secrets_encryption_key))
    overview["adapter_instances"] = await instances_repo.list_all(include_secrets=False)
    overview["adapter_runtime_instances"] = container.adapter_registry.list_instances()
    overview["adapter_runtime_statuses"] = container.adapter_runtime_monitor.snapshot()
    overview["available_platforms"] = container.adapter_registry.list_platforms()
    return overview


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


@router.get("/api/dashboard/runtime-adapters")
async def dashboard_runtime_adapters(container=Depends(get_container)):
    return container.adapter_runtime_monitor.snapshot()


@router.get("/api/dashboard/diagnostics")
async def dashboard_diagnostics(container=Depends(get_container), session: AsyncSession = Depends(get_session)):
    return {
        "adapter_runtime_statuses": container.adapter_runtime_monitor.snapshot(),
        "routes": await RoutesRepo(session).list_all(),
    }
