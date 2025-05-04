import json
import os
import re
import time
import base64
import dashscope
#from dashscope.audio.tts_v2 import SpeechSynthesizer
from speechify import Speechify
from dotenv import load_dotenv

import traceback

def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def split_into_sentences(text):
    # 中文标点符号列表
    punctuation = ['，', '。', '；', '？', '！', '.',',',';','?',"!"]
    brackets = {'(': ')', '[': ']', '{': '}', '（': '）', '【': '】', '《': '》'}
    
    # 初始化结果列表和临时句子存储
    sentences = []
    temp_sentence = ''
    bracket_stack = []
    
    # 遍历文本中的每一个字符
    for char in text:
        # 如果是左括号，压入栈
        if char in brackets:
            bracket_stack.append(char)
        # 如果是右括号且与栈顶匹配，弹出栈
        elif char in brackets.values() and bracket_stack and brackets[bracket_stack[-1]] == char:
            bracket_stack.pop()
        
        # 如果字符是中文标点之一且括号栈为空，表示句子结束
        if char in punctuation and not bracket_stack:
            # 添加临时句子到结果列表，并清空临时句子
            sentences.append(temp_sentence.strip())
            temp_sentence = ''
        else:
            # 否则，将字符添加到临时句子中
            temp_sentence += char
    
    # 处理最后一个可能没有标点结尾的句子
    if temp_sentence:
        sentences.append(temp_sentence.strip())
    
    return sentences


def save_sentences_to_markdown(sentences, base_dir, index1):
    for index2, sentence in enumerate(sentences, start=1):
        # 创建目录
        dir_name = f'audio_for_paragraph_{index1}'
        dir_path = os.path.join(base_dir, dir_name)
        os.makedirs(dir_path, exist_ok=True)
        
        # 构建文件名
        file_name = f'paragraph_{index1}_sentence_{index2}.md'
        file_path = os.path.join(dir_path, file_name)
        
        # 写入Markdown文件
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(sentence + '\n')


def process_json_file(json_file_path, base_dir):
    
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    file_prefix = os.path.splitext(os.path.basename(json_file_path))[0]
    
    base_dir = os.path.join(base_dir, file_prefix)

    # 读取JSON文件
    json_data = read_json_file(json_file_path)
    
    sentencesAll = []

    # 处理JSON数据中的每个条目
    for index1, item in enumerate(json_data):
        if 'content' in item:
            content = item['content']
            
            # 检查content是否为链接
            if not is_url(content):
                sentences = split_into_sentences(content)
                sentences.append(item['title'])
                sentencesAll.append(sentences)
                save_sentences_to_markdown(sentences, base_dir, index1+1)
    return sentencesAll
            

def is_url(s):
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    return bool(url_pattern.match(s))

'''
def synthesize_md_to_speech(base_directory):
    """
    识别指定目录下的所有.md文件，读取其内容并使用DashScope API将其转换为语音，
    保存为同名.mp3文件在同一目录下。

    参数:
    base_directory (str): 包含.md文件的顶层目录路径。
    """
    # 确保环境变量中存在DashScope API密钥
    if 'DASHSCOPE_API_KEY' not in os.environ:
        raise ValueError("DashScope API key must be set in the environment variables.")
    mp3Paths = []
    
    # 遍历指定目录及其子目录
    for root, dirs, files in os.walk(base_directory):
        for file in files:
            if file.endswith('.md'):
                # 构建完整文件路径
                md_file_path = os.path.join(root, file)
                
                # 读取.md文件内容
                with open(md_file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # 初始化语音合成器
                #speech_synthesizer = SpeechSynthesizer(model='cosyvoice-v1', voice='longxiaochun')

                
                # 合成语音
                print("audio text:",text)
                #audio_data = speech_synthesizer.call(text)
                
                # 构建输出.mp3文件路径
                mp3_file_path = os.path.splitext(md_file_path)[0] + '.mp3'
                mp3Paths.append(mp3_file_path)
                # 保存音频到文件
                with open(mp3_file_path, 'wb') as f:
                    f.write(audio_data)
                
                print(f'Synthesized text from file "{md_file_path}" to file: {mp3_file_path}')
'''

def synthesize_sentences_to_speech(base_directory, paragraphs):
    """
    识别指定目录下的所有.md文件，读取其内容并使用DashScope API将其转换为语音，
    保存为同名.mp3文件在同一目录下。

    参数:
    base_directory (str): 包含.md文件的顶层目录路径。
    """
    # 确保环境变量中存在DashScope API密钥
    #if 'DASHSCOPE_API_KEY' not in os.environ:
        #raise ValueError("DashScope API key must be set in the environment variables.")
    if not os.path.exists(base_directory):
        os.makedirs(base_directory)
    mp3Paths = []
    
    # 遍历指定目录及其子目录
    for indexParagraph in range(len(paragraphs)):
        sentences = paragraphs[indexParagraph]
        print(f"----paragraph {indexParagraph+1}: ", sentences)
        for indexSentence in range(len(sentences)-1):
            text = sentences[indexSentence]
            
            # 初始化语音合成器
            #speech_synthesizer = SpeechSynthesizer(model='cosyvoice-v1', voice='longxiaochun')

            client = Speechify()
            # 合成语音
            print("audio text:",text)
            audio_response = client.tts.audio.speech(input = text, voice_id="henry", audio_format="mp3")
            audio_data = audio_response.audio_data.encode()
            content = base64.b64decode(audio_data)
            #audio_data = speech_synthesizer.call(text)
            
            #set up directory name
            #audio_for_paragraph_{indexParagraph+1}/
            subpath = f"paragraph_{indexParagraph+1}_sentence_{indexSentence+1}.mp3"
            mp3_file_path = os.path.join(base_directory,subpath)
            mp3Paths.append(mp3_file_path)
            # 保存音频到文件
            with open(mp3_file_path, 'wb') as f:
                f.write(content)
            
            print(f'Synthesized paragraph {indexParagraph} sentence {indexSentence} to file: {mp3_file_path}')
    return mp3Paths


if __name__ == "__main__":
    synthesize_sentences_to_speech(".",[["hello world","this is a test"],["hello world","this is a test"]])