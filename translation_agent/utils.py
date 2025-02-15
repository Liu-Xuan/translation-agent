# 导入所需的Python标准库
import os
from typing import List, Union, Dict, Optional  # 导入类型提示所需的类型
import time
import logging
import requests
import json

# 导入第三方依赖库
import openai  # OpenAI API客户端
import tiktoken  # OpenAI的分词工具
from dotenv import load_dotenv  # 用于加载环境变量
from icecream import ic  # 用于调试输出的工具
from langchain_text_splitters import RecursiveCharacterTextSplitter  # 文本分割工具
from translation_agent.glossary_utils import find_relevant_terms, format_glossary
from tqdm import tqdm  # 用于进度条显示


# 加载本地.env文件中的环境变量
load_dotenv()  
# 初始化OpenAI客户端，使用环境变量中的API密钥
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 定义每个文本块的最大token数
MAX_TOKENS_PER_CHUNK = 1000  # 如果文本超过这个token数，将被分割成多个块逐块翻译

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TranslationError(Exception):
    """翻译错误异常类"""
    pass

def exponential_backoff(attempt: int, base_delay: float = 5.0) -> float:
    """
    计算指数退避延迟时间
    Args:
        attempt: 当前尝试次数（从0开始）
        base_delay: 基础延迟时间（秒）
    Returns:
        计算出的延迟时间（秒）
    """
    return min(base_delay * (2 ** attempt), 60)  # 最大延迟60秒

