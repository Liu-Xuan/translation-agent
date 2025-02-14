# 导入所需的Python标准库
import os
from typing import List, Union, Dict, Optional  # 导入类型提示所需的类型
import time
import logging

# 导入第三方依赖库
import openai  # OpenAI API客户端
import tiktoken  # OpenAI的分词工具
from dotenv import load_dotenv  # 用于加载环境变量
from icecream import ic  # 用于调试输出的工具
from langchain_text_splitters import RecursiveCharacterTextSplitter  # 文本分割工具
from translation_agent.glossary_utils import find_relevant_terms, format_glossary


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


def get_completion(
    prompt: str,
    system_message: str = "You are a helpful assistant.",
    model: str = "gpt-4-turbo",
    temperature: float = 0.3,
    json_mode: bool = False,
    max_retries: int = 3,  # 最大重试次数
    retry_delay: float = 5.0,  # 初始重试延迟（秒）
    timeout: float = 60.0,  # 请求超时时间
) -> Union[str, dict]:
    """
    使用OpenAI API生成补全，包含重试机制
    
    Args:
        prompt: 用户提示
        system_message: 系统消息
        model: 模型名称
        temperature: 温度参数
        json_mode: JSON输出模式
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
        timeout: 请求超时时间（秒）
    Returns:
        生成的回复
    """
    for attempt in range(max_retries):
        try:
            if json_mode:
                response = client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    top_p=1,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt},
                    ],
                    timeout=timeout
                )
                return response.choices[0].message.content
            else:
                response = client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    top_p=1,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt},
                    ],
                    timeout=timeout
                )
                return response.choices[0].message.content
                
        except Exception as e:
            if attempt < max_retries - 1:  # 如果还有重试机会
                logger.warning(f"API调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
                # 每次重试增加等待时间（指数退避）
                retry_delay *= 1.5
                continue
            else:
                logger.error(f"API调用失败，已重试{max_retries}次: {str(e)}")
                raise TranslationError(f"API调用失败，已重试{max_retries}次: {str(e)}") from e


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


def one_chunk_initial_translation(
    source_lang: str,
    target_lang: str,
    source_text: str,
    country: Optional[str] = None
) -> str:
    """
    单块文本的初始翻译
    Args:
        source_lang: 源语言代码
        target_lang: 目标语言代码
        source_text: 待翻译文本
        country: 可选的目标国家/地区
    Returns:
        str: 翻译结果
    """
    # 设置系统消息
    system_message = f"You are an expert linguist, specializing in translation from {source_lang} to {target_lang}."
    
    # 生成带术语的翻译提示
    prompt = format_translation_prompt_with_terms(
        source_lang,
        target_lang,
        source_text,
        country
    )
    
    # 获取翻译结果
    translation = get_completion(prompt, system_message=system_message)
    
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


def one_chunk_reflect_on_translation(
    source_lang: str,
    target_lang: str,
    source_text: str,
    translation_1: str,
    country: Optional[str] = None
) -> str:
    """
    对单块翻译进行反思
    Args:
        source_lang: 源语言代码
        target_lang: 目标语言代码
        source_text: 原文
        translation_1: 初次翻译
        country: 可选的目标国家/地区
    Returns:
        str: 反思结果
    """
    # 设置系统消息
    system_message = f"""You are an expert linguist specializing in translation from {source_lang} to {target_lang}.
You will be provided with a source text and its translation and your goal is to improve the translation."""
    
    # 生成带术语验证的反思提示
    prompt = format_reflection_prompt_with_terms(
        source_lang,
        target_lang,
        source_text,
        translation_1,
        country
    )
    
    # 获取反思结果
    reflection = get_completion(prompt, system_message=system_message)
    
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
        reflection: 翻译反思
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


def one_chunk_improve_translation(
    source_lang: str,
    target_lang: str,
    source_text: str,
    translation_1: str,
    reflection: str,
    country: Optional[str] = None
) -> str:
    """
    改进单块翻译
    Args:
        source_lang: 源语言代码
        target_lang: 目标语言代码
        source_text: 原文
        translation_1: 初次翻译
        reflection: 翻译反思
        country: 可选的目标国家/地区
    Returns:
        str: 改进后的翻译
    """
    # 设置系统消息
    system_message = f"You are an expert linguist, specializing in translation editing from {source_lang} to {target_lang}."
    
    # 生成带术语要求的改进提示
    prompt = format_improvement_prompt_with_terms(
        source_lang,
        target_lang,
        source_text,
        translation_1,
        reflection,
        country
    )
    
    # 获取改进后的翻译
    translation_2 = get_completion(prompt, system_message=system_message)
    
    return translation_2


def one_chunk_translate_text(
    source_lang: str,    # 源语言
    target_lang: str,    # 目标语言
    source_text: str,    # 待翻译的文本
    country: str = ""    # 目标语言所在国家（可选）
) -> str:  # 返回最终的翻译结果
    """
    Translate a single chunk of text from the source language to the target language.

    This function performs a two-step translation process:
    1. Get an initial translation of the source text.
    2. Reflect on the initial translation and generate an improved translation.

    Args:
        source_lang (str): The source language of the text.
        target_lang (str): The target language for the translation.
        source_text (str): The text to be translated.
        country (str): Country specified for the target language.
    Returns:
        str: The improved translation of the source text.
    """
    #将单个文本块从源语言翻译成目标语言。
    #该函数执行两步翻译过程：
        #1. 获取源文本的初次翻译
        #2. 对初次翻译进行反思并生成改进的翻译
    #参数:
        #source_lang (str): 源语言
        #target_lang (str): 目标语言
        #source_text (str): 待翻译的文本
        #country (str): 目标语言所在国家
    #返回:
        #str: 源文本的改进翻译结果


    # 获取初次翻译
    translation_1 = one_chunk_initial_translation(
        source_lang, target_lang, source_text, country
    )

    # 获取对初次翻译的反思
    reflection = one_chunk_reflect_on_translation(
        source_lang, target_lang, source_text, translation_1, country
    )
    # 基于反思改进翻译
    translation_2 = one_chunk_improve_translation(
        source_lang, target_lang, source_text, translation_1, reflection, country
    )

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
    source_text_chunks: List[str]  # 源文本块列表
) -> List[str]:  # 返回翻译后的文本块列表
    """
    Translate a text in multiple chunks from the source language to the target language.

    Args:
        source_lang (str): The source language of the text.
        target_lang (str): The target language for translation.
        source_text_chunks (List[str]): A list of text chunks to be translated.

    Returns:
        List[str]: A list of translated text chunks.
    """

    #将多个文本块从源语言翻译成目标语言。
    #参数:
        #source_lang (str): 源语言
        #target_lang (str): 目标语言
        #source_text_chunks (List[str]): 待翻译的文本块列表
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
        translation = get_completion(prompt, system_message=system_message)
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
        reflection = get_completion(prompt, system_message=system_message)
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
        translation_2 = get_completion(prompt, system_message=system_message)
        translation_2_chunks.append(translation_2)

    return translation_2_chunks


