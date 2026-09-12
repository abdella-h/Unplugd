from sqlalchemy import Column, DateTime, Integer, String, func

from app.core.database import Base


class Datacenter(Base):
    __tablename__ = "datacenters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    location = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
