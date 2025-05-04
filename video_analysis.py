from alibabacloud_tea_openapi_sse.client import Client as OpenApiClient
from alibabacloud_tea_openapi_sse import models as open_api_models
from alibabacloud_tea_openapi import models as open_models
from alibabacloud_tea_util_sse import models as util_models
from alibabacloud_quanmiaolightapp20240801.client import Client as QuanMiaoLightApp20240801Client
from alibabacloud_quanmiaolightapp20240801 import models as quan_miao_light_app_20240801_models
import asyncio
import json
import re  # 新增用于正则验证的模块
import pprint
from google import genai
import typing_extensions as typing
from urllib.request import urlretrieve
import time
import keys
from datetime import datetime
class LightApp:
    def __init__(self) -> None:
        # 工程代码泄露可能会导致 AccessKey 泄露，并威胁账号下所有资源的安全性。以下代码示例仅供参考。
        # 建议使用更安全的 STS 方式，更多鉴权访问方式请参见：https://help.aliyun.com/document_detail/378659.html。
        self.access_key_id = keys.access_key_id
        self.access_key_secret = keys.access_key_secret
        self.workspace_id = keys.workspace_id
        # 以上字段请改成实际的值。
        self.endpoint = 'quanmiaolightapp.cn-beijing.aliyuncs.com'
        self._client = None
        self._api_info = self._create_api_info()
        self._runtime = util_models.RuntimeOptions(read_timeout=1000 * 100)
        self._client = self._create_client(self.access_key_id, self.access_key_secret, self.endpoint)
        self._async_client = self._create_async_client(self.access_key_id,self.access_key_secret,self.endpoint)
        self.gclient = genai.Client(api_key=keys.gemini_key)
        generation_config = {
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }

        

    def _create_client(
            self,
            access_key_id: str,
            access_key_secret: str,
            endpoint: str,
    ) -> OpenApiClient:
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint=endpoint
        )
        return OpenApiClient(config)

    def _create_async_client(
            self,
            access_key_id: str,
            access_key_secret: str,
            endpoint: str,
    ) -> QuanMiaoLightApp20240801Client:
        config = open_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint=endpoint,
        )
        return QuanMiaoLightApp20240801Client(config)

    def _create_api_info(self) -> open_api_models.Params:
        """
        API 相关
        @param path: params
        @return: OpenApi.Params
        """
        params = open_api_models.Params(
            # 接口名称
            action='RunVideoAnalysis',
            # 接口版本
            version='2024-08-01',
            # 接口协议
            protocol='HTTPS',
            # 接口 HTTP 方法
            method='POST',
            auth_type='AK',
            style='RPC',
            # 接口 PATH,
            pathname='/'+self.workspace_id+'/quanmiao/lightapp/runVideoAnalysis',
            # 接口请求体内容格式,
            req_body_type='formData',
            # 接口响应体内容格式,
            body_type='sse'
        )
        return params
    
    async def do_paragraph_gemini_query(self, txt):
        prompt = f"""Divide the following text into short segments according to contents.
                    include a summarized segment title and its content for each segment.
                    Further divide each segment into a list of independent or dependent clauses.
                    Such as those separated by commas, semicolons, and conjunctions.
                    The content of segments must not be altered from the original below, no addition or deletion. 
                    The conjunctions must be preserved, just like every other word in the original text.
                    The conjunctions would be part of the clause that come after it. 
                    The original text is below:\n
                    {txt}"""
        print(prompt)
        class segement(typing.TypedDict):
            title: str
            content: str
            clauses: list[str]
        class paragraph(typing.TypedDict):
            segements: list[segement]
        result = self.gclient.models.generate_content(
            model="gemini-1.5-flash",
            contents=[prompt],
            config={
                "response_mime_type":"application/json", "response_schema": paragraph, "temperature": 0
            },
        )
        return result

    async def do_gemini_query(self,url):
        video_file = self.gclient.files.upload(file=url)
        while video_file.state.name == "PROCESSING":
            print('.', end='')
            time.sleep(10)
            video_file = self.gclient.files.get(name = video_file.name)
        print(f"Completed upload: {video_file.uri}")
        if video_file.state.name == "FAILED":
            raise ValueError(video_file.state.name)
        prompt = """ Please generate a short title for this video. 
                     Please segment the following video by themes, plots and events 
                     and for each segement, generate the following: 
                     generate a brief theme, 
                     generate a detailed summary and analysis of the content of this segement
                     record start/end time in minute:second format"""
        class segment(typing.TypedDict):
            theme: str
            summary: str
            start: str
            end: str
        class video(typing.TypedDict):
            title: str
            segments: list[segment]
        result = self.gclient.models.generate_content(
            model="gemini-1.5-flash",
            contents=[video_file, prompt],
            config={
                "response_mime_type":"application/json", "response_schema": video, "temperature": 0
            },
        )
        return result
    
    def gemini_embedding(self, txt):
        result = self.gclient.models.embed_content(
            model="text-embedding-004",
            contents=txt,
            config={"task_type": "RETRIEVAL_DOCUMENT"}
        )
        return result
    

    async def do_sse_query(self, url, extrainfo):
        body = {
            'videoExtraInfo': extrainfo,
            'videoUrl': url,
            'videoModelId': "qwen-vl-max-latest",
            'videoModelCustomPromptTemplate': "# 角色\n你是一名视频分析师，擅长对各种视频片段进行理解。\n\n# 任务描述\n给你一个视频片段的多张关键帧图片，请你完成以下任务。\n- 输出每张图片的画面信息，包括人物、物体、动作、文字、字幕、镜头语言、一句话总结等。\n- 把每张图片的信息串联起来，生成视频的详细概述，还原该片段的剧情。\n\n# 限制\n- 分析范围严格限定于提供的视频子片段，不涉及视频之外的任何推测或背景信息。\n- 总结时需严格依据视频内容，不可添加个人臆测或创意性内容。\n- 保持对所有视频元素（尤其是文字和字幕）的高保真还原，避免信息遗漏或误解。\n\n# 输入数据\n## 视频片段ASR信息  (如果输入为空则忽略ASR信息)\n{videoAsrText}\n\n## 视频补充信息 (可能对你理解该片段有帮助，如果输入为空则忽略补充信息)\n{videoExtraInfo}\n\n# 输出格式\n直接按照任务目标里即可，先输出每张图片的描述，再串联起来输出整个视频片段的剧情。",
            'modelId': "qwen-max-latest",
            'modelCustomPromptTemplate': "# 角色\n你是一个专业的视频结构解析大师，擅长结合视频镜头信息来生成一个简洁清晰完整明了的视频结构大纲。\n\n# 任务目标\n为了从大量输入数据中梳理出视频内容的结构，请你完成以下2个任务：\n1、标题总结。\n为视频生成一个标题\n- title：视频的标题。\n2、大纲总结。\n- abstract：为视频总结一个大纲，大纲要高度概括视频，覆盖从开始到结束的各个阶段。每个阶段包括阶段主题和阶段细节。\n- theme：用一句话来概括该阶段的内容。\n- details：用key-value来展示该阶段的细节内容，数量根据实际内容多少来看，可以是1个、2个或3个。\n- content：该阶段的具体内容 \n- start：记录该阶段细节开始的时间点（秒）\n- end：记录该阶段细节结束的时间点（秒）\n\n# 输入数据\n## 资料一：视频分镜信息 (视频各镜头的视觉描述信息)\n{videoAnalysisText}\n\n## 资料二：视频ASR转录信息 (未标注出说话者，可能有错误和遗漏，如果没有输入ASR，则忽略此信息)\n{videoAsrText}\n\n## 资料三：视频补充信息 (如果输入为空则忽略补充信息)\n{videoExtraInfo}\n\n# 输出格式\n以以下json格式输出：\n{\"title\":\"\", \"abstract\": [{\"theme\": \"\", \"details\": {\"content\": \"\", \"start\": \"\", \"end\":\"\"}}]}",
            'generateOptions': ["videoAnalysis", "videoGenerate", "videoCaption", "videoMindMappingGenerate", "videoTitleGenerate"]
        }
        request = open_api_models.OpenApiRequest(
            body=body
        )
        sse_receiver = self._client.call_sse_api_async(params=self._api_info, request=request, runtime=self._runtime)
        return sse_receiver
    
    async def do_async_sse_query(self, url, extrainfo):
        body = {
            'videoExtraInfo': extrainfo,
            'videoUrl': url,
            'videoModelId': "qwen-vl-max-latest",
            'videoModelCustomPromptTemplate': "# 角色\n你是一名视频分析师，擅长对各种视频片段进行理解。\n\n# 任务描述\n给你一个视频片段的多张关键帧图片，请你完成以下任务。\n- 输出每张图片的画面信息，包括人物、物体、动作、文字、字幕、镜头语言、一句话总结等。\n- 把每张图片的信息串联起来，生成视频的详细概述，还原该片段的剧情。\n\n# 限制\n- 分析范围严格限定于提供的视频子片段，不涉及视频之外的任何推测或背景信息。\n- 总结时需严格依据视频内容，不可添加个人臆测或创意性内容。\n- 保持对所有视频元素（尤其是文字和字幕）的高保真还原，避免信息遗漏或误解。\n\n# 输入数据\n## 视频片段ASR信息  (如果输入为空则忽略ASR信息)\n{videoAsrText}\n\n## 视频补充信息 (可能对你理解该片段有帮助，如果输入为空则忽略补充信息)\n{videoExtraInfo}\n\n# 输出格式\n直接按照任务目标里即可，先输出每张图片的描述，再串联起来输出整个视频片段的剧情。",
            'modelId': "qwen-max-latest",
            'modelCustomPromptTemplate': "# 角色\n你是一个专业的视频结构解析大师，擅长结合视频镜头信息来生成一个简洁清晰完整明了的视频结构大纲。\n\n# 任务目标\n为了从大量输入数据中梳理出视频内容的结构，请你完成以下2个任务：\n1、标题总结。\n为视频生成一个标题\n- title：视频的标题。\n2、大纲总结。\n- abstract：为视频总结一个大纲，大纲要高度概括视频，覆盖从开始到结束的各个阶段。每个阶段包括阶段主题和阶段细节。\n- theme：用一句话来概括该阶段的内容。\n- details：用key-value来展示该阶段的细节内容，数量根据实际内容多少来看，可以是1个、2个或3个。\n- content：该阶段的具体内容 \n- start：记录该阶段细节开始的时间点（秒）\n- end：记录该阶段细节结束的时间点（秒）\n\n# 输入数据\n## 资料一：视频分镜信息 (视频各镜头的视觉描述信息)\n{videoAnalysisText}\n\n## 资料二：视频ASR转录信息 (未标注出说话者，可能有错误和遗漏，如果没有输入ASR，则忽略此信息)\n{videoAsrText}\n\n## 资料三：视频补充信息 (如果输入为空则忽略补充信息)\n{videoExtraInfo}\n\n# 输出格式\n以以下json格式输出：\n{\"title\":\"\", \"abstract\": [{\"theme\": \"\", \"details\": {\"content\": \"\", \"start\": \"\", \"end\":\"\"}}]}",
            'generateOptions': ["videoAnalysis", "videoGenerate", "videoCaption", "videoMindMappingGenerate", "videoTitleGenerate"]
        }
        request = quan_miao_light_app_20240801_models.SubmitVideoAnalysisTaskRequest(video_extra_info=extrainfo,\
            video_url= url,\
            video_model_id = "qwen-vl-max-latest",\
            video_model_custom_prompt_template= "# 角色\n你是一名视频分析师，擅长对各种视频片段进行理解。\n\n# 任务描述\n给你一个视频片段的多张关键帧图片，请你完成以下任务。\n- 输出每张图片的画面信息，包括人物、物体、动作、文字、字幕、镜头语言、一句话总结等。\n- 把每张图片的信息串联起来，生成视频的详细概述，还原该片段的剧情。\n\n# 限制\n- 分析范围严格限定于提供的视频子片段，不涉及视频之外的任何推测或背景信息。\n- 总结时需严格依据视频内容，不可添加个人臆测或创意性内容。\n- 保持对所有视频元素（尤其是文字和字幕）的高保真还原，避免信息遗漏或误解。\n\n# 输入数据\n## 视频片段ASR信息  (如果输入为空则忽略ASR信息)\n{videoAsrText}\n\n## 视频补充信息 (可能对你理解该片段有帮助，如果输入为空则忽略补充信息)\n{videoExtraInfo}\n\n# 输出格式\n直接按照任务目标里即可，先输出每张图片的描述，再串联起来输出整个视频片段的剧情。",
            model_id= "qwen-max-latest",
            model_custom_prompt_template= "# 角色\n你是一个专业的视频结构解析大师，擅长结合视频镜头信息来生成一个简洁清晰完整明了的视频结构大纲。\n\n# 任务目标\n为了从大量输入数据中梳理出视频内容的结构，请你完成以下2个任务：\n1、标题总结。\n为视频生成一个标题\n- title：视频的标题。\n2、大纲总结。\n- abstract：为视频总结一个大纲，大纲要高度概括视频，覆盖从开始到结束的各个阶段。每个阶段包括阶段主题和阶段细节。大纲语言为中文\n- theme：用一句话来概括该阶段的内容。\n- details：用key-value来展示该阶段的细节内容，数量根据实际内容多少来看，可以是1个、2个或3个。\n- content：该阶段的具体内容 \n- start：记录该阶段细节开始的时间点（秒）\n- end：记录该阶段细节结束的时间点（秒）\n\n# 输入数据\n## 资料一：视频分镜信息 (视频各镜头的视觉描述信息)\n{videoAnalysisText}\n\n## 资料二：视频ASR转录信息 (未标注出说话者，可能有错误和遗漏，如果没有输入ASR，则忽略此信息)\n{videoAsrText}\n\n## 资料三：视频补充信息 (如果输入为空则忽略补充信息)\n{videoExtraInfo}\n\n# 输出格式\n以以下json格式输出：\n{\"title\":\"\", \"abstract\": [{\"theme\": \"\", \"details\": {\"content\": \"\", \"start\": \"\", \"end\":\"\"}}]}",
            generate_options= ["videoAnalysis", "videoGenerate", "videoCaption", "videoMindMappingGenerate", "videoTitleGenerate"]
        )
        runtime = util_models.RuntimeOptions()
        header = {}
        sse_response = await self._async_client.submit_video_analysis_task_with_options_async(self.workspace_id, request,header,runtime)
        print(sse_response.body.http_status_code)
        if sse_response.body.http_status_code == 200:
            return sse_response.body.data.task_id

    async def retrieve_async_sse_response(self,taskid):
        request = quan_miao_light_app_20240801_models.GetVideoAnalysisTaskRequest(task_id = taskid)
        runtime = util_models.RuntimeOptions()
        header = {}
        try:
            response = self._async_client.get_video_analysis_task_with_options(self.workspace_id, request, header, runtime)
            print(response.body.http_status_code, response.body.message)
            return response, None
        except Exception as e:
            print(e.message)
            return e.code, e.message


    async def do_sse_query2(self, url,prompt, extrainfo = ""):
        body = {
            'videoExtraInfo': extrainfo,
            'videoUrl': url,
            'videoModelId': "qwen-vl-max-latest",
            'videoModelCustomPromptTemplate': "# 角色\n你是一名视频分析师，擅长对各种视频片段进行理解。\n\n# 任务描述\n给你一个视频片段的多张关键帧图片，请你完成以下任务。\n- 输出每张图片的画面信息，包括人物、物体、动作、文字、字幕、镜头语言、一句话总结等。\n- 把每张图片的信息串联起来，生成视频的详细概述，还原该片段的剧情。\n\n# 限制\n- 分析范围严格限定于提供的视频子片段，不涉及视频之外的任何推测或背景信息。\n- 总结时需严格依据视频内容，不可添加个人臆测或创意性内容。\n- 保持对所有视频元素（尤其是文字和字幕）的高保真还原，避免信息遗漏或误解。\n\n# 输入数据\n## 视频片段ASR信息  (如果输入为空则忽略ASR信息)\n{videoAsrText}\n\n## 视频补充信息 (可能对你理解该片段有帮助，如果输入为空则忽略补充信息)\n{videoExtraInfo}\n\n# 输出格式\n直接按照任务目标里即可，先输出每张图片的描述，再串联起来输出整个视频片段的剧情。",
            'modelId': "qwen-max-latest",
            'modelCustomPromptTemplate': "# 角色\n你是一个专业的视频结构解析大师，擅长结合视频镜头信息来生成包含各个镜头信息的视频结构大纲。\n\n# 任务目标\n为了从大量输入数据中梳理出视频内容的结构，请你完成以下2个任务：\n1、标题总结。\n为视频生成一个标题\n- title：视频的标题。\n2、大纲总结。\n- abstract：为视频总结一个大纲，大纲要高度概括视频，覆盖从开始到结束的各个镜头。每个镜头包括镜头主题和阶段细节。\n- theme：用一句话来概括该镜头的内容。\n- details：用key-value来展示该镜头的细节内容，数量根据实际内容多少来看，可以是1个、2个或3个。\n- content：该镜头的具体内容 \n- start：记录该镜头细节开始的时间点（秒）\n- end：记录该镜头细节结束的时间点（秒）\n\n# 输入数据\n## 资料一：视频分镜信息 (视频各镜头的视觉描述信息)\n{videoAnalysisText}\n\n## 资料二：视频ASR转录信息 (未标注出说话者，可能有错误和遗漏，如果没有输入ASR，则忽略此信息)\n{videoAsrText}\n\n## 资料三：视频补充信息 (如果输入为空则忽略补充信息)\n{videoExtraInfo}\n\n# 输出格式\n以以下json格式输出：\n{\"title\":\"\", \"abstract\": [{\"theme\": \"\", \"details\": {\"content\": \"\", \"start\": \"\", \"end\":\"\"}}]}",
            'generateOptions': ["videoAnalysis", "videoGenerate", "videoCaption", "videoMindMappingGenerate", "videoTitleGenerate"]
        }
        request = open_api_models.OpenApiRequest(
            body=body
        )
        sse_receiver = self._client.call_sse_api_async(params=self._api_info, request=request, runtime=self._runtime)
        return sse_receiver


    '''
    async def do_gemini_query(self,url):
        TMPDIRNAME = "/home/azureuser/iapwebsitebackend/tmp/"
        downloadurl = url.replace(" ","%20")
        url = url.replace(" ","")
        originalname = url[url.rfind("/")+1:]
        TMPFILENAME = TMPDIRNAME+originalname
        urlretrieve(downloadurl, TMPFILENAME)
        print("uploading file",TMPFILENAME)
        video_file = genai.upload_file(path=TMPFILENAME)
        while video_file.state.name == "PROCESSING":
            print('.', end='')
            time.sleep(10)
            video_file = genai.get_file(video_file.name)
        print(f"Completed upload: {video_file.uri}")
        if video_file.state.name == "FAILED":
            raise ValueError(video_file.state.name)
        prompt = """ Please generate a short title for this video. 
                     Please segment the following video by themes and events 
                     and for each segement, generate the following: 
                     generate a brief theme, 
                     generate a detailed summary and analysis of this segement
                     record start/end time in seconds"""
        class segment(typing.TypedDict):
            theme: str
            summary: str
            start: int
            end: int
        class video(typing.TypedDict):
            title: str
            segments: list[segment]
        result = self.model.generate_content(
            [video_file, prompt],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json", response_schema=video
            ),
        )
        video_file.delete()
        return result
    '''



