"""
app/database/db.py
───────────────────
SQLite setup, session management, and school seeding from final_dataset.csv.
"""

import sys
import logging
from pathlib import Path
from contextlib import contextmanager

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import DATABASE_URL, FINAL_DATASET
from app.database.models import Base, School

log = logging.getLogger(__name__)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite + FastAPI
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables. Safe to call multiple times."""
    Base.metadata.create_all(bind=engine)
    log.info("Database tables initialised")


@contextmanager
def get_db_context():
    """Use in non-FastAPI code (scripts, tests)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# SEED SCHOOLS FROM CSV
# ─────────────────────────────────────────────────────────────

SCHOOL_COLUMNS = [
    "pseudocode", "school_level", "total_students", "total_boys", "total_girls",
    "total_tch", "regular", "contract", "classrooms_total", "classrooms_pucca",
    "classrooms_good", "has_girls_toilet", "has_boys_toilet", "has_ramp",
    "has_library", "has_playground", "has_electricity", "has_internet",
    "has_handwash", "has_boundary_wall", "has_comp_lab", "ptr",
    "infrastructure_gap", "risk_score", "risk_level",
]


def seed_schools(force: bool = False) -> int:
    """
    Load schools from final_dataset.csv into the DB.
    Skips if already seeded (unless force=True).
    Returns number of schools inserted.
    """
    if not FINAL_DATASET.exists():
        raise FileNotFoundError(
            f"Run pipeline first: python app/data/pipeline.py"
        )

    with get_db_context() as db:
        existing = db.query(School).count()
        if existing > 0 and not force:
            log.info(f"Schools already seeded ({existing} records). Skipping.")
            return 0

        if force:
            db.query(School).delete()
            log.info("Cleared existing school records")

        df = pd.read_csv(FINAL_DATASET)

        # Keep only columns that exist in both CSV and School model
        available = [c for c in SCHOOL_COLUMNS if c in df.columns]
        df = df[available].copy()

        # Ensure pseudocode is string
        df["pseudocode"] = df["pseudocode"].astype(str)

        # Fill NaN
        for col in df.columns:
            if df[col].dtype in ["float64", "int64"]:
                df[col] = df[col].fillna(0)
            else:
                df[col] = df[col].fillna("unknown")

        schools = [
            School(**{k: row[k] for k in available})
            for _, row in df.iterrows()
        ]

        db.bulk_save_objects(schools)
        log.info(f"Seeded {len(schools)} schools into database")
        return len(schools)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    init_db()
    n = seed_schools(force=True)
    print(f"Done. {n} schools in database.")


def seed_users(force: bool = False) -> None:
    """
    Seed default admin + one demo principal.
    Safe to call multiple times — skips if already seeded.
    """
    from app.api.auth import hash_password
    from app.database.models import User

    with get_db_context() as db:
        if db.query(User).count() > 0 and not force:
            log.info("Users already seeded. Skipping.")
            return

        if force:
            db.query(User).delete()

        import os
        from config import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

        defaults = []

        # Only seed admin if DEFAULT_ADMIN_PASSWORD is set in environment
        if DEFAULT_ADMIN_PASSWORD:
            defaults.append(User(
                username          = DEFAULT_ADMIN_USERNAME,
                hashed_password   = hash_password(DEFAULT_ADMIN_PASSWORD),
                role              = "admin",
                full_name         = "System Administrator",
                school_pseudocode = None,
                is_active         = True,
            ))
            log.info(f"Seeded admin user: {DEFAULT_ADMIN_USERNAME}")
        else:
            log.warning(
                "DEFAULT_ADMIN_PASSWORD not set in environment. "
                "No admin user seeded. Set it in .env to create the initial admin."
            )

        if defaults:
            db.bulk_save_objects(defaults)
            log.info(f"Seeded {len(defaults)} default users from environment config")