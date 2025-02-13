"""
术语表工具模块
提供术语表加载、索引构建和术语匹配等功能
"""
import json
import os
from collections import defaultdict
from typing import Dict, List, Optional

class GlossaryCache:
    """术语表缓存类"""
    def __init__(self, data: Dict, load_time: float):
        self.data = data
        self.load_time = load_time

# 全局缓存
_glossary_cache: Optional[GlossaryCache] = None
_index_cache: Optional[Dict] = None

def load_glossary(file_path: str = 'data/glossary.json') -> Dict:
    """
    加载术语表文件
    Args:
        file_path: 术语表JSON文件路径
    Returns:
        包含术语数据的字典
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载术语表失败: {e}")
        return {"terms": []}

def get_glossary(file_path: str = 'data/glossary.json') -> Dict:
    """
    获取最新术语表（带缓存机制）
    Args:
        file_path: 术语表文件路径
    Returns:
        术语表数据字典
    """
    global _glossary_cache
    
    # 如果缓存不存在或文件已更新，则重新加载
    if not _glossary_cache or (
        os.path.exists(file_path) and
        os.path.getmtime(file_path) > _glossary_cache.load_time
    ):
        data = load_glossary(file_path)
        _glossary_cache = GlossaryCache(
            data=data,
            load_time=os.path.getmtime(file_path) if os.path.exists(file_path) else 0
        )
    
    return _glossary_cache.data

def build_index(glossary: Dict) -> Dict[str, List]:
    """
    创建术语索引字典
    Args:
        glossary: 术语表数据
    Returns:
        索引字典：{术语文本: [相关术语列表]}
    """
    index = defaultdict(list)
    for term in glossary.get('terms', []):
        # 提取源语言文本作为索引键（支持多词术语）
        source_text = term['source']['text'].lower()
        # 将多词术语也加入索引
        index[source_text].append(term)
        # 将单词也加入索引
        for word in source_text.split():
            word = word.strip('.,!?')
            if word and word != source_text:
                index[word].append(term)
    return dict(index)

def get_index() -> Dict[str, List]:
    """
    获取术语索引（带缓存）
    Returns:
        术语索引字典
    """
    global _index_cache
    if not _index_cache:
        glossary = get_glossary()
        _index_cache = build_index(glossary)
    return _index_cache

def find_relevant_terms(text: str, max_terms: int = 15) -> List[Dict]:
    """
    在文本中查找相关术语
    Args:
        text: 待分析文本
        max_terms: 最多返回术语数量
    Returns:
        相关术语列表
    """
    index = get_index()
    found_terms = []
    
    # 文本预处理
    text = text.lower()
    
    # 1. 先尝试匹配多词术语
    for term_text in sorted(index.keys(), key=len, reverse=True):
        if ' ' in term_text and term_text in text:
            found_terms.extend(index[term_text])
    
    # 2. 再匹配单词术语
    words = set(text.split())
    for word in words:
        word = word.strip('.,!?')
        if word in index and ' ' not in word:
            found_terms.extend(index[word])
    
    # 去重并按术语长度排序
    seen = set()
    unique_terms = []
    for term in sorted(found_terms, key=lambda x: len(x['source']['text']), reverse=True):
        if term['id'] not in seen:
            seen.add(term['id'])
            unique_terms.append(term)
    
    return unique_terms[:max_terms] 