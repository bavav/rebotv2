from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func,JSON, BigInteger, Text, Interval, String, DateTime, Integer, Boolean, ForeignKey, UniqueConstraint

class Base(DeclarativeBase):
    pass

class CommandPermission(Base):
    __tablename__ = "command_permissions"  # Исправлено: command вместо comand
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    command_name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    user: Mapped["User"] = relationship("User", back_populates="command_permissions")  # Исправлено: command вместо comand
    
    __table_args__ = (
        UniqueConstraint("user_id", "command_name", name="uq_user_command"),
    )

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True,autoincrement=True)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Убрал дубликат
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    admin_level: Mapped[int] = mapped_column(Integer, default=0)
    message_count: Mapped[int] = mapped_column(BigInteger, default=0)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    first_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reputation: Mapped[int] = mapped_column(Integer, default=0)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)
    muted_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    banned_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    
    can_send_photos: Mapped[Optional[bool]] = mapped_column(Boolean,default=True)
    

    command_permissions: Mapped[List["CommandPermission"]] = relationship(
        "CommandPermission", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )

    punishments_received: Mapped[List["Punishment"]] = relationship(
        "Punishment", 
        foreign_keys="Punishment.target_id", 
        back_populates="target"
    )
    punishments_given: Mapped[List["Punishment"]] = relationship(
        "Punishment", 
        foreign_keys="Punishment.admin_id", 
        back_populates="admin"
    )
    rep_history: Mapped[List["ReputationHistory"]] = relationship(
        "ReputationHistory", 
        foreign_keys="ReputationHistory.target_id", 
        back_populates="target"
    )

class Punishment(Base):
    __tablename__ = "punishments"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    admin_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    previous_permissions: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())  # Исправлено: created_at вместо created_ad
    duration: Mapped[Optional[timedelta]] = mapped_column(Interval, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    target: Mapped['User'] = relationship('User', foreign_keys=[target_id], back_populates='punishments_received')
    admin: Mapped['User'] = relationship('User', foreign_keys=[admin_id], back_populates='punishments_given')

class ReputationHistory(Base):
    __tablename__ = "reputation_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    change: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    target: Mapped['User'] = relationship('User', foreign_keys=[target_id], back_populates='rep_history')
    sender: Mapped['User'] = relationship('User', foreign_keys=[sender_id])
