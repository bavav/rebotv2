from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func,JSON, BigInteger, Text, Interval, String, DateTime, Integer, Boolean, ForeignKey, UniqueConstraint

class Base(DeclarativeBase):
    pass



class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True,autoincrement=True)
    message_count: Mapped[int] = mapped_column(BigInteger, default=0)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    first_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    can_send_photos: Mapped[Optional[bool]] = mapped_column(Boolean,default=False)



