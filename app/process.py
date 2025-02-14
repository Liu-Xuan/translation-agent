from difflib import Differ

import docx
import gradio as gr
import pymupdf
from icecream import ic
from langchain_text_splitters import RecursiveCharacterTextSplitter
from patch import (
    calculate_chunk_size,
    model_load,
    multichunk_improve_translation,
    multichunk_initial_translation,
    multichunk_reflect_on_translation,
    num_tokens_in_string,
    one_chunk_improve_translation,
    one_chunk_initial_translation,
    one_chunk_reflect_on_translation,
)
from simplemma import simple_tokenizer


progress = gr.Progress()


def extract_text(path):
    """
    从普通文本文件中提取内容
    
    这个函数处理基本的文本文件读取，支持txt、py、json等文本格式。
    
    Args:
        path (str): 文本文件的路径
    Returns:
        str: 提取的文本内容
    """
    with open(path) as f:
        file_text = f.read()
    return file_text


def extract_pdf(path):
    """
    从PDF文件中提取文本内容
    
    使用pymupdf库提取PDF文档中的文本，支持多页PDF，
    会按顺序提取所有页面的文本并合并。
    
    Args:
        path (str): PDF文件的路径
    Returns:
        str: 提取的文本内容，包含所有页面的文本
    """
    doc = pymupdf.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def extract_docx(path):
    """
    从Word文档中提取文本内容
    
    使用python-docx库提取Word文档中的文本，
    保持段落结构，使用双换行符分隔不同段落。
    
    Args:
        path (str): Word文档的路径
    Returns:
        str: 提取的文本内容，段落之间用双换行符分隔
    """
    doc = docx.Document(path)
    data = []
    for paragraph in doc.paragraphs:
        data.append(paragraph.text)
    content = "\n\n".join(data)
    return content


def tokenize(text):
    """
    文本分词函数，保留空格和标点符号的位置信息
    
    这个函数不仅执行基本的分词，还会保持原文本的格式特征，
    包括空格和标点符号的位置，这对于准确比较文本差异很重要。
    
    Args:
        text (str): 输入文本
    Returns:
        list: 分词后的标记列表，包含单词、空格和标点符号
    """
    words = simple_tokenizer(text)
    
    if " " in text:
        tokens = []
        for word in words:
            tokens.append(word)
            if not word.startswith("'") and not word.endswith("'"):
                tokens.append(" ")
        return tokens[:-1]
    else:
        return words


def diff_texts(text1, text2):
    """
    比较两个文本之间的差异，并生成带有差异标记的文本
    
    使用Python的difflib库比较文本差异，生成易于可视化的差异标记，
    标记包括添加的文本（绿色）和删除的文本（红色）。
    
    Args:
        text1 (str): 原始文本
        text2 (str): 比较文本
    Returns:
        list: 包含(单词, 差异类型)元组的列表，差异类型包括'added'和'removed'
    """
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)

    d = Differ()
    diff_result = list(d.compare(tokens1, tokens2))

    highlighted_text = []
    for token in diff_result:
        word = token[2:]
        category = None
        if token[0] == "+":
            category = "added"
        elif token[0] == "-":
            category = "removed"
        elif token[0] == "?":
            continue

        highlighted_text.append((word, category))

    return highlighted_text


