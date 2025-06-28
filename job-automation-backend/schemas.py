from pydantic import BaseModel, EmailStr
from typing import List, Optional

class WorkExperience(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

class Education(BaseModel):
    degree: Optional[str] = None
    school: str
    year: Optional[str] = None
    location: Optional[str] = None
    gpa: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    location: str | None = None
    visa_status: str | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    full_name: str | None = None
    location: str | None = None
    visa_status: str | None = None
    phone: str | None = None
    skills: List[str] | None = None
    languages: List[str] | None = None
    work_experience: List[WorkExperience] | None = None
    education: List[Education] | None = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    location: str | None = None
    visa_status: str | None = None
    phone: str | None = None
    skills: List[str] | None = None
    languages: List[str] | None = None
    work_experience: List[WorkExperience] | None = None
    education: List[Education] | None = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class JobResult(BaseModel):
    id: int
    title: str
    company: str
    location: str
    description: str
    link: str
    source: Optional[str] = None 