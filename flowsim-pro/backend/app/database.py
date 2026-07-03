"""SQLite database models and session management."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./flowsim_pro.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class SimulationCase(Base):
    __tablename__ = "simulation_cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    case_type = Column(String(64), default="well_tubing_flowline")
    inputs_json = Column(Text, nullable=False)
    outputs_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def inputs(self) -> dict:
        return json.loads(self.inputs_json)

    @inputs.setter
    def inputs(self, value: dict) -> None:
        self.inputs_json = json.dumps(value)

    @property
    def outputs(self) -> dict | None:
        return json.loads(self.outputs_json) if self.outputs_json else None

    @outputs.setter
    def outputs(self, value: dict | None) -> None:
        self.outputs_json = json.dumps(value) if value else None


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
