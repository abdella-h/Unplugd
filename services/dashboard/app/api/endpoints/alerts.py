import logging
import os
from datetime import datetime, timezone
from typing import Callable

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import ensure_alert_scope, get_hub, require_admin
from app.core.broker import EventHub
from app.core.database import get_db
from app.models.alert import Alert
from app.schemas.alerts import AcknowledgeResponse, AlertRead

load_dotenv()

logger = logging.getLogger(__name__)

DEVICES_SERVICE_URL = os.getenv("DEVICES_SERVICE_URL", "http://localhost:8004")

router = APIRouter()


def _reset_device_to_ok(device_id: int, authorization: str) -> bool:
    """Best-effort synchronous reset of the device to ok in devices service."""
    try:
        resp = httpx.put(
            f"{DEVICES_SERVICE_URL}/devices/{device_id}/state",
            json={"state": "ok"},
            headers={"Authorization": authorization},
            timeout=5.0,
        )
        if resp.status_code >= 400:
            logger.warning(
                "Device reset failed for device %s: %s %s",
                device_id,
                resp.status_code,
                resp.text,
            )
            return False
        return True
    except Exception:  # noqa: BLE001 best-effort: ack must survive devices outage
        logger.warning("Device reset call failed for device %s", device_id)
        return False


def get_device_reset() -> Callable[[int, str], bool]:
    return _reset_device_to_ok


def _get_scoped_alert_or_404(db: Session, alert_id: int, admin: dict) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
        )
    ensure_alert_scope(admin, int(alert.datacenter_id))
    return alert


@router.get("/alerts", response_model=list[AlertRead])
def list_alerts(
    acknowledged: bool | None = None,
    datacenter_id: int | None = None,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    query = db.query(Alert)
    # ADR-0002 scoping: scoped admin sees only its DC; global may filter.
    if admin["dc_id"] is not None:
        query = query.filter(Alert.datacenter_id == admin["dc_id"])
    elif datacenter_id is not None:
        query = query.filter(Alert.datacenter_id == datacenter_id)
    if acknowledged is True:
        query = query.filter(Alert.acknowledged_at.is_not(None))
    elif acknowledged is False:
        query = query.filter(Alert.acknowledged_at.is_(None))
    return query.order_by(Alert.id.desc()).all()


@router.get("/alerts/{alert_id}", response_model=AlertRead)
def read_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    return _get_scoped_alert_or_404(db, alert_id, admin)


@router.post("/alerts/{alert_id}/acknowledge", response_model=AcknowledgeResponse)
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
    event_hub: EventHub = Depends(get_hub),
    reset_device: Callable[[int, str], bool] = Depends(get_device_reset),
    authorization: str = Header(),
):
    alert = _get_scoped_alert_or_404(db, alert_id, admin)

    # Best-effort reset: a failing devices service (or resetter) must never
    # turn a valid ack into a 500. Re-run on repeat acks too so the reported
    # status is always from a live attempt, never a stale default.
    try:
        device_reset_ok = reset_device(int(alert.device_id), authorization)
    except Exception:  # noqa: BLE001 best-effort: ack must survive devices outage
        logger.warning("Device reset call failed for device %s", alert.device_id)
        device_reset_ok = False

    if alert.acknowledged_at is None:
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = admin["username"]
        db.commit()
    db.refresh(alert)

    event_hub.broadcast(
        {
            "type": "alert_acknowledged_and_resolved",
            "alert_id": alert.id,
            "device_id": alert.device_id,
            "datacenter_id": alert.datacenter_id,
            "acknowledged_by": alert.acknowledged_by,
        }
    )

    payload = AcknowledgeResponse.model_validate(alert, from_attributes=True)
    payload.device_reset_ok = device_reset_ok
    return payload
