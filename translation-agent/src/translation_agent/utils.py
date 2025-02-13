# 导入所需的Python标准库
import os
from typing import List, Union  # 导入类型提示所需的类型

# 导入第三方依赖库
import openai  # OpenAI API客户端
import tiktoken  # OpenAI的分词工具
from dotenv import load_dotenv  # 用于加载环境变量
from icecream import ic  # 用于调试输出的工具
from langchain_text_splitters import RecursiveCharacterTextSplitter  # 文本分割工具


# 加载本地.env文件中的环境变量
load_dotenv()  
# 初始化OpenAI客户端，使用环境变量中的API密钥
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 定义每个文本块的最大token数
MAX_TOKENS_PER_CHUNK = 1000  # 如果文本超过这个token数，将被分割成多个块逐块翻译


def get_completion(
    prompt: str,  # 用户提示或查询
    system_message: str = "You are a helpful assistant.",  # 系统消息，设置助手的上下文
    model: str = "gpt-4-turbo",  # 使用的OpenAI模型名称
    temperature: float = 0.3,  # 采样温度，控制生成文本的随机性
    json_mode: bool = False,  # 是否返回JSON格式的响应
) -> Union[str, dict]:  # 返回字符串或字典类型
    """
        Generate a completion using the OpenAI API.

    Args:
        prompt (str): The user's prompt or query.
        system_message (str, optional): The system message to set the context for the assistant.
            Defaults to "You are a helpful assistant.".
        model (str, optional): The name of the OpenAI model to use for generating the completion.
            Defaults to "gpt-4-turbo".
        temperature (float, optional): The sampling temperature for controlling the randomness of the generated text.
            Defaults to 0.3.
        json_mode (bool, optional): Whether to return the response in JSON format.
            Defaults to False.

    Returns:
        Union[str, dict]: The generated completion.
            If json_mode is True, returns the complete API response as a dictionary.
            If json_mode is False, returns the generated text as a string.
    """

    #参数:
        #prompt (str): 用户的提示或查询
        #system_message (str, 可选): 设置助手上下文的系统消息
        #model (str, 可选): 使用的OpenAI模型名称
        #temperature (float, 可选): 控制生成文本随机性的采样温度
        #json_mode (bool, 可选): 是否返回JSON格式的响应
    #返回:
        #Union[str, dict]: 生成的补全响应
            #如果json_mode为True，返回完整的API响应字典
            #如果json_mode为False，返回生成的文本字符串

    if json_mode:
        # 创建聊天补全请求，指定JSON响应格式
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            top_p=1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content
    else:
        # 创建普通的聊天补全请求
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            top_p=1,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content


def one_chunk_initial_translation(
    source_lang: str,  # 源语言
    target_lang: str,  # 目标语言
    source_text: str   # 待翻译的文本
) -> str:  # 返回翻译后的文本
    """
    Translate the entire text as one chunk using an LLM.

    Args:
        source_lang (str): The source language of the text.
        target_lang (str): The target language for translation.
        source_text (str): The text to be translated.

    Returns:
        str: The translated text.
    """

    # 设置系统消息，定义模型角色为特定语言对的翻译专家
    system_message = f"You are an expert linguist, specializing in translation from {source_lang} to {target_lang}."

    # 构建翻译提示
    translation_prompt = f"""This is an {source_lang} to {target_lang} translation, please provide the {target_lang} translation for this text. \
Do not provide any explanations or text apart from the translation.
{source_lang}: {source_text}

{target_lang}:"""

    # 获取翻译结果
    translation = get_completion(translation_prompt, system_message=system_message)

    return translation


