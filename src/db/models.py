from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4
from sqlalchemy import (
    String,
    DateTime,
    Enum as SQLEnum,
    Index,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class GraphStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Base(DeclarativeBase):
    pass


class Intent(Base):
    __tablename__ = "intents"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # sys_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    graphs: Mapped[list["Graph"]] = relationship(
        "Graph",
        back_populates="intent",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Intent(name={self.name})>"


class Graph(Base):
    __tablename__ = "graphs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    intent_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intents.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    graph_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        SQLEnum(GraphStatusEnum),
        default=GraphStatusEnum.PUBLISHED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    intent: Mapped["Intent"] = relationship("Intent", back_populates="graphs")
    audit_logs: Mapped[list["GraphAuditLog"]] = relationship(
        "GraphAuditLog",
        back_populates="graph",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_graphs_intent_id", "intent_id"),
        Index("idx_graphs_intent_version", "intent_id", "version", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Graph(intent_id={self.intent_id}, version={self.version}, status={self.status})>"


class GraphAuditLog(Base):
    __tablename__ = "graph_audit_log"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    graph_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graphs.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    status_before: Mapped[Optional[str]] = mapped_column(
        SQLEnum(GraphStatusEnum), nullable=True
    )
    status_after: Mapped[Optional[str]] = mapped_column(
        SQLEnum(GraphStatusEnum), nullable=True
    )
    performed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    graph: Mapped["Graph"] = relationship("Graph", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index("idx_graph_audit_log_graph_id", "graph_id"),
        Index("idx_graph_audit_log_performed_at", "performed_at"),
    )

    def __repr__(self) -> str:
        return f"<GraphAuditLog(graph_id={self.graph_id}, action={self.action})>"
