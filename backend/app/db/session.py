from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from fastapi import Request
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


def build_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        raw_path = database_url.split("///", maxsplit=1)[-1]
        if raw_path and raw_path != ":memory:":
            Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            future=True,
        )
    return create_engine(database_url, future=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def _has_incompatible_schema(engine: Engine) -> bool:
    inspector = inspect(engine)
    for table in Base.metadata.tables.values():
        if not inspector.has_table(table.name):
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
        model_columns = {column.name for column in table.columns}
        if not model_columns.issubset(existing_columns):
            return True
    return False


def _drop_current_schema(engine: Engine) -> None:
    table_names = list(Base.metadata.tables)
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        for table_name in reversed(table_names):
            connection.exec_driver_sql(f'DROP TABLE IF EXISTS "{table_name}"')
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def init_db(engine: Engine) -> None:
    from app import models  # noqa: F401

    if _has_incompatible_schema(engine):
        _drop_current_schema(engine)
    Base.metadata.create_all(bind=engine)


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.SessionLocal
    db: Session = session_factory()
    try:
        yield db
    finally:
        db.close()
