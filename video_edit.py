import moviepy
import subprocess
import shutil
import urllib
import asyncio
import os
import uuid
from urllib.request import urlretrieve
from pathlib import Path
from moviepy.video.io import ffmpeg_tools as videoTools
from MovieClips import *
import srt2video
#TMPDIRNAME = "/home/azureuser/iapwebsitebackend/tmp/"
class VideoEdit:
    url:str
    parts: list
    size:int
    tracker: list
    originalname: str
    dirname: str
    def __init__(self,url: str,parts: list[(int,int)],clipdir = None, filenames = None):
        self.url = url
        self.parts = parts
        self.size = len(parts)
        self.tracker = [0]*self.size
        self.dirname = clipdir
        self.filenames = filenames
        if not os.path.exists(clipdir):
            os.mkdir(clipdir)
    def divideVideo(self, names = None):
        print(self.url)
        TMPFILENAME = os.path.splitext(self.url)[0]
        originalname = os.path.basename(TMPFILENAME)
        parts = self.parts
        ret = []
        print(TMPFILENAME+".mp4")
        #Path.unlink(TMPFILENAME)
        #clip = moviepy.VideoFileClip(TMPFILENAME+".mp4")
        clip = MovieClips(self.url)
        clip.resize(1960, 1080)
        clip.setFps(24)
        #clip = clip.resized(width=640,height=360)
        name = 1
        for i in range(len(parts)):
            p = parts[i]
            print(p[0],p[1])
            print("checked")
            if int(p[1]) > clip.duration:
                break
            
            #c = clip.subclipped(p[0],p[1])
            c = clip.subclipcopy(p[0],p[1])
            print(self.dirname, names)
            if names == None:
                file = TMPFILENAME+"--"+str(name)+".mp4"
            else:
                print(self.dirname, names[i])
                file = os.path.join(self.dirname, names[i])
            #c.write_videofile(file, threads = 8, fps=24)
            print(file)
            c.write(file,'slow')
            self.tracker[name-1] = 1
            ret.append(file)
            print("***PRINT***",file)
            name +=1
        
        return ret
    '''
    def writeSubClip(video_path, start, end, outputFile):

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            "%0.2f" % start,
            "-i",
            video_path,
            "-t",
            "%0.2f" % (end - start),
            "-map",
            "0",
            "-vf scale=64"
            
            ffmpeg_escape_filename(outputFile),
        ]

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while merging video and subtitles: {e}")
    '''
