import os
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import uuid
import os

import models
import dbaccess
import video_analysis
import video_edit
import audio_generate_each_sentence
import srt_generate_for_each_sentences
import calculate_durations_for_each_image
from auth import create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES, TokenData, oauth2_scheme


router = APIRouter()

#login
@router.post("/login")
async def login(user: models.UserLogin):
    print(user.email)
    user = await dbaccess.verify_user(user)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "id": user.id},
        expires_delta=access_token_expires
    )
    return {"message": "登录成功", "access_token": access_token, "token_type": "bearer"}

#register
@router.post("/register")
async def register(user: models.UserCreate):
    """
    Register a new user."""
    user = await dbaccess.create_user(user)
    return {"message": "Register Success!"}

#auth for swagger
@router.get("/token")
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Validate user credentials and return a token
    return {"access_token": "fake-token", "token_type": "bearer"}


#check current user
@router.get("/users/me")
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    return current_user

@router.get("/videos")
async def get_videos():#current_user: TokenData = Depends(get_current_user)):
    """
    Get all videos uploaded by the current user
    """
    '''
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")'''
    videos = await dbaccess.get_video_by_user(dbaccess.PUBLICID)#current_user.id)
    paths = []
    for v in videos:
        paths.append(v.path)
    return paths

#upload videos for processing
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a video to system
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    if not file.filename.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="File is not a video")
    DIR = "./lclips/"
    guid = uuid.uuid4().hex
    filename = os.path.join(DIR, file.filename + guid + ".mp4")
    # Save the file to the server
    with open(filename, "wb") as f:
        f.write(file.file.read())
    return {"filename": filename}

@router.post("/analysevideo")
async def analyse_video(filepath: str) -> list[models.VideoSegment]:
    """
    Call gemini to analyse the video
    Return the segemented video
    """
    if not filepath:
        raise HTTPException(status_code=400, detail="No file uploaded")
    if not filepath.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="File is not a video")
    response = await video_analysis.gemini_run(filepath)
    
    parts = []
    descriptions = []
    try:
        for s in response["segments"]:
            start = s["start"].split(":")
            end = s["end"].split(":")
            start = int(start[0])*60 + int(start[1])
            end = int(end[0])*60 + int(end[1])
            parts.append((start,end))
            descriptions.append(s["theme"] + s["summary"])
    except:
        raise HTTPException(status_code=400, detail="Error parsing response")
    
    ret = []
    for i in range(len(parts)):
        
        
        print("embedding completed")
        start = parts[i][0]
        end = parts[i][1]
        print(i, parts[i][0], parts[i][1])
        
        #url, name = videoGetUrl(file)
        #names.append()
        print(start, end)
        clip = models.VideoSegment(
            start=start,
            end=end,
            title = response["title"],
            description=descriptions[i],
            filename=filepath
        )
        ret.append(clip)
    return ret

@router.post("/storevideos")
async def store_videos(videoStore: models.VideoStore) -> list[str]:#, current_user: TokenData = Depends(get_current_user)):
    """
    Store the video segments in the database
    """
    public_video = videoStore.public_video
    ALPHA = 0.3
    # dividing the video into segments
    parts = []
    url = videoStore.filename
    filenames = []
    embeddings = []
    print(videoStore)
    try:
        embeddingTitle = video_analysis.embeddingRun(videoStore.title)
    except:
        raise HTTPException(status_code=400, detail="Error embedding title")
    for i in range(len(videoStore.start)):
        
        try:
            embeddingDescriptions = video_analysis.embeddingRun(videoStore.description[i])
            for j in range(len(embeddingDescriptions)):
                #attempt: relate the title to the video
                embeddingDescriptions[j] = embeddingTitle[j]*ALPHA + embeddingDescriptions[j]*(1-ALPHA)
        except:
            raise HTTPException(status_code=400, detail="Error embedding video")
        filepath = videoStore.filename
        filename = os.path.splitext(filepath)[0]
        originalname = os.path.basename(filename)
        
        file = originalname+uuid.uuid4().hex+".mp4"
        print(file)
        filenames.append(file)
        parts.append((videoStore.start[i], videoStore.end[i]))
        embeddings.append(embeddingDescriptions)
    print(url, parts, filenames)
    ve = video_edit.VideoEdit(url, parts, "./lclips", filenames=filenames)
    paths = ve.divideVideo(filenames)
    '''
    try:
        ve = video_edit.VideoEdit(url, parts, filenames=filenames)
        ve.divideVideo()
    except:
        raise HTTPException(status_code=400, detail="Error dividing video")'''
    

    #store to database
    id = dbaccess.PUBLICID
    '''if public_video:
        id = dbaccess.PUBLICID
    else:
        id = current_user.id'''
    await dbaccess.save_segments_to_db(parts, paths, embeddings, id)

    return paths

