"""
app/api/routes/auth_routes.py
──────────────────────────────
Authentication endpoints:
  POST /auth/login              — returns JWT token
  GET  /auth/me                 — current user profile
  POST /auth/register           — admin creates a new principal account
  POST /auth/register-principal — principal self-registration with UDISE
  GET  /auth/users              — admin lists all users
  PUT  /auth/users/{id}/toggle  — admin activates/deactivates user
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.database.db import get_db
from app.database.models import User, School
from app.api.auth.auth import (
    hash_password, verify_password, create_token,
    get_current_user, require_admin,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request/response models
class RegisterRequest(BaseModel):
    username:         str
    password:         str
    full_name:        Optional[str] = None
    school_pseudocode: Optional[str] = None   # required for principal role
    role:             str = "principal"        # admin | principal


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str


# ─────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────

@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form.username).first()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact administrator.",
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    token = create_token({
        "sub":               user.username,
        "role":              user.role,
        "school_pseudocode": user.school_pseudocode,
    })

    return {
        "access_token":      token,
        "token_type":        "bearer",
        "role":              user.role,
        "username":          user.username,
        "full_name":         user.full_name,
        "school_pseudocode": user.school_pseudocode,
    }


# ─────────────────────────────────────────────────────────────
# CURRENT USER PROFILE
# ─────────────────────────────────────────────────────────────

@router.get("/me")
def get_profile(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    result = {
        "id":                current_user.id,
        "username":          current_user.username,
        "role":              current_user.role,
        "full_name":         current_user.full_name,
        "school_pseudocode": current_user.school_pseudocode,
        "is_active":         current_user.is_active,
        "last_login":        current_user.last_login.isoformat() if current_user.last_login else None,
    }

    # For principals — attach their school baseline
    if current_user.role == "principal" and current_user.school_pseudocode:
        school = db.query(School).filter(
            School.pseudocode == current_user.school_pseudocode
        ).first()
        if school:
            result["school"] = {
                "pseudocode":        school.pseudocode,
                "school_level":      school.school_level,
                "total_students":    school.total_students,
                "total_tch":         school.total_tch,
                "ptr":               school.ptr,
                "risk_score":        school.risk_score,
                "risk_level":        school.risk_level,
                "infrastructure_gap":school.infrastructure_gap,
            }

    return result


# ─────────────────────────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────────────────────────

@router.post("/change-password")
def change_password(
    req:          ChangePasswordRequest,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    current_user.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


# ─────────────────────────────────────────────────────────────
# ADMIN — REGISTER NEW USER
# ─────────────────────────────────────────────────────────────

@router.post("/register")
def register_user(
    req:        RegisterRequest,
    admin:      User    = Depends(require_admin),
    db:         Session = Depends(get_db),
):
    # Check username not taken
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail=f"Username '{req.username}' already exists")

    # Principal must have a school pseudocode
    if req.role == "principal" and not req.school_pseudocode:
        raise HTTPException(
            status_code=400,
            detail="school_pseudocode is required for principal role"
        )

    # Verify school exists for principals
    if req.role == "principal" and req.school_pseudocode:
        school = db.query(School).filter(School.pseudocode == req.school_pseudocode).first()
        if not school:
            raise HTTPException(
                status_code=404,
                detail=f"School '{req.school_pseudocode}' not found in database"
            )

    if req.role not in ("admin", "principal"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'principal'")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = User(
        username          = req.username,
        hashed_password   = hash_password(req.password),
        role              = req.role,
        full_name         = req.full_name,
        school_pseudocode = req.school_pseudocode,
        is_active         = True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message":           "User created successfully",
        "id":                user.id,
        "username":          user.username,
        "role":              user.role,
        "school_pseudocode": user.school_pseudocode,
    }


# ─────────────────────────────────────────────────────────────
# PRINCIPAL SELF-REGISTRATION
# ─────────────────────────────────────────────────────────────

class RegisterPrincipalRequest(BaseModel):
    full_name:         str
    school_pseudocode: str
    username:          str
    password:          str


@router.post("/register-principal")
def register_principal(
    req: RegisterPrincipalRequest,
    db:  Session = Depends(get_db),
):
    """
    Self-service principal registration endpoint.
    No admin approval required — creates principal account directly.
    Principal UDISE code will be locked after registration.
    """
    
    # Validate inputs
    if not req.full_name or not req.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required")
    
    if not req.school_pseudocode or not req.school_pseudocode.strip():
        raise HTTPException(status_code=400, detail="School UDISE code is required")
    
    if not req.username or not req.username.strip():
        raise HTTPException(status_code=400, detail="Username is required")
    
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    # Check username not taken
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail=f"Username '{req.username}' already exists")
    
    # Verify school exists
    school = db.query(School).filter(School.pseudocode == req.school_pseudocode).first()
    if not school:
        raise HTTPException(
            status_code=404,
            detail=f"School UDISE '{req.school_pseudocode}' not found in database. Please verify your UDISE code."
        )
    
    # Create principal user
    user = User(
        username          = req.username,
        hashed_password   = hash_password(req.password),
        role              = "principal",
        full_name         = req.full_name,
        school_pseudocode = req.school_pseudocode,
        is_active         = True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "message":           "Principal account created successfully. Your UDISE is now locked.",
        "id":                user.id,
        "username":          user.username,
        "full_name":         user.full_name,
        "school_pseudocode": user.school_pseudocode,
        "role":              "principal",
    }


# ─────────────────────────────────────────────────────────────
# ADMIN — LIST ALL USERS
# ─────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(
    admin: User    = Depends(require_admin),
    db:    Session = Depends(get_db),
):
    users = db.query(User).all()
    return [
        {
            "id":                u.id,
            "username":          u.username,
            "role":              u.role,
            "full_name":         u.full_name,
            "school_pseudocode": u.school_pseudocode,
            "is_active":         u.is_active,
            "last_login":        u.last_login.isoformat() if u.last_login else None,
        }
        for u in users
    ]


# ─────────────────────────────────────────────────────────────
# ADMIN — TOGGLE USER ACTIVE STATUS
# ─────────────────────────────────────────────────────────────

@router.put("/users/{user_id}/toggle")
def toggle_user(
    user_id: int,
    admin:   User    = Depends(require_admin),
    db:      Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.username == admin.username:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    user.is_active = not user.is_active
    db.commit()

    return {
        "message":   f"User {'activated' if user.is_active else 'deactivated'}",
        "username":  user.username,
        "is_active": user.is_active,
    }


# ─────────────────────────────────────────────────────────────
# ADMIN — GET SPECIFIC USER BY ID
# ─────────────────────────────────────────────────────────────

@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    admin:   User    = Depends(require_admin),
    db:      Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = {
        "id":                user.id,
        "username":          user.username,
        "role":              user.role,
        "full_name":         user.full_name,
        "school_pseudocode": user.school_pseudocode,
        "is_active":         user.is_active,
        "created_at":        user.created_at.isoformat() if user.created_at else None,
    }
    
    # Attach school details if principal
    if user.role == "principal" and user.school_pseudocode:
        school = db.query(School).filter(
            School.pseudocode == user.school_pseudocode
        ).first()
        if school:
            result["school"] = {
                "pseudocode":        school.pseudocode,
                "school_level":      school.school_level,
                "total_students":    school.total_students,
                "total_tch":         school.total_tch,
                "ptr":               school.ptr,
                "risk_score":        school.risk_score,
                "risk_level":        school.risk_level,
                "infrastructure_gap":school.infrastructure_gap,
            }
    
    return result


# ─────────────────────────────────────────────────────────────
# ADMIN — GET PRINCIPAL BY UDISE
# ─────────────────────────────────────────────────────────────

@router.get("/users/udise/{udise}")
def get_principal_by_udise(
    udise: str,
    admin: User    = Depends(require_admin),
    db:    Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.school_pseudocode == udise,
        User.role == "principal"
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail=f"Principal with UDISE '{udise}' not found")
    
    result = {
        "id":                user.id,
        "username":          user.username,
        "full_name":         user.full_name,
        "school_pseudocode": user.school_pseudocode,
        "is_active":         user.is_active,
        "created_at":        user.created_at.isoformat() if user.created_at else None,
    }
    
    # Attach school details
    school = db.query(School).filter(School.pseudocode == udise).first()
    if school:
        result["school"] = {
            "pseudocode":        school.pseudocode,
            "school_level":      school.school_level,
            "total_students":    school.total_students,
            "total_tch":         school.total_tch,
            "ptr":               school.ptr,
            "risk_score":        school.risk_score,
            "risk_level":        school.risk_level,
            "infrastructure_gap":school.infrastructure_gap,
        }
    
    return result


# ─────────────────────────────────────────────────────────────
# ADMIN — UPDATE USER DETAILS
# ─────────────────────────────────────────────────────────────

class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    req:     UpdateUserRequest,
    admin:   User    = Depends(require_admin),
    db:      Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update full_name
    if req.full_name is not None:
        user.full_name = req.full_name
    
    # Update username (check for duplicates)
    if req.username is not None and req.username != user.username:
        if db.query(User).filter(User.username == req.username).first():
            raise HTTPException(status_code=400, detail=f"Username '{req.username}' already exists")
        user.username = req.username
    
    db.commit()
    db.refresh(user)
    
    return {
        "message": "User updated successfully",
        "id":      user.id,
        "username": user.username,
        "full_name": user.full_name,
    }


# ─────────────────────────────────────────────────────────────
# ADMIN — DELETE USER
# ─────────────────────────────────────────────────────────────

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin:   User    = Depends(require_admin),
    db:      Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.username == admin.username:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    username = user.username
    db.delete(user)
    db.commit()
    
    return {"message": f"User '{username}' deleted successfully"}


# ─────────────────────────────────────────────────────────────
# SCHOOL MANAGEMENT ENDPOINTS
# ─────────────────────────────────────────────────────────────

class SchoolUpdateRequest(BaseModel):
    school_level: Optional[str] = None
    total_students: Optional[float] = None
    total_boys: Optional[float] = None
    total_girls: Optional[float] = None
    total_tch: Optional[float] = None
    classrooms_total: Optional[float] = None
    has_girls_toilet: Optional[int] = None
    has_boys_toilet: Optional[int] = None
    has_library: Optional[int] = None
    has_playground: Optional[int] = None
    has_electricity: Optional[int] = None
    has_internet: Optional[int] = None


@router.get("/schools")
def list_schools(
    admin: User    = Depends(require_admin),
    db:    Session = Depends(get_db),
):
    schools = db.query(School).all()
    return [
        {
            "pseudocode":        s.pseudocode,
            "school_level":      s.school_level,
            "total_students":    s.total_students,
            "total_tch":         s.total_tch,
            "ptr":               s.ptr,
            "risk_score":        s.risk_score,
            "risk_level":        s.risk_level,
            "infrastructure_gap":s.infrastructure_gap,
        }
        for s in schools
    ]


@router.get("/schools/{pseudocode}")
def get_school(
    pseudocode: str,
    admin:      User    = Depends(require_admin),
    db:         Session = Depends(get_db),
):
    school = db.query(School).filter(School.pseudocode == pseudocode).first()
    if not school:
        raise HTTPException(status_code=404, detail=f"School with UDISE '{pseudocode}' not found")
    
    return {
        "pseudocode":        school.pseudocode,
        "school_level":      school.school_level,
        "total_students":    school.total_students,
        "total_boys":        school.total_boys,
        "total_girls":       school.total_girls,
        "total_tch":         school.total_tch,
        "regular":           school.regular,
        "contract":          school.contract,
        "classrooms_total":  school.classrooms_total,
        "classrooms_pucca":  school.classrooms_pucca,
        "classrooms_good":   school.classrooms_good,
        "has_girls_toilet":  school.has_girls_toilet,
        "has_boys_toilet":   school.has_boys_toilet,
        "has_library":       school.has_library,
        "has_playground":    school.has_playground,
        "has_electricity":   school.has_electricity,
        "has_internet":      school.has_internet,
        "ptr":               school.ptr,
        "risk_score":        school.risk_score,
        "risk_level":        school.risk_level,
        "infrastructure_gap":school.infrastructure_gap,
    }


@router.put("/schools/{pseudocode}")
def update_school(
    pseudocode: str,
    req:        SchoolUpdateRequest,
    admin:      User    = Depends(require_admin),
    db:         Session = Depends(get_db),
):
    school = db.query(School).filter(School.pseudocode == pseudocode).first()
    if not school:
        raise HTTPException(status_code=404, detail=f"School with UDISE '{pseudocode}' not found")
    
    # Update all provided fields
    for field, value in req.dict(exclude_unset=True).items():
        if value is not None:
            setattr(school, field, value)
    
    db.commit()
    db.refresh(school)
    
    return {
        "message": "School updated successfully",
        "pseudocode": school.pseudocode,
        "school_level": school.school_level,
        "total_students": school.total_students,
        "total_tch": school.total_tch,
    }