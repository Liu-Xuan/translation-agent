"""
翻译功能测试模块
"""
import pytest
from translation_agent.core import translate

def test_basic_translation():
    """测试基本翻译功能"""
    # 测试单个术语
    text1 = "I have an apple."
    result1 = translate("en", "zh", text1, test_mode=True, debug=True)
    print(f"\n=== 测试单个术语 ===\n{result1}")
    assert "TEST苹果TEST" in result1
    
    # 测试多词术语
    text2 = "I have a red apple."
    result2 = translate("en", "zh", text2, test_mode=True, debug=True)
    print(f"\n=== 测试多词术语 ===\n{result2}")
    assert "TEST红苹果TEST" in result2
    
    # 测试多个术语组合
    text3 = "I have a fresh red apple and a banana in my fruit basket."
    result3 = translate("en", "zh", text3, test_mode=True, debug=True)
    print(f"\n=== 测试多个术语组合 ===\n{result3}")
    assert all(term in result3 for term in [
        "TEST新鲜TEST",
        "TEST红苹果TEST",
        "TEST香蕉TEST",
        "TEST水果篮TEST"
    ])

def test_term_priority():
    """测试术语优先级"""
    # 测试长术语优先
    text = "red apple and apple"
    result = translate("en", "zh", text, test_mode=True, debug=True)
    print(f"\n=== 测试术语优先级 ===\n{result}")
    
    # 应该优先匹配"red apple"而不是单独的"apple"
    assert "TEST红苹果TEST" in result
    # 第二个"apple"应该被转换为普通的"苹果"
    assert "TEST苹果TEST" in result

def test_case_insensitive():
    """测试大小写不敏感"""
    variations = [
        "Apple",
        "APPLE",
        "aPpLe"
    ]
    
    print("\n=== 测试大小写不敏感 ===")
    for text in variations:
        result = translate("en", "zh", text, test_mode=True, debug=True)
        print(f"\n测试文本：{text}\n{result}")
        assert "TEST苹果TEST" in result

def test_context_preservation():
    """测试上下文保留"""
    text = "A fresh red apple in the fruit basket."
    result = translate("en", "zh", text, test_mode=True, debug=True)
    print(f"\n=== 测试上下文保留 ===\n{result}")
    
    # 验证所有术语都被正确替换，且保持了原有顺序
    expected_terms = [
        "TEST新鲜TEST",
        "TEST红苹果TEST",
        "TEST水果篮TEST"
    ]
    
    # 检查术语出现的顺序
    last_pos = -1
    for term in expected_terms:
        pos = result.find(term)
        assert pos > last_pos  # 确保术语按原文顺序出现
        last_pos = pos

def test_special_cases():
    """测试特殊情况"""
    # 测试重复术语
    text1 = "apple apple apple"
    result1 = translate("en", "zh", text1, test_mode=True, debug=True)
    print(f"\n=== 测试重复术语 ===\n{result1}")
    # 在译文部分检查替换次数
    translated_section = result1.split("\n译文：\n")[1].split("\n\n")[0]
    assert translated_section.count("TEST苹果TEST") == 3
    
    # 测试术语作为其他词的一部分
    text2 = "pineapple"  # 不应该匹配"apple"
    result2 = translate("en", "zh", text2, test_mode=True, debug=True)
    print(f"\n=== 测试部分匹配 ===\n{result2}")
    assert "TEST苹果TEST" not in result2
    
    # 测试空文本
    text3 = ""
    result3 = translate("en", "zh", text3, test_mode=True, debug=True)
    print(f"\n=== 测试空文本 ===\n{result3}")
    assert "未找到匹配的术语" in result3

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 