# analyse video given by url
# exposing ali tea open api
# json: title, abstract: {
#   theme, details: {
#       content, start, end 
#   }
# }
async def run(url, extrainfo = "") -> dict:
    light_app = LightApp()
    ret = []
    #print("starting analysing")
    async for res in await light_app.do_sse_query(url,extrainfo):
        #print(res)
        data_str = res.get('event').data
       
        # 增加数据格式验证逻辑，使用正则简单判断是否像JSON格式
        if re.match(r'^\{.*\}$', data_str):
            try:
                data = json.loads(data_str)
                
                if data["header"]["event"] == "task-finished":
                    ret = analyse(data_str)
                    #pprint.pprint(ret,compact=True)
                    #print("analyses successful")
                    return ret
            except json.JSONDecodeError:
                print('------json.JSONDecodeError--------')
                print(res.get('headers'))
                print('------body------')
                print(data_str)
                print('------json.JSONDecodeError-end--------')
                return -1
        else:
            return -1
            print(f"接收到的数据格式不符合JSON规范: {data_str}")

def embeddingRun(txt) -> list:
    print("embedding:", txt)
    lightapp = LightApp()
    response = lightapp.gemini_embedding(txt)
    return response.embeddings[0].values
async def fileRun(url, extrainfo = ""):
    ret = []
    #print("starting analysing")
    file = open("planeroutput3")
    print("open completed")
    datastr = file.read()
    print("read completed")
    datastr = datastr.replace("\'","\"")
    print(datastr)
    ret = analyse(datastr)
    print("analyse completed")
    return ret



