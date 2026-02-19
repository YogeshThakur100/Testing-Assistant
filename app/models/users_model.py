from sqlalchemy import Column, Float, Integer, String,TIMESTAMP,Boolean,Text,ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
# from . import database.Base as Base
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import relationship
from database.session import Base , engine
from models.users_chat_model import UserChat , UserMessage

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True)
    password = Column(String)
    is_active = Column(Boolean, default=True)
    api_key = Column(String, unique=True,  default=None)
    created_at = Column(TIMESTAMP(timezone=True), default=None)


# One User -> Many Chats
    chats = relationship(
        "UserChat",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )



Base.metadata.create_all(bind=engine)