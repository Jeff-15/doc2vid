import subprocess
import json
import os
TMPDIR = os.getenv("TMP_VID_DIR","./tmp/")
class MovieClips:
    #class for clips
    def probe(self):
        command = ['ffprobe', '-v', 'error', '-select_streams','v', '-show_entries','stream=duration,width,height,r_frame_rate','-of', 'json', self.fileName]
        result = subprocess.run(command, stdout=subprocess.PIPE, text=True)
        result = json.loads(result.stdout)
        resultDict = result["streams"][0]
        self.duration = float(resultDict["duration"])
        self.height = float(resultDict["height"])
        self.width = float(resultDict["width"])
        fpsDiv = resultDict["r_frame_rate"].split("/")
        self.fps = float(fpsDiv[0])/float(fpsDiv[1])
    def __init__(self, fileName:str):
        self.fileName = fileName
        self.probe()
        self.start = 0
        self.end = self.duration
        self.audio = None
        print(self.fileName, self.height, self.width)
    def resize(self, width, height):
        self.height = height
        self.width = width
    def setFps(self, fps):
        self.fps = fps
    def addAudio(self, audioFilePath):
        self.audio = audioFilePath
    def subclipcopy(self, start, end):
        subclip = MovieClips(self.fileName)
        subclip.start = start
        subclip.end = end
        subclip.duration = end - start
        subclip.height = self.height
        subclip.width = self.width
        subclip.fps = self.fps
        return subclip
    def write(self, outputFile, preset = 'medium'):
        cmd = ['ffmpeg', '-y',
                '-hwaccel', 'cuda',
                '-i', self.fileName,
                '-vf', f'scale={self.width}:{self.height}',
                '-r', str(self.fps),
                '-c:v', 'h264_nvenc' ,'-preset', preset ,
                '-threads', '16',
                '-ss',str(self.start),
                '-to',str(self.end),
                outputFile]
        audioCmd = ['ffmpeg', '-y',
                '-hwaccel', 'cuda',
                '-i', self.fileName,
                '-i', self.audio,
                '-map', '0:v',
                '-map', '1:a',
                '-shortest', 
                '-vf', f'scale={self.width}:{self.height}',
                '-r', str(self.fps),
                '-c:v', 'h264_nvenc' ,'-preset', preset ,
                '-threads', '16',
                '-ss',str(self.start),
                '-to',str(self.end),
                outputFile]
        if self.audio == None:
            result = subprocess.run(cmd)
        else:
            result = subprocess.run(audioCmd)
        print(result)

# Clips must have same fps, encoding and size!
def concat(clipList:list[MovieClips], outputFile, tmpDir = TMPDIR):
    concatFile = open("concat.txt", 'w')
    for i in range(len(clipList)):
        clip = clipList[i]
        outName = f"{i}.mp4"
        outName = os.path.join(tmpDir,outName)
        concatFile.write(f"file \'{outName}\'\n")
        clip.write(outName, 'fast')
    concatFile.close()
    cmd = ['ffmpeg','-y','-f','concat', '-safe', '0',
                '-hwaccel', 'cuda',
                '-i', 'concat.txt',
                '-c:v', 'h264_nvenc' ,'-preset', 'fast' ,
                '-threads', '16',
                outputFile]
    print(cmd)
    result = subprocess.run(cmd)
    final = MovieClips(outputFile)
    return final



'''
mc = MovieClips("video.mp4")
mc.resize(640, 360)
mcc1 = mc.subclipcopy(0, 10)
mcc2 = mc.subclipcopy(10,54)
mm = concat([mcc1, mcc2],'./tmp/','./final.mp4')
mm.addAudio("rattlesnake_song.mp3")
mm.write("./concatAudio.mp4",'fast')
'''