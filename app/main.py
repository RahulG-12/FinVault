from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.schemas import UserRegister, UserLogin, TokenResponse, UserOut

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    # Check if username or email already exists
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Username already registered"
        )
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    # Create new user instance
    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    # 1. Fetch user from database
    user = db.query(User).filter(User.username == data.username).first()
    
    # 2. Validate user and password
    # If this fails, HTTPException stops the function immediately
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid credentials"
        )
    
    # 3. Generate the JWT access token
    # Fixed: This line is now guaranteed to run after validation passes
    token = create_access_token({"sub": str(user.id)})
    
    # 4. Return the successful response
    return TokenResponse(
        access_token=token, 
        user_id=user.id, 
        username=user.username
    )