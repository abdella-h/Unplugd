from sqlalchemy import Column, DateTime, Integer, String, func

from app.core.database import Base


class Alert(Base):
    """Dashboard record raised when a device enters warning/alert.

    Mirrors docs/glossary.md: Alert + Acknowledgment. Separate service DB,
    so no FK to devices — device_id/datacenter_id are plain copied values
    from the consumed event.
    """

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, nullable=False, index=True)
    datacenter_id = Column(Integer, nullable=False, index=True)
    old_state = Column(String(10), nullable=False)
    new_state = Column(String(10), nullable=False)
    reporter = Column(String(255), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String(255), nullable=True)
