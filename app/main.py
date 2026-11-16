"""Authenticated notes stored only in the deployment's Neon branch."""

import os
import secrets
import ssl
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated, ClassVar, Final
from uuid import UUID

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, status
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
PREVIEW_ID: Final = os.environ["PREVIEW_ID"]
COMMIT_SHA: Final = os.environ["COMMIT_SHA"]
PREVIEW_TOKEN: Final = os.environ["PREVIEW_TOKEN"]
CA_FILE: Final = ssl.get_default_verify_paths().openssl_cafile
if not Path(CA_FILE).is_file():
    raise FileNotFoundError(CA_FILE)


class NoteInput(BaseModel):
    """Bound input size and reject accidental extra fields."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, extra="forbid", str_strip_whitespace=True,
    )
    body: str = Field(min_length=1, max_length=1000)


class Note(BaseModel):
    """One persisted note."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    id: UUID
    body: str
    created_at: datetime


class Notes(BaseModel):
    """Include nonsecret identity so reviewers can compare two previews."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    preview: str
    commit: str
    notes: list[Note]


def authorize(authorization: Annotated[str, Header()] = "") -> None:
    """Require a preview-specific bearer token before accessing Postgres."""
    if not secrets.compare_digest(
        authorization.encode(), f"Bearer {PREVIEW_TOKEN}".encode(),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid preview token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@contextmanager
def database() -> Iterator[psycopg.Connection[Note]]:
    """Use libpq environment credentials and verified TLS, with bounded queries."""
    with psycopg.Connection[Note].connect(
        connect_timeout=10,
        options="-c statement_timeout=10000",
        sslmode="verify-full",
        sslrootcert=CA_FILE,
        row_factory=class_row(Note),
    ) as connection:
        # Serialize initial DDL across cold starts as well as this tiny workload.
        # The lock is transaction-scoped and is released on commit or rollback.
        _ = connection.execute("SELECT pg_advisory_xact_lock(684273918)")
        _ = connection.execute(
            """CREATE TABLE IF NOT EXISTS notes (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                body text NOT NULL CHECK (length(body) BETWEEN 1 AND 1000),
                created_at timestamptz NOT NULL DEFAULT now())""",
        )
        yield connection


@app.get("/api/notes", dependencies=[Depends(authorize)])
def list_notes() -> Notes:
    """Return the latest hundred notes from this PR only."""
    with database() as connection:
        rows = connection.execute(
            """SELECT id, body, created_at FROM notes
            ORDER BY created_at DESC, id DESC LIMIT 100""",
        ).fetchall()
    return Notes(preview=PREVIEW_ID, commit=COMMIT_SHA, notes=rows)


@app.post("/api/notes", status_code=201, dependencies=[Depends(authorize)])
def create_note(note: NoteInput) -> Note:
    """Insert one parameterized record; transaction commits before responding."""
    with database() as connection:
        result = connection.execute(
            "INSERT INTO notes (body) VALUES (%s) RETURNING id, body, created_at",
            (note.body,),
        ).fetchone()
    if result is None:
        raise HTTPException(status_code=500, detail="Insert returned no record")
    return result
