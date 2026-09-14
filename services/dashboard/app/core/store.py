import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.events import DeviceStateChanged
from app.models.alert import Alert

logger = logging.getLogger(__name__)

ALERT_STATES = ("warning", "alert")


def persist_state_changed_event(db: Session, event: dict) -> Alert | None:
    """Validate a broker event and persist an Alert for warning/alert.

    Returns the created Alert, or None when the event is not alert-worthy
    (e.g. recovery to ok) or fails validation. Never raises on bad input —
    the consumer drops such messages after logging.
    """
    try:
        parsed = DeviceStateChanged.model_validate(event)
    except ValidationError:
        logger.warning("Discarding invalid device event: %r", event)
        return None
    if parsed.new_state not in ALERT_STATES:
        return None
    alert = Alert(
        device_id=parsed.device_id,
        datacenter_id=parsed.datacenter_id,
        old_state=parsed.old_state,
        new_state=parsed.new_state,
        reporter=parsed.reporter,
        occurred_at=parsed.occurred_at,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
