from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import ensure_device_scope, require_admin, require_scoped_user
from app.core.database import get_db
from app.models.datacenters import Datacenter
from app.models.devices import Device
from app.schemas.devices import (
    DeviceCreate,
    DeviceRead,
    DeviceStateUpdate,
    DeviceUpdate,
)

router = APIRouter()


def _ensure_unique_in_dc(
    db: Session,
    datacenter_id: int,
    *,
    name: str | None = None,
    serial_number: str | None = None,
    exclude_id: int | None = None,
):
    query = db.query(Device).filter(Device.datacenter_id == datacenter_id)
    if exclude_id is not None:
        query = query.filter(Device.id != exclude_id)

    if name is not None and query.filter(Device.name == name).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device name already exists in this datacenter",
        )
    if (
        serial_number is not None
        and query.filter(Device.serial_number == serial_number).first()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device serial number already exists in this datacenter",
        )


@router.post("/devices", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def create_device(
    device_in: DeviceCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    ensure_device_scope(admin, device_in.datacenter_id)

    dc = db.query(Datacenter).filter(Datacenter.id == device_in.datacenter_id).first()
    if not dc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Datacenter not found",
        )

    _ensure_unique_in_dc(
        db,
        device_in.datacenter_id,
        name=device_in.name,
        serial_number=device_in.serial_number,
    )

    device = Device(
        name=device_in.name,
        datacenter_id=device_in.datacenter_id,
        type=device_in.type,
        description=device_in.description,
        serial_number=device_in.serial_number,
        state=device_in.state,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("/devices", response_model=list[DeviceRead])
def list_devices(
    db: Session = Depends(get_db),
    user: dict = Depends(require_scoped_user),
):
    query = db.query(Device)
    if user["dc_id"] is not None:
        query = query.filter(Device.datacenter_id == user["dc_id"])
    return query.all()


def _get_scoped_device_or_404(db: Session, device_id: int, user: dict) -> Device:
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    ensure_device_scope(user, device.datacenter_id)
    return device


@router.get("/devices/{device_id}", response_model=DeviceRead)
def read_device(
    device_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_scoped_user),
):
    return _get_scoped_device_or_404(db, device_id, user)


@router.put("/devices/{device_id}/state", response_model=DeviceRead)
def report_device_state(
    device_id: int,
    state_in: DeviceStateUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_scoped_user),
):
    device = _get_scoped_device_or_404(db, device_id, user)

    setattr(device, "state", state_in.state)
    db.commit()
    db.refresh(device)
    return device


@router.patch("/devices/{device_id}", response_model=DeviceRead)
def update_device(
    device_id: int,
    device_in: DeviceUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    device = _get_scoped_device_or_404(db, device_id, admin)

    update_data = device_in.model_dump(exclude_unset=True)

    _ensure_unique_in_dc(
        db,
        device.datacenter_id,
        name=update_data.get("name"),
        serial_number=update_data.get("serial_number"),
        exclude_id=device_id,
    )

    for field in ("name", "type", "description", "serial_number", "state"):
        if field in update_data:
            setattr(device, field, update_data[field])

    db.commit()
    db.refresh(device)
    return device


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    device = _get_scoped_device_or_404(db, device_id, admin)

    db.delete(device)
    db.commit()
