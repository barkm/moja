from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import func
from sqlmodel import Session, select

import src.db.models as models


def session_is_alive(session: Session) -> bool:
    try:
        session.exec(select(1)).first()
        return True
    except Exception:
        return False


def get_device(
    session: Session, name: str, role: models.Role | None = None
) -> models.Device | None:
    statement = select(models.Device).where(models.Device.name == name)
    if role:
        statement = statement.where(models.Device.allowed_roles.any(role))  # type: ignore
    return session.exec(statement).first()


def get_devices(session: Session, role: models.Role) -> list[models.Device]:
    statement = select(models.Device).where(models.Device.allowed_roles.any(role))  # type: ignore
    return list(session.exec(statement).all())


def add_device(session: Session, name: str) -> models.Device:
    device = models.Device(name=name, allowed_roles=[models.Role.ADMIN])
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def set_device_roles(session: Session, device: models.Device, roles: list[models.Role]):
    device.allowed_roles = roles
    session.add(device)
    session.commit()
    session.refresh(device)


def register_device(session: Session, device: models.Device, url: str):
    statement = (
        select(models.Registration)
        .where(models.Registration.device_id == device.id)
        .order_by(models.Registration.created_at.desc())  # type: ignore
        .limit(1)
    )
    register = session.exec(statement).first()
    if register:
        register.url = url
        register.created_at = datetime.now(timezone.utc)
    else:
        register = models.Registration(device_id=device.id, url=url)
    session.add(register)
    session.commit()
    session.refresh(register)


def get_url(session: Session, name: str) -> str | None:
    statement = (
        select(models.Registration)
        .join(models.Device)
        .where(models.Device.name == name)
        .order_by(models.Registration.created_at.desc())  # type: ignore
        .limit(1)
    )
    register = session.exec(statement).first()
    return register.url if register else None


def get_recordings(
    session: Session,
    device_name: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[models.Recording]:
    statement = (
        select(models.Recording)
        .join(models.Device)
        .where(models.Device.name == device_name)
    )
    if start:
        statement = statement.where(models.Recording.created_at >= start)
    if end:
        statement = statement.where(models.Recording.created_at <= end)
    return list(session.exec(statement).all())


def get_sensors(
    session: Session,
    role: models.Role,
    device_name: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[models.Sensor]:
    statement = (
        select(models.Sensor)
        .join(models.Device)
        .order_by(models.Sensor.created_at.desc())  # type: ignore
        .where(models.Device.name == device_name)
        .where(models.Sensor.temperature.is_(None) | (models.Sensor.temperature > -30))
        .where(models.Device.allowed_roles.any(role))  # type: ignore
    )
    if start:
        statement = statement.where(models.Sensor.created_at >= start)
    if end:
        statement = statement.where(models.Sensor.created_at <= end)
    return list(session.exec(statement).all())


def add_sensor(
    session: Session,
    device: models.Device,
    temperature: float | None,
    humidity: float | None,
    cpu_temperature: float | None,
) -> models.Sensor:
    sensor = models.Sensor(
        device_id=device.id,
        temperature=temperature,
        humidity=humidity,
        cpu_temperature=cpu_temperature,
    )
    session.add(sensor)
    session.commit()
    session.refresh(sensor)
    return sensor


def get_user_by_uid(session: Session, uid: str) -> models.User | None:
    statement = select(models.User).where(models.User.uid == uid)
    return session.exec(statement).first()


def get_user_by_id(session: Session, id: UUID) -> models.User | None:
    statement = select(models.User).where(models.User.id == id)
    return session.exec(statement).first()


def add_user(session: Session, user: models.User) -> models.User:
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_users(session: Session) -> list[models.User]:
    statement = select(models.User)
    return list(session.exec(statement).all())


def get_locations(session: Session) -> list[models.Location]:
    return list(session.exec(select(models.Location)).all())


def get_current_location(
    session: Session, device: models.Device
) -> models.Location | None:
    statement = (
        select(models.Location)
        .join(models.DeviceLocation)
        .where(models.DeviceLocation.device_id == device.id)
        .order_by(models.DeviceLocation.assigned_at.desc())  # type: ignore
        .limit(1)
    )
    return session.exec(statement).first()


def get_current_device_for_location(
    session: Session, role: models.Role, location_name: str
) -> models.Device | None:
    latest_per_device_sq = (
        select(
            models.DeviceLocation.device_id,
            func.max(models.DeviceLocation.assigned_at).label("max_assigned_at"),
        )
        .group_by(models.DeviceLocation.device_id)
        .subquery()
    )
    statement = (
        select(models.Device)
        .join(
            latest_per_device_sq, latest_per_device_sq.c.device_id == models.Device.id
        )
        .join(
            models.DeviceLocation,
            (models.DeviceLocation.device_id == models.Device.id)
            & (
                models.DeviceLocation.assigned_at
                == latest_per_device_sq.c.max_assigned_at
            ),
        )
        .join(models.Location, models.Location.id == models.DeviceLocation.location_id)
        .where(models.Location.name == location_name)
        .where(models.Device.allowed_roles.any(role))  # type: ignore
    )
    return session.exec(statement).first()


def get_sensors_by_location(
    session: Session,
    role: models.Role,
    location_name: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[models.Sensor]:
    latest_assignment_sq = (
        select(func.max(models.DeviceLocation.assigned_at))
        .where(models.DeviceLocation.device_id == models.Sensor.device_id)
        .where(models.DeviceLocation.assigned_at <= models.Sensor.created_at)
        .correlate(models.Sensor)
        .scalar_subquery()
    )
    statement = (
        select(models.Sensor)
        .join(models.Device, models.Device.id == models.Sensor.device_id)
        .join(
            models.DeviceLocation,
            (models.DeviceLocation.device_id == models.Sensor.device_id)
            & (models.DeviceLocation.assigned_at == latest_assignment_sq),
        )
        .join(models.Location, models.Location.id == models.DeviceLocation.location_id)
        .where(models.Location.name == location_name)
        .where(models.Device.allowed_roles.any(role))  # type: ignore
        .where(models.Sensor.temperature.is_(None) | (models.Sensor.temperature > -30))
        .order_by(models.Sensor.created_at.desc())  # type: ignore
    )
    if start:
        statement = statement.where(models.Sensor.created_at >= start)
    if end:
        statement = statement.where(models.Sensor.created_at <= end)
    return list(session.exec(statement).all())


def get_recordings_by_location(
    session: Session,
    role: models.Role,
    location_name: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[models.Recording]:
    latest_assignment_sq = (
        select(func.max(models.DeviceLocation.assigned_at))
        .where(models.DeviceLocation.device_id == models.Recording.device_id)
        .where(models.DeviceLocation.assigned_at <= models.Recording.created_at)
        .correlate(models.Recording)
        .scalar_subquery()
    )
    statement = (
        select(models.Recording)
        .join(models.Device, models.Device.id == models.Recording.device_id)
        .join(
            models.DeviceLocation,
            (models.DeviceLocation.device_id == models.Recording.device_id)
            & (models.DeviceLocation.assigned_at == latest_assignment_sq),
        )
        .join(models.Location, models.Location.id == models.DeviceLocation.location_id)
        .where(models.Location.name == location_name)
        .where(models.Device.allowed_roles.any(role))  # type: ignore
        .order_by(models.Recording.created_at.desc())  # type: ignore
    )
    if start:
        statement = statement.where(models.Recording.created_at >= start)
    if end:
        statement = statement.where(models.Recording.created_at <= end)
    return list(session.exec(statement).all())
