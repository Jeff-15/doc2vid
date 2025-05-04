import os
from pydub import AudioSegment
from moviepy import AudioFileClip

def calculate_audio_durations(directory):
    """
    计算指定目录下所有以 audio_for_paragraph_{index} 命名的文件夹中 mp3 文件的总持续时间（以秒为单位）。
    
    参数:
        directory (str): 需要扫描的根目录路径。

    返回:
        list: 每个 audio_for_paragraph_{index} 文件夹中 mp3 文件总持续时间（秒）的列表。
    """
    # 初始化结果列表
    durations = []
    
    # 遍历目录下的所有子目录
    for entry in os.scandir(directory):
        if entry.is_dir() and entry.name.startswith("audio_for_paragraph_"):
            # 提取 index
            index = int(entry.name.split("_")[-1])
            
            # 初始化当前文件夹的总持续时间为0
            total_duration_ms = 0
            
            # 遍历子目录中的所有文件
            for file_entry in os.scandir(entry.path):
                if file_entry.name.endswith(".mp3"):
                    # 加载 mp3 文件并计算持续时间
                    audio = AudioSegment.from_mp3(file_entry.path)
                    delay = 300
                    total_duration_ms += len(audio) + delay
            
            # 将当前文件夹的总持续时间转换为秒，并添加到结果列表中
            total_duration_seconds = total_duration_ms / 1000.0
            durations.append((index, total_duration_seconds))
    
    # 按照 index 排序结果列表
    durations.sort(key=lambda x: x[0])


    
    # 只保留持续时间（秒）
    durations = [duration for _, duration in durations]

    durations.insert(0, 2)
    
    return durations

def calculate_sentence_audio_durations(directory,mp3Paths):
    """
    计算指定目录下所有以 audio_for_paragraph_{index} 命名的文件夹中 mp3 文件的总持续时间（以秒为单位）。
    
    参数:
        directory (str): 需要扫描的根目录路径。

    返回:
        list: 每个 audio_for_paragraph_{index} 文件夹中 mp3 文件总持续时间（秒）的列表。
    """
    # 初始化结果列表
    durations = []
    
    # 遍历目录下的所有子目录
    print(len(mp3Paths))
    for mp3Path in mp3Paths:
            # 加载 mp3 文件并计算持续时间
        audio = AudioFileClip(mp3Path)
        duration = audio.duration
        durations.append(duration)

    
    return durations