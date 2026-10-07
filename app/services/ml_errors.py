from sqlalchemy import func
from sqlalchemy import DateTime
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, String, select, Integer, Boolean, Float, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from ..config import config
# 1. Define the PostgreSQL connection string
DATABASE_URL = config.DATABASE_URL

# 2. Setup the engine and session helper
engine = create_engine(DATABASE_URL, echo=True)  # echo=True prints SQL commands to console

# 3. Base class for defining database models
class Base(DeclarativeBase):
    pass

# 4. Define your Table/Model
class CheckedText(Base):
    __tablename__ = "texts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    ts_of_getting: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    chat_id: Mapped[int] = mapped_column(BigInteger)
    from_user_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger)
    text: Mapped[str] = mapped_column(String())
    is_spam: Mapped[bool] = mapped_column(Boolean())
    approwed_is_spam: Mapped[bool] = mapped_column(Boolean(),nullable=True)
    ts_of_approve: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    confidence: Mapped[float] = mapped_column(Float())
    reason: Mapped[str] = mapped_column(String())
    is_checked: Mapped[bool] = mapped_column(Boolean(),nullable=False,default=False)
    
Base.metadata.create_all(engine)
def get_sesion() -> Session:
    return Session(engine)
# 5. Main execution wrapper
if __name__ == "__main__":
    # Create tables in the PostgreSQL database if they don't exist
    

    # Use Session to interact with the database
    with Session(engine) as session:
        # --- CREATE (Insert Data) ---
        new_user = CheckedText()
        session.add(new_user)
        session.commit()  # Commits transactions safely
        print(f"\nCreated: {new_user}")

        # --- READ (Select Data) ---
        # Querying with the newer SQLAlchemy 2.0 1.x style
        statement = select(User).where(User.name == "Alice")
        user = session.scalars(statement).first()
        print(f"\nRetrieved: {user}")

        # --- UPDATE (Modify Data) ---
        if user:
            user.email = "alice_new@example.com"
            session.commit()
            print(f"\nUpdated User Email: {user.email}")

        # --- DELETE (Remove Data) ---
        # session.delete(user)
        # session.commit()
