"""
使用小爱API的翻译流程测试模块
包含基础测试和完整流程测试
"""
import os
import pytest
from dotenv import load_dotenv
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 添加src目录到Python路径
src_path = str(Path(project_root) / 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

# 导入必要的模块
from app.patch import model_load, get_completion
from translation_agent.core import translate, mock_translate, format_translation_debug
from translation_agent.utils import (
    one_chunk_initial_translation,
    one_chunk_reflect_on_translation,
    one_chunk_improve_translation,
    format_translation_prompt_with_terms,
    format_reflection_prompt_with_terms,
    format_improvement_prompt_with_terms
)

# 加载环境变量
load_dotenv()

def setup_xiaoai_api():
    """初始化小爱API配置"""
    model_load(
        endpoint="XiaoAI",
        base_url=os.getenv("XIAOAI_API_BASE", "https://xiaoai.plus/v1"),
        model="gpt-4-1106-preview",
        api_key=os.getenv("XIAOAI_API_KEY"),
    )

def test_basic_translation_xiaoai():
    """使用小爱API测试基本翻译功能"""
    setup_xiaoai_api()
    
    print("\n=== 基础翻译测试（小爱API）===")
    
    # 测试简单翻译
    text1 = "Hello, how are you?"
    result1 = translate("en", "zh", text1)
    print(f"\n测试文本1：{text1}")
    print(f"翻译结果：{result1}")
    assert any(word in result1 for word in ["你好", "您好"])
    
    # 测试带格式的文本
    text2 = "**Important**: Please *read* carefully."
    result2 = translate("en", "zh", text2)
    print(f"\n测试文本2：{text2}")
    print(f"翻译结果：{result2}")
    assert "**" in result2  # 检查格式保留
    assert "*" in result2   # 检查格式保留

def test_complex_translation_xiaoai():
    """使用小爱API测试复杂文本翻译"""
    setup_xiaoai_api()
    
    print("\n=== 复杂文本翻译测试（小爱API）===")
    
    # 测试复杂格式文本
    source_text = """
    # User Guide
    
    ## Introduction
    
    This document contains:
    
    1. **Basic Information**
       - *Important* notes
       - Key points
    
    2. *Advanced* Topics
       - Detailed explanation
       - Technical terms
    
    > Please read carefully.
    
    ```python
    def hello():
        print("Hello, World!")
    ```
    """
    
    result = translate("en", "zh", source_text)
    print(f"\n复杂文本翻译结果：\n{result}")
    
    # 验证格式保留
    assert "#" in result      # Markdown标题
    assert "##" in result     # 二级标题
    assert "**" in result     # 粗体
    assert "*" in result      # 斜体
    assert "`" in result      # 代码
    assert ">" in result      # 引用
    assert "1." in result     # 编号列表
    assert "-" in result      # 无序列表

def test_full_translation_workflow_xiaoai():
    """使用小爱API测试完整翻译工作流程"""
    setup_xiaoai_api()
    
    print("\n=== 完整翻译流程测试（小爱API）===")
    
    source_text = """
    # Product Documentation
    
    ## Overview
    
    This document describes our product features:
    
    1. **Main Features**:
       - User interface
       - System settings
       - Advanced options
    
    2. *Technical Details*:
       - Configuration
       - Performance
       - Security
    """
    
    print("\n原文：")
    print(source_text)
    
    # 1. 初始翻译
    print("\n=== 第一阶段：初始翻译 ===")
    translation_1 = one_chunk_initial_translation(
        "en", "zh", source_text, "CN"
    )
    print("\n初始翻译结果：")
    print(translation_1)
    
    # 验证初始翻译
    assert any(word in translation_1 for word in ["概览", "概述", "总览"])
    assert "产品" in translation_1
    assert "文档" in translation_1
    
    # 2. 翻译反思
    print("\n=== 第二阶段：翻译反思 ===")
    reflection = one_chunk_reflect_on_translation(
        "en", "zh", source_text, translation_1, "CN"
    )
    print("\n反思结果：")
    print(reflection)
    
    # 3. 翻译改进
    print("\n=== 第三阶段：翻译改进 ===")
    translation_2 = one_chunk_improve_translation(
        "en", "zh", source_text, translation_1, reflection, "CN"
    )
    print("\n最终翻译结果：")
    print(translation_2)
    
    # 验证格式保留
    assert "#" in translation_2     # 标题格式
    assert "##" in translation_2    # 二级标题
    assert "**" in translation_2    # 粗体
    assert "*" in translation_2     # 斜体
    assert "1." in translation_2    # 编号列表
    assert "-" in translation_2     # 无序列表
    
    # 验证翻译质量（使用更灵活的断言）
    assert any(word in translation_2 for word in ["概览", "概述", "总览"])
    assert "产品" in translation_2
    assert "文档" in translation_2
    assert any(word in translation_2 for word in ["功能", "特性", "特点"])
    assert any(word in translation_2 for word in ["技术", "技术性", "技术细节"])

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 