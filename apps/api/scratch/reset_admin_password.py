import asyncio
from app.core.database import async_session_factory
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.email == "admin@historiai.vn")
        )
        user = result.scalar_one_or_none()
        if user:
            user.hashed_password = get_password_hash("admin123")
            await session.commit()
            print("Password updated successfully!")
        else:
            print("User admin@historiai.vn not found")

if __name__ == "__main__":
    asyncio.run(main())