# processing result json string
def analyse(s:str):
    ret = {}
    s = s.replace("```json\\n","")
    s = s.replace("\\n","")
    s = s.replace("```","")
    #pprint.pprint(json.loads(s))
    #print("loading json")
    print("analysing")
    data = json.loads(s)
    '''captionlist = data["payload"]["output"]["videoCaptionResult"]["videoCaptions"]
    for cap in captionlist:
        pprint.pprint(cap)
    print()
    ret["captions"] = captionlist
    #pprint.pprint(json.loads(data["payload"]["output"]["videoGenerateResult"]["text"]))'''
    #generateText = data["payload"]["output"]["videoGenerateResult"]["text"]
    ret["generate_result"] = json.loads(data["payload"]["output"]["videoGenerateResult"]["text"])
    #ret["generate_result"] = data
    #print(ret["generate_result"])
    '''AnalysisStr = data["payload"]["output"]["videoAnalysisResult"]["text"]
    AnalysisStr = AnalysisStr.replace("###","\\n###")
    AnalysisStr = AnalysisStr.replace("-","\\n  -")
    scenetime = re.findall(r'（[0-9]+:[0-9]+~[0-9]+:[0-9]+）',AnalysisStr)
    sceneTexts = re.split(r'镜头[0-9:~（]*）：',AnalysisStr)
    ret["scenetime"] = scenetime
    ret["sceneTexts"] = sceneTexts[1:]
    for i in range(len(scene)):
        print(scene[i])
        print(sceneTexts[i+1])'''
    return ret

