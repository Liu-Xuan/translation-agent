"""
核心翻译模块
提供翻译功能和术语集成
"""
import json
from typing import Dict, List, Optional, Tuple
from .glossary_utils import find_relevant_terms, get_glossary

def format_glossary(terms: List[Dict]) -> str:
    """
    格式化术语提示
    Args:
        terms: 术语列表
    Returns:
        格式化后的术语提示文本
    """
    if not terms:
        return ""
    
    prompt = "\n\n## 术语翻译要求\n请严格遵守以下术语对应关系："
    
    # 按术语长度排序（长术语优先）
    for term in terms:
        # 添加术语上下文提示
        context = term.get('context', '')
        context_note = f"（上下文：{context}）" if context else ""
        prompt += f"\n- 【强制】'{term['source']['text']}' → '{term['target']['text']}'{context_note}"
    
    return prompt

def mock_translate(text: str, terms: List[Dict]) -> Tuple[str, List[Dict[str, str]]]:
    """
    模拟翻译过程（仅用于测试）
    Args:
        text: 源文本
        terms: 相关术语列表
    Returns:
        翻译结果和匹配记录的元组
    """
    result = text.lower()  # 转小写以便匹配
    matches = []  # 记录匹配的术语
    
    # 按术语长度排序（长术语优先）
    sorted_terms = sorted(terms, key=lambda x: len(x['source']['text']), reverse=True)
    
    # 替换术语并记录
    for term in sorted_terms:
        source = term['source']['text'].lower()
        target = term['target']['text']
        
        # 查找所有匹配位置
        start = 0
        while True:
            pos = result.find(source, start)
            if pos == -1:
                break
                
            # 记录匹配信息
            matches.append({
                'source_text': source,
                'target_text': target,
                'position': pos,
                'context': term.get('context', ''),
                'length': len(source)
            })
            
            # 替换文本
            result = result[:pos] + target + result[pos + len(source):]
            start = pos + len(target)
    
    # 按位置排序匹配记录
    matches.sort(key=lambda x: x['position'])
    
    return result, matches

def format_translation_debug(
    source_text: str,
    translated_text: str,
    matches: List[Dict[str, str]]
) -> str:
    """
    格式化翻译调试信息
    Args:
        source_text: 源文本
        translated_text: 翻译后的文本
        matches: 术语匹配记录
    Returns:
        格式化的调试信息
    """
    debug_info = [
        "=== 翻译详情 ===",
        f"\n原文：\n{source_text}",
        f"\n译文：\n{translated_text}",
        "\n匹配的术语："
    ]
    
    if matches:
        for i, match in enumerate(matches, 1):
            debug_info.append(
                f"\n{i}. 在位置 {match['position']} 处：\n"
                f"   - 原文术语：{match['source_text']}\n"
                f"   - 译文术语：{match['target_text']}\n"
                f"   - 上下文：{match['context']}"
            )
    else:
        debug_info.append("\n（未找到匹配的术语）")
    
    return "\n".join(debug_info)

def translate(
    source_lang: str,
    target_lang: str,
    source_text: str,
    country: Optional[str] = None,
    test_mode: bool = False,
    debug: bool = False
) -> str:
    """
    执行翻译
    Args:
        source_lang: 源语言代码
        target_lang: 目标语言代码
        source_text: 待翻译文本
        country: 可选的国家/地区代码
        test_mode: 是否使用测试模式（使用mock翻译）
        debug: 是否返回调试信息
    Returns:
        翻译后的文本或调试信息
    """
    if not source_text:
        return "未找到匹配的术语" if debug else ""
        
    # 动态获取相关术语
    relevant_terms = find_relevant_terms(source_text)
    
    if test_mode:
        # 测试模式：使用mock翻译
        translated_text, matches = mock_translate(source_text, relevant_terms)
        
        if debug:
            return format_translation_debug(source_text, translated_text, matches)
        return translated_text
    
    # 构建基础提示语
    base_prompt = f"""请将以下{source_lang}文本翻译成{target_lang}。
保持原文的格式和标点符号。如有HTML标签或Markdown标记，请保留不变。
"""
    
    # 添加国家/地区特定要求
    if country:
        base_prompt += f"\n请使用{country}地区的用语习惯。"
    
    # 添加术语要求
    prompt = base_prompt + format_glossary(relevant_terms)
    
    # TODO: 实现实际的翻译调用
    # 这里需要集成具体的翻译API
    translated_text = "翻译结果示例"  # 临时占位
    
    if debug:
        return format_translation_debug(source_text, translated_text, [])
    return translated_text 