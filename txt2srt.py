import re
from datetime import timedelta
import math
import os

def split_text_into_sentences(text):
    # 使用正则表达式匹配句末的标点符号或换行符来分割文本
    sentences = re.split(r'[\。\？\！\，\n]', text)
    # 过滤掉空字符串
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def generate_srt_content(sentences, start_time=0):
    srt_content = []
    duration_per_four_chinese_chars = 0.7   # 每四个汉字持续0.7秒
    duration_per_other_char = 0.2           # 每个其他字符持续0.2秒
    
    current_time = start_time
    for index, sentence in enumerate(sentences, start=1):
        chinese_char_count = len(re.findall(r'[\u4e00-\u9fa5]', sentence))

        other_char_count = len(sentence) - chinese_char_count
        
        # 确保汉字的总持续时间按每四个汉字0.7秒计算
        total_chinese_duration = math.ceil(chinese_char_count / 4) * duration_per_four_chinese_chars
        # 计算非汉字字符的总持续时间
        total_other_duration = other_char_count * duration_per_other_char
        
        # 总持续时间
        total_duration = total_chinese_duration + total_other_duration
        
        # 确保总持续时间不会导致时间过长（例如超过1分钟）
        if total_duration > 60:
            total_duration = 60
        
        # 获取总秒数
        total_seconds_start = current_time
        total_seconds_end = min(current_time + total_duration, current_time + 60)

        # 分离秒和毫秒
        start_seconds = int(total_seconds_start)
        start_milliseconds = int((total_seconds_start - start_seconds) * 1000)
        end_seconds = int(total_seconds_end)
        end_milliseconds = int((total_seconds_end - end_seconds) * 1000)

        # 计算开始时间的小时、分钟、秒和毫秒
        hours, remainder = divmod(start_seconds, 3600)  # 一小时有3600秒
        minutes, seconds = divmod(remainder, 60)
        milliseconds = start_milliseconds

        start = '{:02d}:{:02d}:{:02d},{:03d}'.format(hours, minutes, seconds, milliseconds)

        # 计算结束时间的小时、分钟、秒和毫秒
        hours, remainder = divmod(end_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = end_milliseconds

        end = '{:02d}:{:02d}:{:02d},{:03d}'.format(hours, minutes, seconds, milliseconds)
 
        # 构建SRT格式的单条记录
        srt_line = f"{index}\n{start} --> {end}\n{sentence}\n"
        srt_content.append(srt_line)
        
        # 更新当前时间以供下一句使用
        current_time += total_duration
    
    return srt_content




def txt_to_srt(txt_file_path, output_srt_file_path):
    """
    将TXT文件转换为SRT字幕文件。

    :param txt_file_path: 输入TXT文件的路径
    :param output_srt_file_path: 输出SRT文件的路径
    :param start_time: 字幕开始的时间（秒），默认为2秒
    """
    with open(txt_file_path, 'r', encoding='utf-8') as file:
        text = file.read()

    sentences = split_text_into_sentences(text)
    srt_content = generate_srt_content(sentences, start_time=2)

    srt_content_str = '\n'.join(srt_content)

    file_name = 'output_with_audio.srt'


    with open(os.path.join(output_srt_file_path, file_name), 'w', encoding='utf-8') as file:
        file.write(srt_content_str)

    print("SRT文件已生成。")