# dict analyse
def async_analyse(d: dict):
    ret = {}
    #pprint.pprint(d)
    #pprint.pprint(json.loads(s))
    #print("loading json")
    print("analysing")
    s = d["text"]
    #print(s)
    s = s.replace("```json","")
    s = s.replace("\\n","")
    s = s.replace("```","")
    s = s.replace("\n","")
    #print(s)
    ret = json.loads(s)
    '''captionlist = data["payload"]["output"]["videoCaptionResult"]["videoCaptions"]
    for cap in captionlist:
        pprint.pprint(cap)
    print()
    ret["captions"] = captionlist
    #pprint.pprint(json.loads(data["payload"]["output"]["videoGenerateResult"]["text"]))'''
    #generateText = data["payload"]["output"]["videoGenerateResult"]["text"]
    #ret["generate_result"] = data
    #print(ret["generate_result"])
    '''AnalysisStr = data["payload"]["output"]["videoAnalysisResult"]["text"]
    AnalysisStr = AnalysisStr.replace("###","\\n###")
    AnalysisStr = AnalysisStr.replace("-","\\n  -")
    scenetime = re.findall(r'（[0-9]+:[0-9]+~[0-9]+:[0-9]+）',AnalysisStr)
    sceneTexts = re.split(r'镜头[0-9:~（]*）：',AnalysisStr)
    ret["scenetime"] = scenetime
    ret["sceneTexts"] = sceneTexts[1:]
    for i in range(len(scene)):
        print(scene[i])
        print(sceneTexts[i+1])'''
    return ret


