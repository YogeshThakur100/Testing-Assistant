from sqlalchemy import Column, Float, Integer, String,TIMESTAMP,Boolean,Text,ForeignKey , UUID
from sqlalchemy.dialects.postgresql import JSONB
# from . import database.Base as Base
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import relationship
from database.session import Base , engine
from datetime import datetime
import uuid

class UserChat(Base):
    __tablename__ = "usersChat"
    id = Column(UUID , primary_key=True , index = True , default=uuid.uuid4)
    user_id = Column(Integer , ForeignKey("users.id" ,ondelete="CASCADE"))
    title = Column(String , default=None)
    requirements = Column(String , default=None)
    output_format = Column(String , default=None)
    created_at = Column(TIMESTAMP(timezone=True) , default=datetime.utcnow)

    user = relationship(
        "User",
        back_populates="chats",
    )

    messages = relationship(
        'UserMessage',
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

class UserMessage(Base):
    __tablename__ = 'usersMessage'
    id = Column(UUID , primary_key=True , index = True , default=uuid.uuid4)
    chat_id = Column(UUID , ForeignKey("usersChat.id" , ondelete="CASCADE"))
    role = Column(String , nullable=False)
    content = Column(String , nullable=False)
    created_at = Column(TIMESTAMP(timezone=True) , default=datetime.utcnow)

    chat = relationship(
        "UserChat",
        back_populates="messages",
    )

