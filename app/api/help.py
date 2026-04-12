from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pathlib import Path

from app.dependencies import get_container

router = APIRouter(tags=["help"])


@router.get('/api/help/entries')
async def list_help_entries(container=Depends(get_container)):
    entries = [entry.to_dict() for entry in container.definition_registry.list_help_entries()]
    return {"entries": entries}


@router.get('/faq.html', response_class=HTMLResponse)
async def faq_page():
    path = Path(__file__).resolve().parent.parent / 'webui' / 'faq.html'
    return HTMLResponse(path.read_text(encoding='utf-8'))