def translator(
    source_lang: str,
    target_lang: str,
    source_text: str,
    country: str,
    max_tokens: int = 1000,
):
    """
    翻译主函数，支持长文本分块翻译
    
    这是单模型翻译的主要实现，包含完整的三阶段翻译流程：
    1. 初始翻译：将源文本翻译成目标语言
    2. 翻译反思：分析初始翻译的质量，提供改进建议
    3. 改进翻译：根据反思结果生成最终的优化翻译
    
    函数会根据文本长度自动选择单块处理或多块处理模式。
    
    Args:
        source_lang: 源语言代码
        target_lang: 目标语言代码
        source_text: 待翻译的文本
        country: 目标国家/地区，用于适应当地语言风格
        max_tokens: 单次翻译的最大token数量
    
    Returns:
        tuple: (初始翻译, 翻译反思, 最终翻译)
    """
    num_tokens_in_text = num_tokens_in_string(source_text)

    ic(num_tokens_in_text)

    if num_tokens_in_text < max_tokens:
        ic("Translating text as single chunk")

        progress((1, 3), desc="First translation...")
        init_translation = one_chunk_initial_translation(
            source_lang, target_lang, source_text
        )

        progress((2, 3), desc="Reflection...")
        reflection = one_chunk_reflect_on_translation(
            source_lang, target_lang, source_text, init_translation, country
        )

        progress((3, 3), desc="Second translation...")
        final_translation = one_chunk_improve_translation(
            source_lang, target_lang, source_text, init_translation, reflection
        )

        return init_translation, reflection, final_translation

    else:
        ic("Translating text as multiple chunks")

        token_size = calculate_chunk_size(
            token_count=num_tokens_in_text, token_limit=max_tokens
        )

        ic(token_size)

        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            model_name="gpt-4",
            chunk_size=token_size,
            chunk_overlap=0,
        )

        source_text_chunks = text_splitter.split_text(source_text)

        progress((1, 3), desc="First translation...")
        translation_1_chunks = multichunk_initial_translation(
            source_lang, target_lang, source_text_chunks
        )

        init_translation = "".join(translation_1_chunks)

        progress((2, 3), desc="Reflection...")
        reflection_chunks = multichunk_reflect_on_translation(
            source_lang,
            target_lang,
            source_text_chunks,
            translation_1_chunks,
            country,
        )

        reflection = "".join(reflection_chunks)

        progress((3, 3), desc="Second translation...")
        translation_2_chunks = multichunk_improve_translation(
            source_lang,
            target_lang,
            source_text_chunks,
            translation_1_chunks,
            reflection_chunks,
        )

        final_translation = "".join(translation_2_chunks)

        return init_translation, reflection, final_translation


def translator_sec(
    endpoint2: str,
    base2: str,
    model2: str,
    api_key2: str,
    source_lang: str,
    target_lang: str,
    source_text: str,
    country: str,
    max_tokens: int = 1000,
):
    """
    使用两个不同模型的翻译函数
    
    这是双模型翻译的主要实现，通过切换不同的模型来提高翻译质量：
    1. 使用第一个模型进行初始翻译
    2. 切换到第二个模型进行翻译反思
    3. 使用第二个模型生成最终翻译
    
    这种方法可以结合不同模型的优势，通常可以获得更好的翻译效果。
    
    Args:
        endpoint2: 第二个API端点名称
        base2: 第二个API的基础URL
        model2: 第二个翻译模型名称
        api_key2: 第二个API的访问密钥
        source_lang: 源语言代码
        target_lang: 目标语言代码
        source_text: 待翻译的文本
        country: 目标国家/地区
        max_tokens: 单次翻译的最大token数量
    
    Returns:
        tuple: (初始翻译, 翻译反思, 最终翻译)
    """
    num_tokens_in_text = num_tokens_in_string(source_text)

    ic(num_tokens_in_text)

    if num_tokens_in_text < max_tokens:
        ic("Translating text as single chunk")

        progress((1, 3), desc="First translation...")
        init_translation = one_chunk_initial_translation(
            source_lang, target_lang, source_text
        )

        try:
            model_load(endpoint2, base2, model2, api_key2)
        except Exception as e:
            raise gr.Error(f"An unexpected error occurred: {e}") from e

        progress((2, 3), desc="Reflection...")
        reflection = one_chunk_reflect_on_translation(
            source_lang, target_lang, source_text, init_translation, country
        )

        progress((3, 3), desc="Second translation...")
        final_translation = one_chunk_improve_translation(
            source_lang, target_lang, source_text, init_translation, reflection
        )

        return init_translation, reflection, final_translation

    else:
        ic("Translating text as multiple chunks")

        token_size = calculate_chunk_size(
            token_count=num_tokens_in_text, token_limit=max_tokens
        )

        ic(token_size)

        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            model_name="gpt-4",
            chunk_size=token_size,
            chunk_overlap=0,
        )

        source_text_chunks = text_splitter.split_text(source_text)

        progress((1, 3), desc="First translation...")
        translation_1_chunks = multichunk_initial_translation(
            source_lang, target_lang, source_text_chunks
        )

        init_translation = "".join(translation_1_chunks)

        try:
            model_load(endpoint2, base2, model2, api_key2)
        except Exception as e:
            raise gr.Error(f"An unexpected error occurred: {e}") from e

        progress((2, 3), desc="Reflection...")
        reflection_chunks = multichunk_reflect_on_translation(
            source_lang,
            target_lang,
            source_text_chunks,
            translation_1_chunks,
            country,
        )

        reflection = "".join(reflection_chunks)

        progress((3, 3), desc="Second translation...")
        translation_2_chunks = multichunk_improve_translation(
            source_lang,
            target_lang,
            source_text_chunks,
            translation_1_chunks,
            reflection_chunks,
        )

        final_translation = "".join(translation_2_chunks)

        return init_translation, reflection, final_translation
