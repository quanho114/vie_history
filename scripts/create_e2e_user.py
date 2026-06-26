#!/usr/bin/env python3
import asyncio
import os
import sys

# Ensure apps/api is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from app.core.database import async_session
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def main():
    email = "test@example.com"
    username = "test_user"
    password = "Test1234!"
    
    print(f"Checking if E2E test user {email} exists...")
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            print("E2E test user already exists.")
            return

        print("Creating E2E test user...")
        new_user = User(
            email=email,
            username=username,
            hashed_password=get_password_hash(password),
            role="user"
        )
        db.add(new_user)
        await db.commit()
        print("E2E test user created successfully.")

if __name__ == "__main__":
    asyncio.run(main())
