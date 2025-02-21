#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add the server directory to the Python path
server_dir = str(Path(__file__).resolve().parents[1])
sys.path.append(server_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.user import User, UserRole

def create_superadmin(email: str, password: str):
    # Create database engine
    engine = create_engine(settings.DATABASE_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if superadmin already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"User with email {email} already exists")
            return
        
        # Create superadmin user
        superadmin = User(
            email=email,
            password=password,  # Password will be hashed in User model
            is_active=True,
            is_superuser=True,
            role=UserRole.ADMIN,
            is_verified=True,
            full_name="Super Admin"
        )
        
        db.add(superadmin)
        db.commit()
        print(f"Superadmin user created successfully with email: {email}")
        
    except Exception as e:
        print(f"Error creating superadmin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_superadmin.py <email> <password>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    create_superadmin(email, password)