def one_chunk_reflect_on_translation(
    source_lang: str,    # 源语言
    target_lang: str,    # 目标语言
    source_text: str,    # 原始文本
    translation_1: str,  # 初次翻译结果
    country: str = "",   # 目标语言所在国家（可选）
) -> str:  # 返回对翻译的反思和建议
    """
    Use an LLM to reflect on the translation, treating the entire text as one chunk.

    Args:
        source_lang (str): The source language of the text.
        target_lang (str): The target language of the translation.
        source_text (str): The original text in the source language.
        translation_1 (str): The initial translation of the source text.
        country (str): Country specified for the target language.

    Returns:
        str: The LLM's reflection on the translation, providing constructive criticism and suggestions for improvement.
    """
    #使用语言模型对翻译结果进行反思，将整个文本作为一个块处理。
    #参数:
    #        source_lang (str): 源语言
    #        target_lang (str): 目标语言
    #        source_text (str): 原始文本
    #        translation_1 (str): 初次翻译结果
    #        country (str): 目标语言使用的国家
    #返回:
    #        str: 语言模型对翻译的反思，提供建设性批评和改进建议

    # 设置系统消息，定义模型角色为特定语言对的翻译专家
    system_message = f"You are an expert linguist specializing in translation from {source_lang} to {target_lang}. \
You will be provided with a source text and its translation and your goal is to improve the translation."

    # 如果指定了国家，构建包含国家特定要求的反思提示
    if country != "":
        reflection_prompt = f"""Your task is to carefully read a source text and a translation from {source_lang} to {target_lang}, and then give constructive criticism and helpful suggestions to improve the translation. \
The final style and tone of the translation should match the style of {target_lang} colloquially spoken in {country}.

The source text and initial translation, delimited by XML tags <SOURCE_TEXT></SOURCE_TEXT> and <TRANSLATION></TRANSLATION>, are as follows:

<SOURCE_TEXT>
{source_text}
</SOURCE_TEXT>

<TRANSLATION>
{translation_1}
</TRANSLATION>

When writing suggestions, pay attention to whether there are ways to improve the translation's \n\
(i) accuracy (by correcting errors of addition, mistranslation, omission, or untranslated text),\n\
(ii) fluency (by applying {target_lang} grammar, spelling and punctuation rules, and ensuring there are no unnecessary repetitions),\n\
(iii) style (by ensuring the translations reflect the style of the source text and take into account any cultural context),\n\
(iv) terminology (by ensuring terminology use is consistent and reflects the source text domain; and by only ensuring you use equivalent idioms {target_lang}).\n\

Write a list of specific, helpful and constructive suggestions for improving the translation.
Each suggestion should address one specific part of the translation.
Output only the suggestions and nothing else."""

    # 如果未指定国家，使用通用的反思提示
    else:
        reflection_prompt = f"""Your task is to carefully read a source text and a translation from {source_lang} to {target_lang}, and then give constructive criticisms and helpful suggestions to improve the translation. \

The source text and initial translation, delimited by XML tags <SOURCE_TEXT></SOURCE_TEXT> and <TRANSLATION></TRANSLATION>, are as follows:

<SOURCE_TEXT>
{source_text}
</SOURCE_TEXT>

<TRANSLATION>
{translation_1}
</TRANSLATION>

When writing suggestions, pay attention to whether there are ways to improve the translation's \n\
(i) accuracy (by correcting errors of addition, mistranslation, omission, or untranslated text),\n\
(ii) fluency (by applying {target_lang} grammar, spelling and punctuation rules, and ensuring there are no unnecessary repetitions),\n\
(iii) style (by ensuring the translations reflect the style of the source text and take into account any cultural context),\n\
(iv) terminology (by ensuring terminology use is consistent and reflects the source text domain; and by only ensuring you use equivalent idioms {target_lang}).\n\

Write a list of specific, helpful and constructive suggestions for improving the translation.
Each suggestion should address one specific part of the translation.
Output only the suggestions and nothing else."""

    # 获取反思结果
    reflection = get_completion(reflection_prompt, system_message=system_message)
    return reflection


def one_chunk_improve_translation(
    source_lang: str,    # 源语言
    target_lang: str,    # 目标语言
    source_text: str,    # 原始文本
    translation_1: str,  # 初次翻译结果
    reflection: str,     # 对初次翻译的反思和建议
) -> str:  # 返回改进后的翻译
    """
    Use the reflection to improve the translation, treating the entire text as one chunk.

    Args:
        source_lang (str): The source language of the text.
        target_lang (str): The target language for the translation.
        source_text (str): The original text in the source language.
        translation_1 (str): The initial translation of the source text.
        reflection (str): Expert suggestions and constructive criticism for improving the translation.

    Returns:
        str: The improved translation based on the expert suggestions.
    """
    #基于反思结果改进翻译，将整个文本作为一个块处理。
    #参数:
        #source_lang (str): 源语言
        #target_lang (str): 目标语言
        #source_text (str): 原始文本
        #translation_1 (str): 初次翻译结果
        #reflection (str): 专家对翻译的建议和建设性批评
    #返回:
        #str: 基于专家建议改进后的翻译



    # 设置系统消息，定义模型角色为特定语言对的翻译编辑专家
    system_message = f"You are an expert linguist, specializing in translation editing from {source_lang} to {target_lang}."

    # 构建改进翻译的提示
    prompt = f"""Your task is to carefully read, then edit, a translation from {source_lang} to {target_lang}, taking into
account a list of expert suggestions and constructive criticisms.

The source text, the initial translation, and the expert linguist suggestions are delimited by XML tags <SOURCE_TEXT></SOURCE_TEXT>, <TRANSLATION></TRANSLATION> and <EXPERT_SUGGESTIONS></EXPERT_SUGGESTIONS> \
as follows:

<SOURCE_TEXT>
{source_text}
</SOURCE_TEXT>

<TRANSLATION>
{translation_1}
</TRANSLATION>

<EXPERT_SUGGESTIONS>
{reflection}
</EXPERT_SUGGESTIONS>

Please take into account the expert suggestions when editing the translation. Edit the translation by ensuring:

(i) accuracy (by correcting errors of addition, mistranslation, omission, or untranslated text),
(ii) fluency (by applying {target_lang} grammar, spelling and punctuation rules and ensuring there are no unnecessary repetitions), \
(iii) style (by ensuring the translations reflect the style of the source text)
(iv) terminology (inappropriate for context, inconsistent use), or
(v) other errors.

Output only the new translation and nothing else."""

    # 获取改进后的翻译
    translation_2 = get_completion(prompt, system_message)

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
        source_lang, target_lang, source_text
    )

    # 获取对初次翻译的反思
    reflection = one_chunk_reflect_on_translation(
        source_lang, target_lang, source_text, translation_1, country
    )
    # 基于反思改进翻译
    translation_2 = one_chunk_improve_translation(
        source_lang, target_lang, source_text, translation_1, reflection
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