def multichunk_translation(
    source_lang,           # 源语言
    target_lang,          # 目标语言
    source_text_chunks,   # 源文本块列表
    country: str = ""     # 目标语言所在国家（可选）
):
    """
    Improves the translation of multiple text chunks based on the initial translation and reflection.

    Args:
        source_lang (str): The source language of the text chunks.
        target_lang (str): The target language for translation.
        source_text_chunks (List[str]): The list of source text chunks to be translated.
        translation_1_chunks (List[str]): The list of initial translations for each source text chunk.
        reflection_chunks (List[str]): The list of reflections on the initial translations.
        country (str): Country specified for the target language
    Returns:
        List[str]: The list of improved translations for each source text chunk.
    """

    #基于初次翻译和反思改进多个文本块的翻译。
    #参数:
        #source_lang (str): 源语言
        #target_lang (str): 目标语言
        #source_text_chunks (List[str]): 待翻译的源文本块列表
        #translation_1_chunks (List[str]): 每个源文本块的初次翻译列表
        #reflection_chunks (List[str]): 对初次翻译的反思列表
        #country (str): 目标语言使用的国家
    

    # 获取每个块的初次翻译
    translation_1_chunks = multichunk_initial_translation(
        source_lang, target_lang, source_text_chunks
    )

    # 获取对每个翻译块的反思
    reflection_chunks = multichunk_reflect_on_translation(
        source_lang,
        target_lang,
        source_text_chunks,
        translation_1_chunks,
        country,
    )

    # 基于反思改进每个翻译块
    translation_2_chunks = multichunk_improve_translation(
        source_lang,
        target_lang,
        source_text_chunks,
        translation_1_chunks,
        reflection_chunks,
    )

    return translation_2_chunks


