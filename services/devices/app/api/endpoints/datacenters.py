from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_global_admin
from app.core.database import get_db
from app.models.datacenters import Datacenter
from app.models.devices import Device
from app.schemas.datacenters import DatacenterCreate, DatacenterRead, DatacenterUpdate

router = APIRouter()


@router.post(
    "/datacenters",
    response_model=DatacenterRead,
    status_code=status.HTTP_201_CREATED,
)
def create_datacenter(
    dc_in: DatacenterCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_global_admin),
):
    existing = db.query(Datacenter).filter(Datacenter.name == dc_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Datacenter name already exists",
        )

    dc = Datacenter(name=dc_in.name, location=dc_in.location)
    db.add(dc)
    db.commit()
    db.refresh(dc)
    return dc


@router.get(
    "/datacenters",
    response_model=list[DatacenterRead],
)
def list_datacenters(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_global_admin),
):
    return db.query(Datacenter).all()


@router.get(
    "/datacenters/{datacenter_id}",
    response_model=DatacenterRead,
)
def read_datacenter(
    datacenter_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_global_admin),
):
    dc = db.query(Datacenter).filter(Datacenter.id == datacenter_id).first()
    if not dc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Datacenter not found",
        )
    return dc


@router.patch(
    "/datacenters/{datacenter_id}",
    response_model=DatacenterRead,
)
def update_datacenter(
    datacenter_id: int,
    dc_in: DatacenterUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_global_admin),
):
    dc = db.query(Datacenter).filter(Datacenter.id == datacenter_id).first()
    if not dc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Datacenter not found",
        )

    update_data = dc_in.model_dump(exclude_unset=True)

    if "name" in update_data:
        existing = (
            db.query(Datacenter)
            .filter(
                Datacenter.name == update_data["name"],
                Datacenter.id != datacenter_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Datacenter name already exists",
            )
        dc.name = update_data["name"]

    if "location" in update_data:
        dc.location = update_data["location"]

    db.commit()
    db.refresh(dc)
    return dc


@router.delete(
    "/datacenters/{datacenter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_datacenter(
    datacenter_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_global_admin),
):
    dc = db.query(Datacenter).filter(Datacenter.id == datacenter_id).first()
    if not dc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Datacenter not found",
        )

    device_count = (
        db.query(Device).filter(Device.datacenter_id == datacenter_id).count()
    )
    if device_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete datacenter with existing devices",
        )

    db.delete(dc)
    db.commit()
