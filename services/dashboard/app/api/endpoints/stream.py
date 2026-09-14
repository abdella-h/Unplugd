import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_hub, require_admin
from app.core.broker import EventHub

router = APIRouter()


def _event_visible_to_admin(event: dict, admin: dict) -> bool:
    """ADR-0002: scoped admin sees only its datacenter; global sees all."""
    if admin["dc_id"] is None:
        return True
    return event.get("datacenter_id") == admin["dc_id"]


@router.get("/stream")
async def stream(
    admin: dict = Depends(require_admin),
    event_hub: EventHub = Depends(get_hub),
) -> StreamingResponse:
    queue = event_hub.subscribe()

    async def events() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    if not _event_visible_to_admin(event, admin):
                        continue
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            event_hub.unsubscribe(queue)

    return StreamingResponse(events(), media_type="text/event-stream")
