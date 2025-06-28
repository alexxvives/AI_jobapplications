from sqlalchemy import Column, Integer, String, Text, JSON
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    location = Column(String, nullable=True)
    visa_status = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    skills = Column(JSON, nullable=True)  # Store as JSON array
    languages = Column(JSON, nullable=True)  # Store as JSON array
    work_experience = Column(JSON, nullable=True)  # Store as JSON array of objects
    education = Column(JSON, nullable=True)  # Store as JSON array of objects 