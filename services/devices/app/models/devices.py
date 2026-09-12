from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("datacenter_id", "name", name="uq_devices_dc_name"),
        UniqueConstraint(
            "datacenter_id", "serial_number", name="uq_devices_dc_serial"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    datacenter_id = Column(
        Integer, ForeignKey("datacenters.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    serial_number = Column(String(255), nullable=True)
    state = Column(String(10), nullable=False, default="ok")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
