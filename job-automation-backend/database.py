import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Always use the absolute path for the DB
DB_ABS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'job_automation.db'))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_ABS_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    description = Column(Text)
    link = Column(String(500), unique=True, nullable=False)
    source = Column(String(50))
    fetched_at = Column(DateTime, default=func.now(), index=True)

    __table_args__ = (
        UniqueConstraint('link', name='uq_job_link'),
    ) 