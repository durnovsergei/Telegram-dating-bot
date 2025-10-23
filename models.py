from sqlalchemy import Column, Integer, String, JSON
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    bio = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    target_gender = Column(String, nullable=True)
    faculty = Column(String, nullable=True)
    photo_id = Column(String, nullable=False)
    likes = Column(JSON, nullable=False, default=[])
    dislikes = Column(JSON, nullable=False, default=[])
    pending_likes = Column(JSON, nullable=False, default=[])

