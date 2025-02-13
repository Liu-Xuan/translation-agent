"""
翻译功能测试模块
包含基础测试和完整流程测试
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

def test_complex_text_translation():
    """测试复杂文本的翻译处理"""
    # 包含多种复杂情况的测试文本
    source_text = """
    # Technical Specifications
    
    The fresh red apple processing system includes:
    
    1. **Primary Components**:
       - Double red apple sorting machine
       - Fresh banana conveyor
       - Premium fruit basket assembly
    
    2. *Key Features*:
       - Processes 1000 red apples per hour
       - Fresh fruit quality monitoring
       - Multiple fruit basket sizes
    
    > Note: All fresh fruits are stored in our special fruit basket.
    
    ```python
    def process_apple():
        # This is a code example
        fresh_apple = get_fresh_apple()
        return fresh_apple
    ```
    
    For more information about our fresh red apples and bananas, 
    please check the fruit basket catalog.
    """
    
    print("\n=== 测试复杂文本翻译 ===")
    
    # 使用测试模式进行翻译
    result = translate(
        "en", "zh", source_text, country="CN",
        test_mode=True, debug=True
    )
    print(f"\n翻译结果：\n{result}")
    
    # 验证复杂文本的处理
    # 1. 验证术语翻译
    assert "TEST红苹果TEST" in result
    assert "TEST香蕉TEST" in result
    assert "TEST水果篮TEST" in result
    assert "TEST新鲜TEST" in result
    
    # 2. 验证格式保留
    assert "#" in result  # Markdown标题
    assert "**" in result  # 粗体
    assert "*" in result   # 斜体
    assert "`" in result   # 代码块
    assert ">" in result   # 引用
    assert "1." in result  # 有序列表
    assert "-" in result   # 无序列表
    
    # 3. 验证代码块保留
    assert "```python" in result
    assert "def" in result
    assert "return" in result

def test_mixed_content_translation():
    """测试混合内容的翻译"""
    # 混合HTML和Markdown的测试文本
    source_text = """
    <div class="product">
        # Fresh Fruit Collection
        
        <section class="description">
            Our premium fresh red apple and banana selection:
            
            - *Fresh* red apples from organic farms
            - **Premium** bananas
            - <em>Elegant</em> fruit basket design
        </section>
        
        <footer>
            > All fresh fruits are carefully selected.
            > Store in fruit basket for best results.
        </footer>
    </div>
    """
    
    print("\n=== 测试混合内容翻译 ===")
    
    # 使用测试模式翻译
    result = translate(
        "en", "zh", source_text, country="CN",
        test_mode=True, debug=True
    )
    print(f"\n翻译结果：\n{result}")
    
    # 验证混合内容的处理
    # 1. 验证HTML标签保留
    assert "<div" in result
    assert "<section" in result
    assert "<footer" in result
    assert "<em>" in result
    
    # 2. 验证Markdown格式保留
    assert "#" in result
    assert "-" in result
    assert "*" in result
    assert ">" in result
    
    # 3. 验证术语翻译
    assert "TEST红苹果TEST" in result
    assert "TEST香蕉TEST" in result
    assert "TEST水果篮TEST" in result
    assert "TEST新鲜TEST" in result

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 