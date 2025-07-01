from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class SkillWithYears(BaseModel):
    name: str
    years: int | None = None

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
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class JobResult(BaseModel):
    id: Optional[int] = None
    title: str
    company: str
    location: str
    description: str
    link: str
    source: Optional[str] = None

class JobPreference(BaseModel):
    linkedin: str | None = None
    twitter: str | None = None
    github: str | None = None
    portfolio: str | None = None
    other_url: str | None = None
    notice_period: str | None = None
    total_experience: str | None = None
    default_experience: str | None = None
    highest_education: str | None = None
    companies_to_exclude: list[str] | str | None = None
    willing_to_relocate: str | None = None
    driving_license: str | None = None
    visa_requirement: str | None = None
    race_ethnicity: str | None = None
    disability: str | None = None
    veteran_status: str | None = None
    security_clearance: str | None = None

class WorkExperienceItem(BaseModel):
    title: str
    company: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None

class Certificate(BaseModel):
    name: str
    organization: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    credential_id: str | None = None
    credential_url: str | None = None

class Achievement(BaseModel):
    title: str
    issuer: str | None = None
    date: str | None = None
    description: str | None = None

class ProfileCreate(BaseModel):
    title: str | None = None
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    image_url: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None
    citizenship: str | None = None
    gender: str | None = None
    skills: list[SkillWithYears] | None = None
    languages: list[str] | None = None
    work_experience: list[WorkExperienceItem] | None = None
    education: list[Education] | None = None
    job_preferences: JobPreference | None = None
    achievements: list[Achievement] | None = None
    certificates: list[Certificate] | None = None

class ProfileUpdate(ProfileCreate):
    pass

class ProfileResponse(ProfileCreate):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        } 