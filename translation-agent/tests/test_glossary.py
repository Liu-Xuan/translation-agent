"""
术语系统测试模块
"""
import pytest
from translation_agent.glossary_utils import (
    load_glossary,
    get_glossary,
    build_index,
    get_index,
    find_relevant_terms
)

def test_load_glossary():
    """测试术语表加载功能"""
    glossary = load_glossary('data/glossary.json')
    assert glossary is not None
    assert 'terms' in glossary
    assert len(glossary['terms']) > 0
    
    # 验证术语结构
    term = glossary['terms'][0]
    assert 'id' in term
    assert 'source' in term
    assert 'target' in term
    assert 'context' in term

def test_build_index():
    """测试索引构建功能"""
    glossary = load_glossary('data/glossary.json')
    index = build_index(glossary)
    
    # 验证索引结构
    assert isinstance(index, dict)
    assert len(index) > 0
    
    # 验证完整术语索引
    key = 'artificial intelligence'
    assert key in index
    assert len(index[key]) > 0
    assert index[key][0]['target']['text'] == '人工智能'
    
    # 验证单词索引
    assert 'intelligence' in index
    assert 'artificial' in index

def test_find_relevant_terms():
    """测试术语匹配功能"""
    # 测试完整匹配
    text1 = "Artificial Intelligence is amazing."
    terms1 = find_relevant_terms(text1)
    assert len(terms1) > 0
    assert terms1[0]['source']['text'].lower() == 'artificial intelligence'
    
    # 测试部分匹配
    text2 = "The intelligence of machines."
    terms2 = find_relevant_terms(text2)
    assert len(terms2) > 0
    assert any('intelligence' in term['source']['text'].lower() for term in terms2)
    
    # 测试多个术语匹配
    text3 = """
    Artificial Intelligence and Machine Learning are transforming the world.
    Deep learning, a subset of machine learning, uses neural networks to process data.
    Natural Language Processing is one of the key applications.
    """
    terms3 = find_relevant_terms(text3)
    assert len(terms3) > 0
    
    # 验证长术语优先
    term_lengths = [len(term['source']['text']) for term in terms3]
    assert term_lengths == sorted(term_lengths, reverse=True)
    
    # 验证特定术语存在
    term_texts = [term['source']['text'].lower() for term in terms3]
    assert 'artificial intelligence' in term_texts
    assert 'machine learning' in term_texts
    assert 'natural language processing' in term_texts

def test_cache_mechanism():
    """测试缓存机制"""
    # 首次加载
    glossary1 = get_glossary()
    index1 = get_index()
    
    # 再次加载（应该使用缓存）
    glossary2 = get_glossary()
    index2 = get_index()
    
    # 验证缓存有效性
    assert glossary1 is glossary2
    assert index1 is index2

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 