async def testrun2(url,extrainfo = ""):
    light_app = LightApp()
    async for res in await light_app.do_sse_query2(url,prompt="大红斑的研究"):
        data_str = res.get('event').data
        data = json.loads(data_str)
        # 增加数据格式验证逻辑，使用正则简单判断是否像JSON格式
        if re.match(r'^\{.*\}$', data_str):  
            try:
                if data["header"]["event"] == "task-finished":
                    
                    ret = analyse(data_str)
                    pprint.pprint(ret)
                    #pprint.pprint(ret,compact=True)
                    #print("analyses successful")
                    return ret
            except json.JSONDecodeError:
                print('------json.JSONDecodeError--------')
                print(res.get('headers'))
                print(data_str)
                print('------json.JSONDecodeError-end--------')
                continue
        else:
            print(f"接收到的数据格式不符合JSON规范: {data_str}")
    print('------end--------')

async def gemini_test_run(url):
    lightapp = LightApp()
    response = await lightapp.do_paragraph_gemini_query("The western diamondback rattlesnake or Texas diamond-back (Crotalus atrox) is a rattlesnake species and member of the viper family, found in the southwestern United States and Mexico. Like all other rattlesnakes and all other vipers, it is venomous. It is likely responsible for the majority of snakebite fatalities in northern Mexico and the greatest number of snakebites in the U.S. No subspecies are currently recognized.\
It lives in elevations from below sea level up to 6,500 feet (2,000 m). This species ranges throughout the Southwestern United States and northern half of Mexico. Currently, western diamondback rattlesnakes are not threatened or endangered.")
    print(response.text)
    #print(response.text)
    #text = response.text
    #text.replace("\n", "")
    #response = json.loads(response.text)
    #pprint.pprint(response)

