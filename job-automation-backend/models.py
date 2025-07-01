from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, DateTime, func
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=True)  # e.g., 'Software Engineer', 'Data Analyst'
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    skills = Column(JSON, nullable=True)
    languages = Column(JSON, nullable=True)
    work_experience = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    image_url = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    country = Column(String, nullable=True)
    citizenship = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    job_preferences = Column(JSON, nullable=True)
    achievements = Column(JSON, nullable=True)
    certificates = Column(JSON, nullable=True) 