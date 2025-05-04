import os
import re
from moviepy.audio.io import AudioFileClip
from typing import List

def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"

# 定义一个函数来获取音频文件的时长
def get_audio_duration(file_path):
    audio = AudioFileClip.AudioFileClip(file_path)
    duration = audio.duration
    audio.close()
    return duration

# 定义一个函数来生成SRT格式的字幕行
def create_srt_line(index, start_time, end_time, text):
    return f"{index}\n{start_time} --> {end_time}\n{text}\n\n"

def generate_srt_from_audio(base_dir: str, output_dir: str, output_srt_file: str) -> None:
    """
    从指定目录下的音频文件夹生成SRT字幕文件。

    :param base_dir: 包含音频文件夹的根目录。
    :param output_dir: 输出SRT文件的目录。
    :param output_srt_file: 输出SRT文件的完整路径。
    """

    # 创建输出目录，如果它不存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 确保输出文件名有.srt后缀
    if not output_srt_file.endswith('.srt'):
        output_srt_file += '.srt'
    

    # 初始化当前时间
    current_time = 0  # 初始时间

    # 打开SRT文件进行写入
    with open(output_srt_file, 'w', encoding='utf-8') as srt_file:
        srt_index = 1

        # 获取所有符合条件的子目录，并按索引排序
        sub_dirs = [d for d in os.listdir(base_dir) if d.startswith('audio_for_paragraph_')]
        sub_dirs.sort(key=lambda x: int(re.search(r'\d+', x).group()))

        # 遍历所有子目录
        for sub_dir in sub_dirs:
            sub_dir_path = os.path.join(base_dir, sub_dir)

            # 查找所有的.md和.mp3文件
            files = [f for f in os.listdir(sub_dir_path) if f.endswith('.md') or f.endswith('.mp3')]
            md_files = [f for f in files if f.endswith('.md')]

            # 按照index1和index2排序.md文件
            md_files.sort(key=lambda x: (int(x.split('_')[1]), int(x.split('_')[3].split('.')[0])))

            # 处理每个.md文件
            for md_file in md_files:
                md_file_path = os.path.join(sub_dir_path, md_file)
                mp3_file_path = os.path.splitext(md_file_path)[0] + '.mp3'

                # 确保对应的.mp3文件存在
                if os.path.exists(mp3_file_path):
                    # 读取.md文件内容
                    with open(md_file_path, 'r', encoding='utf-8') as f:
                        text = f.read().strip()

                    # 获取.mp3文件时长
                    duration = get_audio_duration(mp3_file_path)

                    # 生成SRT格式的字幕行
                    start_time_str = format_time(current_time)
                    end_time_str = format_time(current_time + duration)
                    srt_line = create_srt_line(srt_index, start_time_str, end_time_str, text)

                    # 写入SRT文件
                    srt_file.write(srt_line)

                    # 更新当前时间
                    current_time += duration + 0.5  # 加上0.5秒以避免时间重叠

                    srt_index += 1
                else:
                    print(f"No corresponding MP3 file found for {md_file}")

    print("SRT file generated successfully.")


def generate_srt_from_arrays(mp3Paths: list, paragraphs: list,output_dir:str , output_srt_file: str) -> list:
    """
    从指定目录下的音频文件夹生成SRT字幕文件。

    :param mp3Paths: 音频文件的列表
    :param paragraphs: 分成段落的句子列表
    :param output_dir: 输出SRT文件的目录。
    :param output_srt_file: 输出SRT文件的完整路径。
    """

    # 创建输出目录，如果它不存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 确保输出文件名有.srt后缀
    if not output_srt_file.endswith('.srt'):
        output_srt_file += '.srt'
    

    # 初始化当前时间
    current_time = 0  # 初始时间

    # 打开SRT文件进行写入
    with open(output_srt_file, 'w', encoding='utf-8') as srt_file:
        srt_index = 1
        i = 0
        for paragraph in paragraphs:
            for index in range(len(paragraph)-1):
                sentence = paragraph[index]
                mp3Path = mp3Paths[i]
                i += 1
                duration = get_audio_duration(mp3Path)
                start_time_str = format_time(current_time)
                end_time_str = format_time(current_time + duration)
                srt_line = create_srt_line(srt_index, start_time_str, end_time_str, sentence)
                srt_file.write(srt_line)
                current_time += duration + 0.5  # 加上0.5秒以避免时间重叠
                srt_index += 1

    print("SRT file generated successfully.")
    return (output_srt_file)