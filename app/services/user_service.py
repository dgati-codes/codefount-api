"""
app/services/user_service.py
=============================
Business logic for User operations.

Spring Boot equivalent
-----------------------
  @Service UserService — the layer between Controller (@RestController)
  and Repository (@Repository / JpaRepository).
  AsyncSession (SQLAlchemy)  ≈  JpaRepository<User, Long> injected via @Autowired.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserRegisterRequest, UserUpdateRequest


class UserService:
    """
    Spring Boot equivalent:
      @Service public class UserService { @Autowired UserRepository repo; ... }
    Constructor injection mirrors @Autowired UserRepository.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Queries ──────────────────────────────────────────────────────────────

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """repo.findById(id)"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """repo.findByEmail(email)  — derived query in Spring Data JPA"""
        result = await self.db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        user = await self.get_by_email(email)
        return user is not None

    # ── Commands ─────────────────────────────────────────────────────────────

    async def create(self, data: UserRegisterRequest, role: UserRole = UserRole.STUDENT) -> User:
        """
        Spring Boot: userRepository.save(new User(...))
        Raises ValueError if email already taken.
        """
        if await self.email_exists(data.email):
            raise ValueError("Email already registered")

        user = User(
            full_name=data.full_name,
            email=data.email.lower().strip(),
            hashed_password=hash_password(data.password),
            phone=data.phone,
            gender=data.gender,
            country_code=data.country_code,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()   # assigns id before commit — like JPA's persist()
        return user

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Spring Boot equivalent:
          authenticationManager.authenticate(
            new UsernamePasswordAuthenticationToken(email, password))
        Returns None on wrong credentials (never raises — let the endpoint decide HTTP status).
        """
        user = await self.get_by_email(email)
        if user is None:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def update(self, user: User, data: UserUpdateRequest) -> User:
        """
        Partial update — only non-None fields are applied.
        Spring Boot: BeanUtils.copyProperties with null-ignore or MapStruct.
        """
        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        self.db.add(user)
        await self.db.flush()
        return user

    async def change_password(self, user: User, current: str, new: str) -> None:
        if not verify_password(current, user.hashed_password):
            raise ValueError("Current password is incorrect")
        user.hashed_password = hash_password(new)
        self.db.add(user)
        await self.db.flush()

    async def deactivate(self, user: User) -> None:
        user.is_active = False
        self.db.add(user)
        await self.db.flush()

    # ── Superuser seed ────────────────────────────────────────────────────────

    async def ensure_superuser(self, email: str, password: str) -> None:
        """Called once on app startup. Spring Boot: ApplicationRunner / CommandLineRunner."""
        if not await self.email_exists(email):
            user = User(
                full_name="Super Admin",
                email=email,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            self.db.add(user)
            await self.db.flush()