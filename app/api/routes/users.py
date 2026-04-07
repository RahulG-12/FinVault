from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.role import Role, UserRole, RolePermission
from app.schemas.schemas import UserOut, AssignRole

router = APIRouter()

@router.post("/assign-role")
def assign_role(data: AssignRole, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    role = db.query(Role).filter(Role.id == data.role_id).first()
    if not role:
        raise HTTPException(404, "Role not found")
    existing = db.query(UserRole).filter(UserRole.user_id == data.user_id, UserRole.role_id == data.role_id).first()
    if existing:
        raise HTTPException(400, "Role already assigned")
    db.add(UserRole(user_id=data.user_id, role_id=data.role_id))
    db.commit()
    return {"message": f"Role '{role.name}' assigned to user '{user.username}'"}

@router.get("/{user_id}/roles")
def get_user_roles(user_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    roles = []
    for ur in user_roles:
        role = db.query(Role).filter(Role.id == ur.role_id).first()
        if role:
            roles.append({"id": role.id, "name": role.name, "description": role.description})
    return {"user_id": user_id, "username": user.username, "roles": roles}

@router.get("/{user_id}/permissions")
def get_user_permissions(user_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    permissions = set()
    roles = []
    for ur in user_roles:
        role = db.query(Role).filter(Role.id == ur.role_id).first()
        if role:
            roles.append(role.name)
            perms = db.query(RolePermission).filter(RolePermission.role_id == ur.role_id).all()
            permissions.update(p.permission for p in perms)
    return {"user_id": user_id, "username": user.username, "roles": roles, "permissions": sorted(permissions)}

@router.get("", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(User).all()

@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user
