import subprocess
import os
def merge_video_and_subtitle(video_and_srt_path, base_name):
    video_ext = ".mp4"
    srt_ext = ".srt"

    video_path = os.path.join(video_and_srt_path, f"{base_name}_with_audio" + video_ext).replace("\\", "/")
    srt_path = os.path.join(video_and_srt_path, base_name + srt_ext).replace("\\", "/")
    output_path = os.path.join(video_and_srt_path, f"{base_name}_with_audio_with_subs" + video_ext).replace("\\", "/")

    command = [
        'ffmpeg',
        '-i', video_path,
        '-vf', f'subtitles={srt_path}',
        '-c:a', 'copy',
        output_path
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while merging video and subtitles: {e}")

def merge_video_and_subtitle_paths(video_path, srt_path,target_path):

    command = [
        'ffmpeg',
        '-y',
        '-hwaccel', 'cuda',
        '-i', video_path, 
        '-vf', f"subtitles={srt_path}:force_style='Fontname=Roboto,OutlineColour=&H40000000,BorderStyle=3'",
        
        '-c:a', 'copy', '-c:v', 'h264_nvenc',
        '-metadata:s:s:0', 'language=zh',
        '-preset', 'fast',
        '-threads', '8',
        target_path
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while merging video and subtitles: {e}")