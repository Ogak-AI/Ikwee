from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

import os

# Default to local SQLite, but allow Render (or Postgres) to override via env variable
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ussd_platform.db")

# If using Postgres later from Render, SQLAlchemy needs 'postgresql://' not 'postgres://'
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
