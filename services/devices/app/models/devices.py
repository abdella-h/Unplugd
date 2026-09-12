from sqlalchemy import Column, ForeignKey, Integer

from app.core.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    datacenter_id = Column(
        Integer, ForeignKey("datacenters.id", ondelete="RESTRICT"), nullable=False, index=True
    )
