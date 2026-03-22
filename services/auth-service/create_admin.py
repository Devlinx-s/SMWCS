import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.user import SystemUser, UserRole
from app.core.security import hash_password

async def create_admin():
    engine = create_async_engine(
        'postgresql+asyncpg://smwcs:smwcs_dev_pass@127.0.0.1:5432/smwcs',
        echo=False
    )
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        user = SystemUser(
            id=uuid.uuid4(),
            email='admin@smwcs.co.ke',
            password_hash=hash_password('Admin1234!'),
            first_name='System',
            last_name='Admin',
            role=UserRole.super_admin,
            is_active=True,
            mfa_enabled=False,
        )
        session.add(user)
        await session.commit()
        print('Admin user created successfully')
        print('Email:    admin@smwcs.co.ke')
        print('Password: Admin1234!')
        print('Role:     super_admin')
    await engine.dispose()

asyncio.run(create_admin())