def calculate_chunk_size(
    token_count: int,  # token总数
    token_limit: int   # 每个块的token限制
) -> int:  # 返回计算出的块大小
    """
    Calculate the chunk size based on the token count and token limit.

    Args:
        token_count (int): The total number of tokens.
        token_limit (int): The maximum number of tokens allowed per chunk.

    Returns:
        int: The calculated chunk size.

    Description:
        This function calculates the chunk size based on the given token count and token limit.
        If the token count is less than or equal to the token limit, the function returns the token count as the chunk size.
        Otherwise, it calculates the number of chunks needed to accommodate all the tokens within the token limit.
        The chunk size is determined by dividing the token limit by the number of chunks.
        If there are remaining tokens after dividing the token count by the token limit,
        the chunk size is adjusted by adding the remaining tokens divided by the number of chunks.

    Example:
        >>> calculate_chunk_size(1000, 500)
        500
        >>> calculate_chunk_size(1530, 500)
        389
        >>> calculate_chunk_size(2242, 500)
        496
    """

    #基于token数量和token限制计算块大小。
    #参数:
        #token_count (int): token总数
        #token_limit (int): 每个块允许的最大token数
    #返回:
        #int: 计算出的块大小
    #说明:
        #此函数基于给定的token总数和token限制计算块大小。
        #如果token总数小于或等于token限制，函数返回token总数作为块大小。
        #否则，它计算需要多少个块来容纳所有token，同时保持在token限制内。
        #块大小通过将token限制除以块数来确定。
        #如果在将token总数除以token限制后还有剩余token，
        #块大小会通过将剩余token除以块数来调整。
    #示例:
        #>>> calculate_chunk_size(1000, 500)
        #500
        #>>> calculate_chunk_size(1530, 500)
        #389
        #>>> calculate_chunk_size(2242, 500)
        #496




    # 如果token总数小于限制，直接返回token总数
    if token_count <= token_limit:
        return token_count

    # 计算需要的块数（向上取整）
    num_chunks = (token_count + token_limit - 1) // token_limit
    # 计算基本块大小
    chunk_size = token_count // num_chunks

    # 处理剩余的token
    remaining_tokens = token_count % token_limit
    if remaining_tokens > 0:
        chunk_size += remaining_tokens // num_chunks

    return chunk_size


def translate(
    source_lang,    # 源语言
    target_lang,    # 目标语言
    source_text,    # 源文本
    country,        # 目标语言所在国家
    max_tokens=MAX_TOKENS_PER_CHUNK,  # 每个块的最大token数
):
    """Translate the source_text from source_lang to target_lang."""
   # """翻译源文本从源语言到目标语言。"""



    # 计算源文本的token数量
    num_tokens_in_text = num_tokens_in_string(source_text)

    ic(num_tokens_in_text)

    # 如果token数量小于最大限制，作为单个块处理
    if num_tokens_in_text < max_tokens:
        ic("Translating text as a single chunk")

        # 使用单块翻译函数处理
        final_translation = one_chunk_translate_text(
            source_lang, target_lang, source_text, country
        )

        return final_translation

    else:
        # 如果token数量超过限制，需要分块处理
        ic("Translating text as multiple chunks")

        # 计算合适的块大小
        token_size = calculate_chunk_size(
            token_count=num_tokens_in_text, token_limit=max_tokens
        )

        ic(token_size)

        # 创建文本分割器
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            model_name="gpt-4",
            chunk_size=token_size,
            chunk_overlap=0,
        )

        # 将源文本分割成多个块
        source_text_chunks = text_splitter.split_text(source_text)

        # 使用多块翻译函数处理
        translation_2_chunks = multichunk_translation(
            source_lang, target_lang, source_text_chunks, country
        )

        # 合并所有翻译块并返回
        return "".join(translation_2_chunks)