async def gemini_paragraph_run(txt):
    lightapp = LightApp()
    response = await lightapp.do_paragraph_gemini_query(txt)
    #return(response.text)
    #print(response.text)
    text = response.text
    text.replace("\n", "")
    response = json.loads(response.text)
    return response
    #pprint.pprint(response)

async def gemini_run(url):
    lightapp = LightApp()
    response = await lightapp.do_gemini_query(url)
    #print(response)
    #print(response.text)
    text = response.text
    text.replace("\n", "")
    response = json.loads(response.text)
    #pprint.pprint(response)
    return response
    #pprint.pprint(response)

async def async_test_run(url):
    lightapp = LightApp()
    id = await lightapp.do_async_sse_query(url, "")
    print(id)
    while True:
        response = await lightapp.retrieve_async_sse_response(id)
        print(response.body.data.task_status)
        if(response.body.http_status_code == 200 and response.body.data.task_status == "SUCCESSED"):
            data = response.body.data.payload.output.video_generate_result.to_map()
            #pprint.pprint(data)
            final = async_analyse(data)
            pprint.pprint(final)
            return final
        
async def async_test_retrieve(id):
    lightapp = LightApp()
    print(id)
    while True:
        response = await lightapp.retrieve_async_sse_response(id)
        print(response.body.data.task_status)
        if(response.body.http_status_code == 200 and response.body.data.task_status == "SUCCESSED"):
            data = response.body.data.payload.output.video_generate_result.to_map()
            #pprint.pprint(data)
            final = async_analyse(data)
            pprint.pprint(final)
            return final

