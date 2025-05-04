from models import Session, engine, User, VideoAnalysisStages, VideoAnalysisTask
from models import UserLogin, UserCreate
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import and_, or_

import os
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
PUBLICID = 1
async def verify_user(user: UserLogin) -> bool:
    """
    Verify user credentials against the database.
    user: UserLogin-> username, email, passwd
    """
    with Session(engine) as session:
        email = user.email
        username = user.username
        password = user.passwd
        user = session.query(User).filter(or_(User.email == email, User.username == username)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if pwd_context.verify(user.password, password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
        return True
    
async def create_user(user: UserCreate) -> User:
    """
    Create a new user in the database.
    user: UserCreate-> username, email, passwd
    """
    with Session(engine) as session:
        email = user.email
        username = user.username
        password = user.passwd
        user = session.query(User).filter(or_(User.email == email, User.username == username)).first()
        if user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
        hashed_password = pwd_context.hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        try:
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            return new_user
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating user: {}".format(e))
    
            
async def get_video_by_user(user_id: int) -> list[VideoAnalysisStages]:
    """
    Get videos that either belongs to the user or the public
    user_id: int
    """
    with Session(engine) as session:
        '''videos = session.query(VideoAnalysisStages).filter(or_(VideoAnalysisStages.userid == user_id, \
                                                           VideoAnalysisStages.userid == PUBLICID)).all()'''
        videos = session.query(VideoAnalysisStages).filter(VideoAnalysisStages.userid == user_id).all()
        return videos
    
async def save_segments_to_db(parts: tuple[int,int], paths: list[str], \
                              description_embedding: list[list[float]], user_id: int) -> bool:
    """
    Save the segments to the database
    parts: list[(int,int)], 
    description: list[str], 
    description_embedding: list[list[float]]
    user_id: int
    """
    print("saving segements to db")
    print("parts: ", parts)
    print("paths: ", paths)
    print("user_id: ", user_id)
    with Session(engine) as session:
        user = session.query(User).filter(User.id == user_id).first()
        print(user, user.id, user.username, user.videos)
        for i in range(len(parts)):
            part = parts[i]
            
            desc_embedding = description_embedding[i]
            video_segment = VideoAnalysisStages(start=part[0], end=part[1], \
                                                path=paths[i], embedding=desc_embedding, userid=user.id, user = user)
            session.add(video_segment)
        try:
            session.commit()
            return True
        except Exception as e:
            print("Error saving segments: {}".format(e), "rolling back")
            session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving segments: {}".format(e))


async def get_video_segments_by_prompt(embeddingPrompt: list[float], user_id: int) -> list[VideoAnalysisStages]:
    """
    Get video segments by prompt
    prompt: str
    user_id: int
    """
    similarity_threshold = 0.5
    with Session(engine) as session:
        print("searching for similar videos")
        result = session.query(VideoAnalysisStages, VideoAnalysisStages.embedding.cosine_distance(embeddingPrompt)
                    .label("distance"))\
                    .filter(VideoAnalysisStages.embedding.cosine_distance(embeddingPrompt) < similarity_threshold)\
                    .filter(or_(VideoAnalysisStages.userid == user_id, VideoAnalysisStages.userid == PUBLICID))\
                    .order_by("distance").all()
        ret = []
        for r in result:
            ret.append(r[0])
        if len(ret) == 0:
            return "No related videos found"
        else:
            return ret