def calculate_timeout(text_length: int) -> float:
    """
    根据文本长度动态计算超时时间
    Args:
        text_length: 文本长度（字符数）
    Returns:
        计算出的超时时间（秒）
    """
    base_timeout = 60.0
    # 每1000字符增加10秒
    additional_timeout = (text_length // 1000) * 10
    return min(base_timeout + additional_timeout, 300)  # 最大5分钟

def calculate_chunk_size(token_count: int, token_limit: int) -> int:
    """
    优化分块大小计算，考虑上下文重叠
    Args:
        token_count: token总数
        token_limit: 每个块的token限制
    Returns:
        计算出的块大小
    """
    # 添加10%的上下文重叠
    overlap = min(100, token_limit // 10)
    effective_limit = token_limit - overlap
    return max(100, effective_limit)  # 确保最小块大小为100 tokens

async def get_completion(
    prompt: str,
    system_message: str = "You are a helpful assistant.",
    model: str = "gpt-4-turbo",
    temperature: float = 0.3,
    json_mode: bool = False,
    max_retries: int = 3,
    retry_delay: float = 5.0,
    timeout: float = 60.0
) -> Union[str, dict]:
    """使用API生成补全，包含改进的重试机制"""
    
    api_base = os.getenv("XIAOAI_API_BASE", "https://api.siliconflow.cn/v1/chat/completions")
    api_key = os.getenv("XIAOAI_API_KEY")
    
    logger.info(f"开始API调用 - 模型: {model}")
    logger.info(f"API基础URL: {api_base}")
    logger.info(f"系统消息: {system_message}")
    logger.info(f"温度参数: {temperature}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # 计算当前重试的延迟时间
            current_delay = exponential_backoff(attempt, retry_delay)
            if attempt > 0:
                logger.info(f"等待 {current_delay} 秒后重试...")
                time.sleep(current_delay)
            
            logger.info(f"尝试API调用 ({attempt + 1}/{max_retries})")
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "top_p": 1
            }
            
            if json_mode:
                logger.info("使用JSON输出模式")
                payload["response_format"] = {"type": "json_object"}
            
            logger.info(f"请求负载: {json.dumps(payload, ensure_ascii=False)[:200]}...")
            
            # 使用动态计算的超时时间
            current_timeout = calculate_timeout(len(prompt))
            logger.info(f"当前请求超时时间: {current_timeout}秒")
            
            response = requests.post(
                api_base,
                headers=headers,
                json=payload,
                timeout=current_timeout
            )
            
            logger.info(f"API响应状态码: {response.status_code}")
            logger.info(f"API响应内容: {response.text[:200]}...")
            
            if response.status_code != 200:
                raise TranslationError(f"API调用失败，状态码: {response.status_code}, 响应: {response.text}")
            
            response_data = response.json()
            if "choices" not in response_data or not response_data["choices"]:
                raise TranslationError("API响应格式错误，未找到choices字段")
                
            logger.info("API调用成功")
            return response_data["choices"][0]["message"]["content"]
            
        except Exception as e:
            last_error = e
            logger.error(f"API调用出错 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            continue
    
    # 所有重试都失败后抛出最后一个错误
    raise TranslationError(f"所有重试都失败: {str(last_error)}")


def format_translation_prompt_with_terms(
    source_lang: str,
    target_lang: str,
    source_text: str,
    country: Optional[str] = None
) -> str:
    """
    生成包含术语要求的翻译提示
    Args:
        source_lang: 源语言代码
        target_lang: 目标语言代码
        source_text: 待翻译文本
        country: 可选的目标国家/地区
    Returns:
        str: 完整的翻译提示
    """
    # 获取相关术语
    relevant_terms = find_relevant_terms(source_text)
    
    # 生成基础提示
    prompt = f"""请将以下{source_lang}文本翻译成{target_lang}。
保持原文的格式和标点符号。如有HTML标签或Markdown标记，请保留不变。

翻译要求：
1. 准确性：确保翻译准确传达原文含义
2. 格式保留：保持所有格式标记和特殊符号
3. 术语一致性：严格遵守术语表要求
4. 语言自然度：确保译文符合目标语言表达习惯"""

    # 添加国家/地区特定要求
    if country:
        prompt += f"\n5. 地区适配：使用{country}地区的用语习惯和表达方式"
    
    # 添加术语要求
    if relevant_terms:
        prompt += "\n\n## 术语表要求："
        prompt += format_glossary(relevant_terms)
        prompt += "\n请严格遵守以上术语表的翻译要求。对于术语的处理：\n"
        prompt += "1. 优先使用术语表中的对应翻译\n"
        prompt += "2. 保持术语的一致性\n"
        prompt += "3. 注意术语的上下文含义\n"
        prompt += "4. 保留术语的专业性"
    
    # 添加源文本
    prompt += f"\n\n源文本：\n{source_text}"
    
    return prompt


async def one_chunk_initial_translation(
    source_lang: str,
    target_lang: str,
    source_text: str,
    country: Optional[str] = None,
    model: str = "deepseek-v3"
) -> str:
    """
    单块文本的初始翻译，使用指定的模型
    """
    logger.info(f"开始初始翻译 - 从 {source_lang} 到 {target_lang}")
    if country:
        logger.info(f"目标地区: {country}")
    logger.info(f"使用模型: {model}")
    
    # 设置系统消息
    system_message = f"You are an expert linguist, specializing in translation from {source_lang} to {target_lang}."
    logger.info("系统消息设置完成")
    
    # 生成带术语的翻译提示
    logger.info("生成翻译提示...")
    prompt = format_translation_prompt_with_terms(
        source_lang,
        target_lang,
        source_text,
        country
    )
    logger.info("翻译提示生成完成")
    
    # 获取翻译结果
    logger.info(f"调用 {model} 模型进行翻译...")
    translation = await get_completion(
        prompt, 
        system_message=system_message,
        model=model
    )
    logger.info("初始翻译完成")
    
    return translation


def format_reflection_prompt_with_terms(
    source_lang: str,
    target_lang: str,
    source_text: str,
    translation: str,
    country: Optional[str] = None
) -> str:
    """
    生成包含术语验证的反思提示
    Args:
        source_lang: 源语言代码
        target_lang: 目标语言代码
        source_text: 原文
        translation: 当前翻译
        country: 可选的目标国家/地区
    Returns:
        str: 完整的反思提示
    """
    # 获取相关术语
    relevant_terms = find_relevant_terms(source_text)
    
    # 生成基础提示
    prompt = f"""请分析以下从{source_lang}到{target_lang}的翻译，重点关注以下方面：

1. 术语翻译：
   - 术语使用的准确性
   - 术语翻译的一致性
   - 术语上下文的适当性
   - 专业术语的规范性

2. 翻译质量：
   - 内容的完整性
   - 含义的准确性
   - 表达的自然度
   - 语言的流畅度

3. 格式规范：
   - 格式标记的保留
   - 标点符号的正确性
   - 特殊标记的处理
   - 排版的一致性"""

    # 添加国家/地区特定要求
    if country:
        prompt += f"\n4. 地区适配：\n   - 符合{country}地区的语言习惯\n   - 使用地区常用表达\n   - 考虑文化差异"
    
    # 添加术语要求
    if relevant_terms:
        prompt += "\n\n## 需要重点关注的术语："
        prompt += format_glossary(relevant_terms)
        prompt += "\n\n请特别注意：\n"
        prompt += "1. 检查每个术语是否按照术语表正确翻译\n"
        prompt += "2. 验证术语在上下文中的使用是否恰当\n"
        prompt += "3. 确认术语的专业性是否得到保持\n"
        prompt += "4. 评估术语翻译的一致性"
    
    # 添加原文和译文
    prompt += f"\n\n原文：\n{source_text}\n\n当前译文：\n{translation}"
    
    # 添加反思要求
    prompt += "\n\n请提供具体的改进建议，包括：\n"
    prompt += "1. 术语使用问题\n"
    prompt += "2. 表达改进建议\n"
    prompt += "3. 格式调整建议\n"
    prompt += "4. 其他需要注意的问题"
    
    return prompt


async def one_chunk_reflect_on_translation(
    source_lang: str,
    target_lang: str,
    source_text: str,
    translation_1: str,
    country: Optional[str] = None,
    model: str = "deepseek-r1"
) -> str:
    """
    对单块文本的翻译进行反思，使用指定的模型
    """
    logger.info(f"开始翻译反思 - 从 {source_lang} 到 {target_lang}")
    if country:
        logger.info(f"目标地区: {country}")
    logger.info(f"使用模型: {model}")
    
    # 设置系统消息
    system_message = f"You are an expert linguist and translation reviewer, specializing in {source_lang} to {target_lang} translation quality assessment."
    logger.info("系统消息设置完成")
    
    # 生成带术语验证的反思提示
    logger.info("生成反思提示...")
    prompt = format_reflection_prompt_with_terms(
        source_lang,
        target_lang,
        source_text,
        translation_1,
        country
    )
    logger.info("反思提示生成完成")
    
    # 获取反思结果
    logger.info(f"调用 {model} 模型进行反思...")
    reflection = await get_completion(
        prompt, 
        system_message=system_message,
        model=model
    )
    logger.info("翻译反思完成")
    
    return reflection


def format_improvement_prompt_with_terms(
    source_lang: str,
    target_lang: str,
    source_text: str,
    translation: str,
    reflection: str,
    country: Optional[str] = None
) -> str:
    """
    生成包含术语要求的改进提示
    Args:
        source_lang: 源语言代码
        target_lang: 目标语言代码
        source_text: 原文
        translation: 当前翻译
        reflection: 反思结果
        country: 可选的目标国家/地区
    Returns:
        str: 完整的改进提示
    """
    # 获取相关术语
    relevant_terms = find_relevant_terms(source_text)
    
    # 生成基础提示
    prompt = f"""请根据以下反馈改进这段从{source_lang}到{target_lang}的翻译。

改进重点：
1. 术语处理
   - 严格遵守术语表要求
   - 保持术语翻译一致性
   - 确保术语使用准确
   - 维护专业术语规范

2. 翻译质量
   - 提高表达准确性
   - 增强语言流畅度
   - 保持内容完整性
   - 改进表达自然度

3. 格式规范
   - 保持格式标记完整
   - 规范标点符号使用
   - 正确处理特殊标记
   - 统一排版风格"""

    # 添加国家/地区特定要求
    if country:
        prompt += f"\n4. 地区适配\n   - 符合{country}地区表达习惯\n   - 使用地区常用用语\n   - 注意文化差异处理"
    
    # 添加术语要求
    if relevant_terms:
        prompt += "\n\n## 术语表要求："
        prompt += format_glossary(relevant_terms)
        prompt += "\n\n术语处理原则：\n"
        prompt += "1. 必须使用术语表规定的译法\n"
        prompt += "2. 确保术语在上下文中使用恰当\n"
        prompt += "3. 保持术语翻译的专业性\n"
        prompt += "4. 维护术语使用的一致性"
    
    # 添加原文、当前译文和反思建议
    prompt += f"""
原文：
{source_text}

当前译文：
{translation}

改进建议：
{reflection}

请根据以上要求提供改进后的译文。注意：
1. 认真考虑所有改进建议
2. 确保术语使用准确
3. 保持格式完整性
4. 提升整体翻译质量

请提供改进后的译文："""
    
    return prompt


async def one_chunk_improve_translation(
    source_lang: str,
    target_lang: str,
    source_text: str,
    translation_1: str,
    reflection: str,
    country: Optional[str] = None,
    model: str = "deepseek-v3"
) -> str:
    """
    根据反思改进单块文本的翻译，使用指定的模型
    """
    logger.info(f"开始翻译改进 - 从 {source_lang} 到 {target_lang}")
    if country:
        logger.info(f"目标地区: {country}")
    logger.info(f"使用模型: {model}")
    
    # 设置系统消息
    system_message = f"You are an expert linguist, specializing in improving {source_lang} to {target_lang} translations based on professional review feedback."
    logger.info("系统消息设置完成")
    
    # 生成改进提示
    logger.info("生成改进提示...")
    prompt = format_improvement_prompt_with_terms(
        source_lang,
        target_lang,
        source_text,
        translation_1,
        reflection,
        country
    )
    logger.info("改进提示生成完成")
    
    # 获取改进后的翻译
    logger.info(f"调用 {model} 模型进行改进...")
    improved_translation = await get_completion(
        prompt, 
        system_message=system_message,
        model=model
    )
    logger.info("翻译改进完成")
    
    return improved_translation


def one_chunk_translate_text(
    source_lang: str,    # 源语言
    target_lang: str,    # 目标语言
    source_text: str,    # 待翻译的文本
    country: str = "",    # 目标语言所在国家（可选）
    initial_model: str = "deepseek-v3",  # 初始翻译模型
    reflection_model: str = "deepseek-r1",  # 翻译反思模型
    improvement_model: str = "deepseek-v3",  # 翻译改进模型
    timeout: float = 60.0  # 超时时间
) -> str:  # 返回最终的翻译结果
    """
    Translate a single chunk of text from the source language to the target language.

    This function performs a three-step translation process:
    1. Get an initial translation of the source text using initial_model.
    2. Reflect on the initial translation using reflection_model.
    3. Generate an improved translation based on the reflection using improvement_model.

    Args:
        source_lang (str): The source language of the text.
        target_lang (str): The target language for the translation.
        source_text (str): The text to be translated.
        country (str): Country specified for the target language.
        initial_model (str): Model to use for initial translation.
        reflection_model (str): Model to use for translation reflection.
        improvement_model (str): Model to use for translation improvement.
        timeout (float): Timeout for the translation process.
    Returns:
        str: The improved translation of the source text.
    """

    # 获取初次翻译
    translation_1 = asyncio.run(one_chunk_initial_translation(
        source_lang, target_lang, source_text, country, model=initial_model
    ))

    # 获取对初次翻译的反思
    reflection = asyncio.run(one_chunk_reflect_on_translation(
        source_lang, target_lang, source_text, translation_1, country, model=reflection_model
    ))

    # 基于反思改进翻译
    translation_2 = asyncio.run(one_chunk_improve_translation(
        source_lang, target_lang, source_text, translation_1, reflection, country, model=improvement_model
    ))

    return translation_2


def num_tokens_in_string(
    input_str: str,                      # 输入字符串
    encoding_name: str = "cl100k_base"   # 编码器名称
) -> int:  # 返回token数量
    """
    Calculate the number of tokens in a given string using a specified encoding.

    Args:
        str (str): The input string to be tokenized.
        encoding_name (str, optional): The name of the encoding to use. Defaults to "cl100k_base",
            which is the most commonly used encoder (used by GPT-4).

    Returns:
        int: The number of tokens in the input string.

    Example:
        >>> text = "Hello, how are you?"
        >>> num_tokens = num_tokens_in_string(text)
        >>> print(num_tokens)
        5
    """

    #使用指定的编码计算给定字符串中的token数量。
    #参数:
        #str (str): 需要计算token数量的输入字符串
        #encoding_name (str, 可选): 使用的编码器名称。默认为"cl100k_base"，
            #这是GPT-4最常用的编码器。
    #返回:
        #int: 输入字符串中的token数量
    #示例:

    
    # 获取指定的编码器
    encoding = tiktoken.get_encoding(encoding_name)
    # 计算token数量
    num_tokens = len(encoding.encode(input_str))
    return num_tokens


def multichunk_initial_translation(
    source_lang: str,              # 源语言
    target_lang: str,              # 目标语言
    source_text_chunks: List[str],  # 源文本块列表
    model: str = "deepseek-v3"  # 指定模型
) -> List[str]:  # 返回翻译后的文本块列表
    """
    Translate a text in multiple chunks from the source language to the target language.

    Args:
        source_lang (str): The source language of the text.
        target_lang (str): The target language for translation.
        source_text_chunks (List[str]): A list of text chunks to be translated.
        model (str): The model to use for translation.

    Returns:
        List[str]: A list of translated text chunks.
    """

    #将多个文本块从源语言翻译成目标语言。
    #参数:
        #source_lang (str): 源语言
        #target_lang (str): 目标语言
        #source_text_chunks (List[str]): 待翻译的文本块列表
        #model (str): 使用的模型
    #返回:
        #List[str]: 翻译后的文本块列表

    # 设置系统消息，定义模型角色为特定语言对的翻译专家
    system_message = f"You are an expert linguist, specializing in translation from {source_lang} to {target_lang}."

    # 构建翻译提示模板
    translation_prompt = """Your task is to provide a professional translation from {source_lang} to {target_lang} of PART of a text.

The source text is below, delimited by XML tags <SOURCE_TEXT> and </SOURCE_TEXT>. Translate only the part within the source text
delimited by <TRANSLATE_THIS> and </TRANSLATE_THIS>. You can use the rest of the source text as context, but do not translate any
of the other text. Do not output anything other than the translation of the indicated part of the text.

<SOURCE_TEXT>
{tagged_text}
</SOURCE_TEXT>

To reiterate, you should translate only this part of the text, shown here again between <TRANSLATE_THIS> and </TRANSLATE_THIS>:
<TRANSLATE_THIS>
{chunk_to_translate}
</TRANSLATE_THIS>

Output only the translation of the portion you are asked to translate, and nothing else.
"""

    # 存储翻译结果的列表
    translation_chunks = []
    # 遍历每个文本块进行翻译
    for i in range(len(source_text_chunks)):
        # 将当前要翻译的块用XML标签标记，其他块作为上下文
        tagged_text = (
            "".join(source_text_chunks[0:i])
            + "<TRANSLATE_THIS>"
            + source_text_chunks[i]
            + "</TRANSLATE_THIS>"
            + "".join(source_text_chunks[i + 1 :])
        )

        # 构建完整的翻译提示
        prompt = translation_prompt.format(
            source_lang=source_lang,
            target_lang=target_lang,
            tagged_text=tagged_text,
            chunk_to_translate=source_text_chunks[i],
        )

        # 获取翻译结果
        translation = asyncio.run(get_completion(prompt, system_message=system_message, model=model))
        translation_chunks.append(translation)

    return translation_chunks


def multichunk_reflect_on_translation(
    source_lang: str,                # 源语言
    target_lang: str,                # 目标语言
    source_text_chunks: List[str],   # 源文本块列表
    translation_1_chunks: List[str],  # 初次翻译的文本块列表
    country: str = "",               # 目标语言所在国家（可选）
) -> List[str]:  # 返回对每个翻译块的反思列表
    """
    Provides constructive criticism and suggestions for improving a partial translation.

    Args:
        source_lang (str): The source language of the text.
        target_lang (str): The target language of the translation.
        source_text_chunks (List[str]): The source text divided into chunks.
        translation_1_chunks (List[str]): The translated chunks corresponding to the source text chunks.
        country (str): Country specified for the target language.

    Returns:
        List[str]: A list of reflections containing suggestions for improving each translated chunk.
    """
    #对部分翻译提供建设性批评和改进建议。
    #参数:
        #source_lang (str): 源语言
        #target_lang (str): 目标语言
        #source_text_chunks (List[str]): 分块的源文本
        #translation_1_chunks (List[str]): 对应源文本块的翻译结果
        #country (str): 目标语言使用的国家
    #返回:
        #List[str]: 包含对每个翻译块的改进建议的列表

    # 设置系统消息，定义模型角色为特定语言对的翻译专家
    system_message = f"You are an expert linguist specializing in translation from {source_lang} to {target_lang}. \
You will be provided with a source text and its translation and your goal is to improve the translation."

    # 根据是否指定国家选择不同的反思提示模板
    if country != "":
        reflection_prompt = """Your task is to carefully read a source text and part of a translation of that text from {source_lang} to {target_lang}, and then give constructive criticism and helpful suggestions for improving the translation.
The final style and tone of the translation should match the style of {target_lang} colloquially spoken in {country}.

The source text is below, delimited by XML tags <SOURCE_TEXT> and </SOURCE_TEXT>, and the part that has been translated
is delimited by <TRANSLATE_THIS> and </TRANSLATE_THIS> within the source text. You can use the rest of the source text
as context for critiquing the translated part.

<SOURCE_TEXT>
{tagged_text}
</SOURCE_TEXT>

To reiterate, only part of the text is being translated, shown here again between <TRANSLATE_THIS> and </TRANSLATE_THIS>:
<TRANSLATE_THIS>
{chunk_to_translate}
</TRANSLATE_THIS>

The translation of the indicated part, delimited below by <TRANSLATION> and </TRANSLATION>, is as follows:
<TRANSLATION>
{translation_1_chunk}
</TRANSLATION>

When writing suggestions, pay attention to whether there are ways to improve the translation's:\n\
(i) accuracy (by correcting errors of addition, mistranslation, omission, or untranslated text),\n\
(ii) fluency (by applying {target_lang} grammar, spelling and punctuation rules, and ensuring there are no unnecessary repetitions),\n\
(iii) style (by ensuring the translations reflect the style of the source text and take into account any cultural context),\n\
(iv) terminology (by ensuring terminology use is consistent and reflects the source text domain; and by only ensuring you use equivalent idioms {target_lang}).\n\

Write a list of specific, helpful and constructive suggestions for improving the translation.
Each suggestion should address one specific part of the translation.
Output only the suggestions and nothing else."""

    else:
        reflection_prompt = """Your task is to carefully read a source text and part of a translation of that text from {source_lang} to {target_lang}, and then give constructive criticism and helpful suggestions for improving the translation.

The source text is below, delimited by XML tags <SOURCE_TEXT> and </SOURCE_TEXT>, and the part that has been translated
is delimited by <TRANSLATE_THIS> and </TRANSLATE_THIS> within the source text. You can use the rest of the source text
as context for critiquing the translated part.

<SOURCE_TEXT>
{tagged_text}
</SOURCE_TEXT>

To reiterate, only part of the text is being translated, shown here again between <TRANSLATE_THIS> and </TRANSLATE_THIS>:
<TRANSLATE_THIS>
{chunk_to_translate}
</TRANSLATE_THIS>

The translation of the indicated part, delimited below by <TRANSLATION> and </TRANSLATION>, is as follows:
<TRANSLATION>
{translation_1_chunk}
</TRANSLATION>

When writing suggestions, pay attention to whether there are ways to improve the translation's:\n\
(i) accuracy (by correcting errors of addition, mistranslation, omission, or untranslated text),\n\
(ii) fluency (by applying {target_lang} grammar, spelling and punctuation rules, and ensuring there are no unnecessary repetitions),\n\
(iii) style (by ensuring the translations reflect the style of the source text and take into account any cultural context),\n\
(iv) terminology (by ensuring terminology use is consistent and reflects the source text domain; and by only ensuring you use equivalent idioms {target_lang}).\n\

Write a list of specific, helpful and constructive suggestions for improving the translation.
Each suggestion should address one specific part of the translation.
Output only the suggestions and nothing else."""

    # 存储反思结果的列表
    reflection_chunks = []
    # 遍历每个文本块进行反思
    for i in range(len(source_text_chunks)):
        # 将当前要反思的块用XML标签标记，其他块作为上下文
        tagged_text = (
            "".join(source_text_chunks[0:i])
            + "<TRANSLATE_THIS>"
            + source_text_chunks[i]
            + "</TRANSLATE_THIS>"
            + "".join(source_text_chunks[i + 1 :])
        )
        # 根据是否指定国家构建完整的反思提示
        if country != "":
            prompt = reflection_prompt.format(
                source_lang=source_lang,
                target_lang=target_lang,
                tagged_text=tagged_text,
                chunk_to_translate=source_text_chunks[i],
                translation_1_chunk=translation_1_chunks[i],
                country=country,
            )
        else:
            prompt = reflection_prompt.format(
                source_lang=source_lang,
                target_lang=target_lang,
                tagged_text=tagged_text,
                chunk_to_translate=source_text_chunks[i],
                translation_1_chunk=translation_1_chunks[i],
            )

        # 获取反思结果
        reflection = asyncio.run(get_completion(prompt, system_message=system_message))
        reflection_chunks.append(reflection)

    return reflection_chunks


def multichunk_improve_translation(
    source_lang: str,                # 源语言
    target_lang: str,                # 目标语言
    source_text_chunks: List[str],   # 源文本块列表
    translation_1_chunks: List[str],  # 初次翻译的文本块列表
    reflection_chunks: List[str],     # 对每个翻译块的反思列表
) -> List[str]:  # 返回改进后的翻译块列表
    """
    Improves the translation of a text from source language to target language by considering expert suggestions.

    Args:
        source_lang (str): The source language of the text.
        target_lang (str): The target language for translation.
        source_text_chunks (List[str]): The source text divided into chunks.
        translation_1_chunks (List[str]): The initial translation of each chunk.
        reflection_chunks (List[str]): Expert suggestions for improving each translated chunk.

    Returns:
        List[str]: The improved translation of each chunk.
    """

    #通过考虑专家建议来改进从源语言到目标语言的文本翻译。
    #参数:
        #source_lang (str): 源语言
        #target_lang (str): 目标语言
        #source_text_chunks (List[str]): 分块的源文本
        #translation_1_chunks (List[str]): 每个块的初次翻译
        #reflection_chunks (List[str]): 对每个翻译块的专家建议
    #返回:
        #List[str]: 每个块改进后的翻译


    # 设置系统消息，定义模型角色为特定语言对的翻译编辑专家
    system_message = f"You are an expert linguist, specializing in translation editing from {source_lang} to {target_lang}."

    # 构建改进翻译的提示模板
    improvement_prompt = """Your task is to carefully read, then improve, a translation from {source_lang} to {target_lang}, taking into
account a set of expert suggestions and constructive criticisms. Below, the source text, initial translation, and expert suggestions are provided.

The source text is below, delimited by XML tags <SOURCE_TEXT> and </SOURCE_TEXT>, and the part that has been translated
is delimited by <TRANSLATE_THIS> and </TRANSLATE_THIS> within the source text. You can use the rest of the source text
as context, but need to provide a translation only of the part indicated by <TRANSLATE_THIS> and </TRANSLATE_THIS>.

<SOURCE_TEXT>
{tagged_text}
</SOURCE_TEXT>

To reiterate, only part of the text is being translated, shown here again between <TRANSLATE_THIS> and </TRANSLATE_THIS>:
<TRANSLATE_THIS>
{chunk_to_translate}
</TRANSLATE_THIS>

The translation of the indicated part, delimited below by <TRANSLATION> and </TRANSLATION>, is as follows:
<TRANSLATION>
{translation_1_chunk}
</TRANSLATION>

The expert translations of the indicated part, delimited below by <EXPERT_SUGGESTIONS> and </EXPERT_SUGGESTIONS>, are as follows:
<EXPERT_SUGGESTIONS>
{reflection_chunk}
</EXPERT_SUGGESTIONS>

Taking into account the expert suggestions rewrite the translation to improve it, paying attention
to whether there are ways to improve the translation's

(i) accuracy (by correcting errors of addition, mistranslation, omission, or untranslated text),
(ii) fluency (by applying {target_lang} grammar, spelling and punctuation rules and ensuring there are no unnecessary repetitions), \
(iii) style (by ensuring the translations reflect the style of the source text)
(iv) terminology (inappropriate for context, inconsistent use), or
(v) other errors.

Output only the new translation of the indicated part and nothing else."""

    # 存储改进后翻译的列表
    translation_2_chunks = []
    # 遍历每个文本块进行改进
    for i in range(len(source_text_chunks)):
        # 将当前要改进的块用XML标签标记，其他块作为上下文
        tagged_text = (
            "".join(source_text_chunks[0:i])
            + "<TRANSLATE_THIS>"
            + source_text_chunks[i]
            + "</TRANSLATE_THIS>"
            + "".join(source_text_chunks[i + 1 :])
        )

        # 构建完整的改进提示
        prompt = improvement_prompt.format(
            source_lang=source_lang,
            target_lang=target_lang,
            tagged_text=tagged_text,
            chunk_to_translate=source_text_chunks[i],
            translation_1_chunk=translation_1_chunks[i],
            reflection_chunk=reflection_chunks[i],
        )

        # 获取改进后的翻译
        translation_2 = asyncio.run(get_completion(prompt, system_message=system_message))
        translation_2_chunks.append(translation_2)

    return translation_2_chunks


def multichunk_translation(
    source_lang: str,
    target_lang: str,
    source_text_chunks: List[str],
    country: str,
    model: str  # 新增模型参数
) -> List[str]:
    return [
        one_chunk_translate_text(
            source_lang, target_lang, chunk, country, model=model
        )
        for chunk in tqdm(source_text_chunks, desc="翻译进度")
    ]


def translate(
    source_lang: str,
    target_lang: str,
    source_text: str,
    country: str,
    model: str = "deepseek-v3",
    max_tokens: Optional[int] = None
) -> str:
    """增强的翻译函数"""
    # 使用配置类获取分块大小
    chunk_size = chunk_config.get_chunk_size(model)
    if max_tokens:
        chunk_size = min(chunk_size, max_tokens)
    
    # 计算文本token数
    num_tokens = num_tokens_in_string(source_text)
    logger.info(f"源文本长度: {len(source_text)}字符，{num_tokens}个token")
    
    if len(source_text) <= chunk_size:
        # 小文本直接翻译
        timeout = chunk_config.get_timeout(model, len(source_text))
        return one_chunk_translate_text(
            source_lang, target_lang, source_text, country,
            model=model, timeout=timeout
        )
    
    # 大文本分块处理
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name=model.split('/')[-1],
        chunk_size=chunk_size,
        chunk_overlap=int(chunk_size * 0.1)  # 10%重叠
    )
    
    chunks = text_splitter.split_text(source_text)
    logger.info(f"文本已分割为{len(chunks)}块，每块约{chunk_size}字符")
    
    translated_chunks = []
    for i, chunk in enumerate(chunks, 1):
        timeout = chunk_config.get_timeout(model, len(chunk))
        logger.info(f"翻译第{i}/{len(chunks)}块，超时设置: {timeout}秒")
        
        translation = one_chunk_translate_text(
            source_lang, target_lang, chunk, country,
            model=model, timeout=timeout
        )
        translated_chunks.append(translation)
    
    return "".join(translated_chunks)


def generate_translation(prompt, system_prompt, model="deepseek-v3"):
    """生成翻译的核心函数"""
    try:
        # 增强调试信息
        logger.debug(f"【API请求详情】\n模型: {model}\n系统提示: {system_prompt[:200]}...\n用户提示: {prompt[:200]}...")
        logger.debug(f"API端点: https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
        logger.debug(f"API密钥: sk-96ddff88a51f40cda3af8a5ae70b8d9a")
        
        start_time = time.time()
        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer sk-96ddff88a51f40cda3af8a5ae70b8d9a"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
        )
        latency = time.time() - start_time
        
        # 记录完整响应头信息
        logger.debug(f"【API响应】状态码: {response.status_code} 延迟: {latency:.2f}s")
        logger.debug(f"响应头: {dict(response.headers)}")
        
        # 成功响应处理
        if response.status_code == 200:
            response_data = response.json()
            logger.debug(f"完整响应体: {json.dumps(response_data, ensure_ascii=False)[:500]}...")
            logger.info(f"API调用成功 - 使用模型: {model} 消耗token: {response_data.get('usage', {}).get('total_tokens', '未知')}")
            return response_data["choices"][0]["message"]["content"]
        
        # 错误响应处理
        logger.error(f"API错误响应: {response.text}")
        logger.error(f"请求详情:\nURL: {response.request.url}\nMethod: {response.request.method}\nBody: {response.request.body[:300]}...")
        
        raise TranslationError(f"API返回错误状态码: {response.status_code}")
        
    except Exception as e:
        logger.error("【API调用异常】", exc_info=True)
        logger.error(f"最后请求信息:\nURL: {response.request.url if 'response' in locals() else 'N/A'}\nMethod: {response.request.method if 'response' in locals() else 'N/A'}")
        raise TranslationError("翻译服务暂时不可用") from e