async def async_submit(url):
    lightapp = LightApp()
    id = await lightapp.do_async_sse_query(url, "")
    return id
    

async def async_try_retrieve(id):
    lightapp = LightApp()
    print(id)
    response, message = await lightapp.retrieve_async_sse_response(id)
    if message != None:
        return 1, message
    if(response.body.http_status_code != 200):
        return 1, response.body.http_status_code
    print(response.body.request_id, response.body.data.task_status)
    if(response.body.data.task_status == "SUCCESSED"):
        #print(response)
        data = response.body.data.payload.output.video_generate_result.to_map()
        #pprint.pprint(data)
        final = async_analyse(data)
        pprint.pprint(final)
        return 0, final
    if response.body.data.task_status == "PENDING" or response.body.data.task_status == "RUNNING":
        return 2, response.body.data.task_status
    else:
        return 3, response.body.data.task_status





if __name__ == '__main__':
    current_time = datetime.now().time()
    print("Current Time:", current_time)
    pprint.pprint(asyncio.run(gemini_run("./testdocker/video.mp4")))
    #print(asyncio.run(gemini_test_run(1)))
    txt = "The western diamondback rattlesnake or Texas diamond-back (Crotalus atrox) is a rattlesnake species and member of the viper family, found in the southwestern United States and Mexico. Like all other rattlesnakes and all other vipers, it is venomous. It is likely responsible for the majority of snakebite fatalities in northern Mexico and the greatest number of snakebites in the U.S. No subspecies are currently recognized.\
It lives in elevations from below sea level up to 6,500 feet (2,000 m). This species ranges throughout the Southwestern United States and northern half of Mexico. Currently, western diamondback rattlesnakes are not threatened or endangered."
    #pprint.pprint(asyncio.run(gemini_paragraph_run(txt)))
    #print(embeddingRun("what is the meaning of life"))
    #asyncio.run(testrun(url="https://shanghai-bgm-vioce.oss-cn-shanghai.aliyuncs.com/1736792415_V 8 RRR.mp4"))
    #asyncio.run(async_test_run(url="https://shanghai-bgm-vioce.oss-cn-shanghai.aliyuncs.com/c79afb98-a381-45c8-9808-c23c4d43e1f9_preview.mp4"))
    #asyncio.run(testrun2(url="https://rr2---sn-cxaaj5o5q5-tt1ed.googlevideo.com/videoplayback?expire=1739226879&ei=nyqqZ6WDEvO36dsP1YCP2AU&ip=176.6.131.181&id=o-ADdM0L1kLsg2oSmzeyMVVU0HlUFgSfdL4o_JjCQNwF-s&itag=134&aitags=133%2C134%2C135%2C136%2C137%2C160%2C242%2C243%2C244%2C247%2C248%2C278%2C394%2C395%2C396%2C397%2C398%2C399&source=youtube&requiressl=yes&xpc=EgVo2aDSNQ%3D%3D&bui=AUWDL3xdvU-YRSovQnsyhqIW1gBJovbsn0Huybn5DI3R0FQnPe6XvfifI0DUPANJduNZrZQXDq3YVGAj&spc=RjZbSYZNESKqu7NR1akdKqSAA157yN9G2HmRDb3lwyI5nMSUbg&vprv=1&svpuc=1&mime=video%2Fmp4&ns=FKZMFM7CKY16DIQIwXOD0g4Q&rqh=1&gir=yes&clen=3844874&dur=177.410&lmt=1709261240274551&keepalive=yes&fexp=24350590,24350737,24350827,24350934,24350961,24350976,24351028,24351059,24351082,51326932,51355912,51371294&c=WEB&sefc=1&txp=4535434&n=nLic2hPdN0nG8w&sparams=expire%2Cei%2Cip%2Cid%2Caitags%2Csource%2Crequiressl%2Cxpc%2Cbui%2Cspc%2Cvprv%2Csvpuc%2Cmime%2Cns%2Crqh%2Cgir%2Cclen%2Cdur%2Clmt&sig=AJfQdSswRQIgDYPMwvHUL6I64nUt2icKdQ2CY9FkzJer6OUTL9XLDkcCIQDbYOes1bIuqskoL0-9ZLTFLG6V_fr6CObt5EnhiLF7xA%3D%3D&pot=MnSXN-NWVS5_65cLigE0KmrUBYZRlWHvCelwHNtIK4iJnATciMpIckqrskU7bCOdryDKeShD87N97ZUrdnBffyClwjPj1Mx6ahn8OvfXWn9gj1zDefm2fs64pUr9WmbZPWUZDU6ntGk4hzNxM1P3mY5bV6F39g==&rm=sn-uxax4vopj5qx-cxge7s,sn-4g5erk76&rrc=79,104&req_id=90b673492391a3ee&rms=rdu,au&redirect_counter=2&cms_redirect=yes&cmsv=e&ipbypass=yes&met=1739205302,&mh=Uz&mip=184.144.58.8&mm=29&mn=sn-cxaaj5o5q5-tt1ed&ms=rdu&mt=1739204476&mv=u&mvi=2&pl=24&lsparams=ipbypass,met,mh,mip,mm,mn,ms,mv,mvi,pl,rms&lsig=AGluJ3MwRgIhAIC-htm49wIRQC2BbkgvqSkvMYELj1odjbfnbACH9R3cAiEAgpSDtqx6i1Xkx6-5smvZpbN_wFLhB4HsMadp_Sga77s%3D"))
    current_time = datetime.now().time()
    print("Current Time:", current_time)