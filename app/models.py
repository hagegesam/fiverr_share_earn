"""SQLAlchemy models for Link and Click tables."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Link(Base):
    __tablename__ = "links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    short_code = Column(String(6), unique=True, nullable=False, index=True)
    target_url = Column(Text, unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    clicks = relationship("Click", back_populates="link", cascade="all, delete-orphan")


class Click(Base):
    __tablename__ = "clicks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link_id = Column(UUID(as_uuid=True), ForeignKey("links.id"), nullable=False)
    clicked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    link = relationship("Link", back_populates="clicks")


# Index on clicks.link_id for fast aggregation queries
Index("idx_clicks_link_id", Click.link_id)