class MergeVideos:
    def __init__(self):
        self.pointer = {}
        self.clips = []
        self.tmpOutDir = "./tmp"
    def videoFillDisect(self,start: float, time: float, video: str):
        path = video.path
        duration = video.end-video.start
        print("disecting, time:",time,"start:",start)
        #originalClip = moviepy.VideoFileClip(path)
        originalClip = MovieClips(path)
        timeLeft = start+time - duration
        #tmpClip = originalClip.subclipped(start, min(duration, start+time))
        tmpClip = originalClip.subclipcopy(start, min(duration, start+time))
        if timeLeft < 0:
            timeLeft = -1
        print("****FILL DISECTING****")
        print(path, tmpClip.duration)
        return tmpClip, timeLeft
    
    def videoFillDisectFfm(self,start: float, time: float, path: str, index:str):
        print("disecting through ffmpeg, time:",time,"start:",start)
        originalClip = moviepy.VideoFileClip(path)
        duration = originalClip.duration
        timeLeft = start+time - duration
        outClipPath = os.join(self.tmpOutDir, (index+".mp4"))
        videoTools.ffmpeg_extract_subclip(path, start, min(start+time,duration), outClipPath)
        
        if timeLeft < 0:
            timeLeft = -1
        print("****FILL DISECTING****")
        print(path, outClipPath)
        return outClipPath, timeLeft
    
    def videoDisect(self,start: float, time: float, video: str):
        path = video.path
        duration = video.end-video.start
        print("disecting, time:",time,"start:",start)
        if duration < start + time:
            print("video Too Short!")
            return -1
        originalClip = MovieClips(path)
        tmpClip = originalClip.subclipcopy(start, start+time)
        print("****DISECTING****")
        print(path, tmpClip.duration)
        return tmpClip

    def videoDisectFfm(self,start: float, time: float, path: str, index: str):
        print("disecting through ffm, time:",time,"start:",start)
        originalClip = moviepy.VideoFileClip(path)
        duration = originalClip.duration
        if duration < start + time:
            print("video Too Short!")
            originalClip.close()
            return -1
        #tmpClip = originalClip.subclipped(start, start+time)
        outClipPath = os.join(self.tmpOutDir, (index+".mp4"))
        videoTools.ffmpeg_extract_subclip(path, start, start+time, outClipPath)

        print("****DISECTING****")
        print(path, outClipPath)
        return outClipPath

    def videoAdd(self, videos, duration, path):
        print("adding")
        count = 0
        while count < 2:
            for video in videos:
                v = video.path
                start = 0
                if v in self.pointer:
                    start = self.pointer[v]
                #clip = self.videoDisect(start,duration,v)
                clip = self.videoDisect(start,duration,video)
                if not clip == -1:
                    self.clips.append(clip)
                    self.pointer[v] = start + duration
                    return
                else:
                    self.pointer[v] = 0
            count += 1
        
        while True:
            for video in videos:
                v = video.path
                print("****FILL DISECTING****")
                start = 0
                if v in self.pointer:
                    start = self.pointer[v]
                clip, timeLeft = self.videoFillDisect(start, duration, video)
                self.clips.append(clip)
                if timeLeft == -1:
                    self.pointer[v] = start + duration
                    return
                else:
                    duration = timeLeft
    
    def videoAddFfm(self, videos, duration, path, index):
        print("adding")
        count = 0
        while count < 2:
            for v in videos:
                start = 0
                if v in self.pointer:
                    start = self.pointer[v]
                #clip = self.videoDisect(start,duration,v)
                clip = self.videoDisectFfm(start,duration,v,str(index))
                if not clip == -1:
                    self.clips.append(clip)
                    self.pointer[v] = start + duration
                    return index+1
                else:
                    self.pointer[v] = 0
            count += 1
        
        while True:
            for v in videos:
                print("****FILL DISECTING****")
                start = 0
                if v in self.pointer:
                    start = self.pointer[v]
                clip, timeLeft = self.videoFillDisectFfm(start, duration, v, str(index))
                index += 1
                self.clips.append(clip)
                if timeLeft == -1:
                    self.pointer[v] = start + duration
                    return index
                else:
                    duration = timeLeft


            
        # merging video clips
    def videoConcat(self, finalPath = "./final.mp4"):
        print("concating")
        final_clip = concat(self.clips, outputFile=finalPath)
        #final_clip = moviepy.concatenate_videoclips(self.clips)
        '''for clip in self.clips:
            clip.close()'''
        print("***FINAL CLIP***", final_clip.duration)
        return final_clip

    def videoConcatFfm(self):
        print("concating")
        final_clip = moviepy.concatenate_videoclips(self.clips)
        for clip in self.clips:
            clip.close()
        print("***FINAL CLIP***", final_clip.duration)
        return final_clip

    def mergeAudio(self, mp3Paths, path):
        print("merging audio")
        mp3s = []
        for mp3Path in mp3Paths:
            mp3 = moviepy.AudioFileClip(mp3Path)
            mp3s.append(mp3)
            mp3s.append(moviepy.AudioClip(lambda t: 0, duration=0.5))
        final_mp3 = moviepy.concatenate_audioclips(mp3s)
        print("****AUDIO****", final_mp3.duration)
        final_mp3.write_audiofile("./final.mp3")
        return "./final.mp3"
    def mergeAll(self, final_clip:MovieClips, final_mp3, srt, path, finalPath):
        print("merging all")
        #final_audio_video_clip = final_clip.with_audio(final_mp3)
        final_clip.addAudio(final_mp3)
        print("****FINAL AUD/VID CLIP****", final_clip.duration)
        final_clip.write(path, preset = 'fast')
        srt2video.merge_video_and_subtitle_paths(path,srt, finalPath)

    

 
if __name__ == '__main__':
    edit = VideoEdit("https://shanghai-bgm-vioce.oss-cn-shanghai.aliyuncs.com/c79afb98-a381-45c8-9808-c23c4d43e1f9_preview.mp4"
                     ,[(0,35),(35,47),(47,87)],"./clips")
    ret = edit.divideVideo()
    print(ret)
    
    