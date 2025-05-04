from http import HTTPStatus
import dashscope
import video_analysis
import json
import os
import asyncio
def doc_split_with_qwen_plus(input_filepath, output_filepath):

    if not os.path.exists(output_filepath):
        os.makedirs(output_filepath)

    with open(input_filepath, 'r', encoding='utf-8') as file:
        content = file.read()

    prompt = """
                    执行文档处理任务，包括分段与自动生成段落标题，需遵循以下具体细则：

                    1. **分段逻辑**：仔细分析文档内容，根据其内在语义逻辑合理划分段落。

                    2. **标题创作**：为每一独立段落设计一个精炼标题，确保该标题简洁明了（不超过10个字），并能有效准确地概括该段落核心信息。

                    3. **输出规格**：完成处理后，生成的文档结构需符合JSON格式标准，每段落及对应的标题组成一个条目，具体格式示例如下：
                    

                    [ 
                        {"title": " ", "content": " "},
                        {"title": " ", "content": " "},
                        ...
                    ]
              
                    输出内容是以"["开头，并以"]"收尾的JSON数据，请不要输出其他内容。

                    4. **原文忠实性**：在输出的JSON数据中，各段落的“content”字段必须精确匹配原始文档的文字内容，不得有增删改动。必须完整地处理原始文档的全部内容，不能有遗漏。请严格保证文字和链接在原文档中的相对位置保持不变。

                    5. **格式化链接**：对于文档中的markdown格式的图片链接，将他们单独保存到JSON条目中。其"title"为"链接{index}"，"content"为链接地址，其中index为索引顺序。

                    6. **内容限制**：输出内容中不得包含任何多余的空格、换行符、制表符等空白字符，也不得包含任何HTML、XML、Markdown等格式的符号。始终保持中文。
    
                    请严格依据上述要求执行文档处理任务。

                    文档内容如下：
              """

    messages = [{
        'role': 'user',
        'content': f"""
                    "{prompt}"
                    "{content}"
                   """
    }]

    response_content = ''
    responses = dashscope.Generation.call("qwen-plus",
                                          messages=messages,
                                          result_format='message',
                                          stream=True,
                                          incremental_output=True)

    for response in responses:
        if response.status_code == HTTPStatus.OK:
            response_content += response.output.choices[0]['message']['content']
        else:
            print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                response.request_id, response.status_code,
                response.code, response.message
            ))
    if response_content.startswith("```") and response_content.endswith("```"):
        response_content = response_content[8:-3].strip()

    input_base_name = os.path.splitext(os.path.basename(input_filepath))[0]
    output_file_path = os.path.join(output_filepath, f'{input_base_name}.json')
    with open(output_file_path, 'w', encoding='utf-8') as json_file:
        print(response_content)
        json.dump(json.loads(response_content), json_file, ensure_ascii=False, indent=4)

    return response_content


def doc_split_with_gemini(input_filepath, output_filepath):

    if not os.path.exists(output_filepath):
        os.makedirs(output_filepath)

    with open(input_filepath, 'r', encoding='utf-8') as file:
        content = file.read()

    responses = asyncio.run(video_analysis.gemini_paragraph_run(content))["segments"]

    input_base_name = os.path.splitext(os.path.basename(input_filepath))[0]
    output_file_path = os.path.join(output_filepath, f'{input_base_name}.json')
    with open(output_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(responses, json_file, ensure_ascii=False, indent=4)

    return responses