@router.get("/getparagraphs")
async def get_paragraphs_with_prompt(prompt: str): #, current_user: TokenData = Depends(get_current_user)):
    """
    Get video segments with the given prompt
    prompt: prompt used to generate video
    """
    if not prompt:
        raise HTTPException(status_code=400, detail="No prompt provided")
    #if not current_user:
    #    raise HTTPException(status_code=401, detail="Not authenticated")
    id = uuid.uuid4().hex
    #Split into paragraphs
    try:
        mp3paths = []
        sentencesAll = []
        paragraphs = (await video_analysis.gemini_paragraph_run(prompt))["segements"]
        for i in range(len(paragraphs)):
            p = paragraphs[i]
            print(p)
            #sentences = audio_generate_each_sentence.split_into_sentences(p["content"])
            #print(sentences)
            sentences = p["clauses"]
            sentences.append(p['title'])
            sentencesAll.append(sentences)
        mp3paths = audio_generate_each_sentence.synthesize_sentences_to_speech("./tmp/"+id, sentencesAll)
        duration = calculate_durations_for_each_image.calculate_sentence_audio_durations(" ", mp3paths)

        return {"paragraphs": sentencesAll, "id": id, "mp3paths": mp3paths, "duration": duration}
    except:
        raise HTTPException(status_code=400, detail="Error parsing prompt")
    

def streamingAudio(filepath: str):
    '''
    Stream the audio file'''
    with open(filepath, "rb") as f:
        yield from f
@router.get("/streamaudio")
async def stream_audio(filepath: str): #, current_user: TokenData = Depends(get_current_user)):
    """
    Stream the audio file
    filepath: path of the audio file
    """
    if not filepath:
        raise HTTPException(status_code=400, detail="No file provided")
    #if not current_user:
    #    raise HTTPException(status_code=401, detail="Not authenticated")
    
    #stream the audio
    try:
        return StreamingResponse(streamingAudio(filepath), media_type="audio/mpeg")
    except:
        raise HTTPException(status_code=400, detail="Error streaming audio")
    

@router.post("/createsrt")
async def create_srt(createSrt: models.CreateSRT): #, current_user: TokenData = Depends(get_current_user)):
    """
    Create srt file for the given video segments
    """
    if not createSrt:
        raise HTTPException(status_code=400, detail="No video segments provided")
    #if not current_user:
    #    raise HTTPException(status_code=401, detail="Not authenticated")
    
    #create srt file
    try:
        srt_file = srt_generate_for_each_sentences.generate_srt_from_arrays(createSrt.mp3Paths, createSrt.paragraphs, "./tmp/"+createSrt.id, "./tmp/"+createSrt.id+"/srt.srt")
        return {"srt_file": srt_file}
    except:
        raise HTTPException(status_code=400, detail="Error creating SRT file")


def streaming_video(filepath: str):
    """
    Stream the video file
    """
    with open(filepath, "rb") as f:
        yield from f

@router.get("/streamvideo")
async def stream_video(filename:str): #, current_user: TokenData = Depends(get_current_user)):
    """
    Stream the video segments with the given filename
    filename: filename of the video
    """
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    #if not current_user:
    #    raise HTTPException(status_code=401, detail="Not authenticated")
    
    #stream the video
    try:
        return StreamingResponse(streaming_video(filename), media_type="video/mp4")
    except:
        raise HTTPException(status_code=400, detail="Error streaming video")

@router.post("/mergevideo")
async def merge_video(mergeVideo: models.MergeVideo): #, current_user: TokenData = Depends(get_current_user)):
    """
    Merge video segments with the given mp3 files, video files and subtitle file
    """
    if not mergeVideo:
        raise HTTPException(status_code=400, detail="No video segments provided")
    #if not current_user:
    #    raise HTTPException(status_code=401, detail="Not authenticated")
    
    #merge the video
    try:
        vm = video_edit.MergeVideos()
        paragraphs= mergeVideo.paragraphs
        duration = mergeVideo.duration
        i = 0
        mp3Paths = mergeVideo.mp3paths
        srtPath = mergeVideo.srtpath
        
        #merge the mp3 files
        for p in paragraphs:
            paragraph = ""
            paraduration = 0
            title = p[-1]
            for k in range(len(p)-1):
                sentence = p[k]
                paraduration += duration[i]
                paraduration += 0.5
                paragraph += (sentence+", ")
                i += 1
            print(paraduration)
            embedding = video_analysis.embeddingRun(paragraph)
            videos = await dbaccess.get_video_segments_by_prompt(embedding, mergeVideo.user_id)
            if videos == None:
                return None, "失败：没有有关联的素材"
            vm.videoAdd(videos,paraduration,"./tmp/title.mp4")
        clip = vm.videoConcat()
        audio = vm.mergeAudio(mp3Paths,"./tmp/"+mergeVideo.id+"/title.mp3")
        vm.mergeAll(clip,audio,srtPath,"./title.mp4","./tmp/"+mergeVideo.id+"/final_title.mp4")
        return {"message": "Video merged successfully", "path": "./tmp/"+mergeVideo.id+"/final_title.mp4"}
    except:
        raise HTTPException(status_code=400, detail="Error merging video")