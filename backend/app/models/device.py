"""PRD §9 'Devices & users'."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, LargeBinary, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Device(Base):
    __tablename__ = "devices"

    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    # Salted hash of ANDROID_ID; no raw identifiers -- PRD NFR-PR4.
    device_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    model: Mapped[str | None] = mapped_column(Text)
    android_version: Mapped[str | None] = mapped_column(Text)
    app_version: Mapped[str | None] = mapped_column(Text)
    locale: Mapped[str] = mapped_column(Text, nullable=False, default="en-IN")
    msisdn_hash: Mapped[str | None] = mapped_column(Text)
    registered_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    last_seen_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    consent_flags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    emergency_contacts: Mapped[list["EmergencyContact"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Envelope-encrypted at rest -- PRD NFR-S2. Encryption happens in the
    # service layer; this column only ever sees ciphertext.
    msisdn_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    relation: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)

    device: Mapped[Device] = relationship(back_populates="emergency_contacts")
