from pgvector.sqlalchemy import Vector
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, ForeignKey, Index
from sqlalchemy.orm import sessionmaker, Session, declarative_base, Mapped, mapped_column, relationship
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
#SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:12345@localhost:5433/viddb"
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:12345@172.184.205.239:5432/viddb"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


#currently all videos uploaded by all users are available to everyone
#This may need to change beyond the demo project

class User(Base):
    __tablename__ = "video_users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    videos: Mapped[List["VideoAnalysisStages"]] = relationship(back_populates="user")
    
Base.metadata.create_all(engine)

#Each Stages of Video analysis
class VideoAnalysisStages(Base):
    __tablename__ = "video_analysis_stages"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    start: Mapped[int] = mapped_column(nullable=False)
    end: Mapped[int] = mapped_column(nullable=False)
    path: Mapped[str] = mapped_column(String(255))
    embedding: Mapped[Vector] = mapped_column(Vector(768))
    userid: Mapped[int] = mapped_column(ForeignKey("video_users.id"))
    user: Mapped["User"] = relationship(back_populates="videos")
    


class VideoAnalysisTask(Base):
    __tablename__ = "video_analysis_tasks"
    AIPROCESSING = 0
    DBPROCESSED = 1
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    taskid: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(255))
    status: Mapped[int] = mapped_column(default=0)



Base.metadata.create_all(engine)

class UserLogin(BaseModel):
    username: str
    email: str
    passwd: str

class UserCreate(BaseModel):
    username: str
    email: str
    passwd: str

class VideoSegment(BaseModel):
    start: int
    end: int
    title: str
    description: str
    filename: str

class VideoStore(BaseModel):
    start: List[int]
    end: List[int]
    title: str
    description: List[str]
    filename: str
    public_video: bool = False

class GetAudio(BaseModel):
    indexSentences: int
    indexParagraphs: int
    sentence: str
    index: str

class CreateSRT(BaseModel):
    paragraphs: List[List[str]]
    mp3Paths: List[str]
    id: str

class MergeVideo(BaseModel):
    mp3paths: List[str]
    paragraphs: List[List[str]]
    srtpath: str
    duration: List[float]
    id: str
    user_id: int

class QueryVideo(BaseModel):
    paragraph: List[str]

def test():
    with Session(engine) as session:
        stages = session.query(VideoAnalysisStages).all()
        for s in stages:
            print(s.id, s.path)

if __name__ == "__main__":
    test()