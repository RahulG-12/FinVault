from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.role import Role, RolePermission, UserRole
from app.schemas.schemas import RoleCreate, RoleOut, AssignRole

router = APIRouter()

DEFAULT_ROLE_PERMISSIONS = {
    "Admin": ["documents:read", "documents:write", "documents:delete", "users:manage", "roles:manage", "rag:search", "rag:index"],
    "Financial Analyst": ["documents:read", "documents:write", "rag:search", "rag:index"],
    "Auditor": ["documents:read", "rag:search"],
    "Client": ["documents:read"],
}

@router.post("/create", response_model=RoleOut, status_code=201)
def create_role(data: RoleCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    existing = db.query(Role).filter(Role.name == data.name).first()
    if existing:
        raise HTTPException(400, "Role already exists")
    role = Role(name=data.name, description=data.description)
    db.add(role)
    db.flush()
    for perm in data.permissions:
        db.add(RolePermission(role_id=role.id, permission=perm))
    db.commit()
    db.refresh(role)
    return role

@router.get("", response_model=List[RoleOut])
def list_roles(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Role).all()

@router.post("/seed-defaults")
def seed_default_roles(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    created = []
    for role_name, perms in DEFAULT_ROLE_PERMISSIONS.items():
        if not db.query(Role).filter(Role.name == role_name).first():
            role = Role(name=role_name, description=f"Default {role_name} role")
            db.add(role)
            db.flush()
            for p in perms:
                db.add(RolePermission(role_id=role.id, permission=p))
            created.append(role_name)
    db.commit()
    return {"created": created}
