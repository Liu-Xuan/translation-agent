"""
测试 utils.py 中的翻译功能
包括术语处理、格式保留和翻译质量
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

from app.patch import model_load
from translation_agent.utils import (
    format_translation_prompt_with_terms,
    format_reflection_prompt_with_terms,
    format_improvement_prompt_with_terms,
    one_chunk_initial_translation,
    one_chunk_reflect_on_translation,
    one_chunk_improve_translation,
    one_chunk_translate_text
)

# 加载环境变量
load_dotenv()

def setup_module():
    """初始化测试环境"""
    model_load(
        endpoint="XiaoAI",
        base_url=os.getenv("XIAOAI_API_BASE", "https://xiaoai.plus/v1"),
        model="gpt-4-1106-preview",
        api_key=os.getenv("XIAOAI_API_KEY"),
    )

def test_format_prompts():
    """测试提示词格式化功能"""
    # 测试数据
    source_text = """
    # Technical Documentation
    
    ## Key Terms
    1. **API**: Application Programming Interface
    2. *REST*: Representational State Transfer
    
    > Important: Please follow the guidelines.
    """
    
    # 测试翻译提示
    translation_prompt = format_translation_prompt_with_terms(
        source_lang="en",
        target_lang="zh",
        source_text=source_text,
        country="CN"
    )
    
    # 验证翻译提示包含必要元素
    assert "翻译要求" in translation_prompt
    assert "术语一致性" in translation_prompt
    assert "格式保留" in translation_prompt
    assert "CN地区" in translation_prompt
    
    # 生成一个模拟翻译
    mock_translation = """
    # 技术文档
    
    ## 关键术语
    1. **API**: 应用程序编程接口
    2. *REST*: 表述性状态转移
    
    > 重要提示：请遵循指南。
    """
    
    # 测试反思提示
    reflection_prompt = format_reflection_prompt_with_terms(
        source_lang="en",
        target_lang="zh",
        source_text=source_text,
        translation=mock_translation,
        country="CN"
    )
    
    # 验证反思提示包含必要元素
    assert "术语翻译" in reflection_prompt
    assert "翻译质量" in reflection_prompt
    assert "格式规范" in reflection_prompt
    assert "地区适配" in reflection_prompt
    
    # 生成一个模拟反思
    mock_reflection = """
    1. 术语翻译准确，保持了专业性
    2. 格式完整保留
    3. 建议优化表达的自然度
    """
    
    # 测试改进提示
    improvement_prompt = format_improvement_prompt_with_terms(
        source_lang="en",
        target_lang="zh",
        source_text=source_text,
        translation=mock_translation,
        reflection=mock_reflection,
        country="CN"
    )
    
    # 验证改进提示包含必要元素
    assert "改进重点" in improvement_prompt
    assert "术语处理" in improvement_prompt
    assert "翻译质量" in improvement_prompt
    assert "格式规范" in improvement_prompt

def test_translation_workflow():
    """测试完整翻译工作流程"""
    # 测试数据
    source_text = """
    # API Documentation
    
    ## Overview
    This document describes the **REST API** interface.
    
    ### Features
    1. *Authentication*
    2. **Rate Limiting**
    3. Error Handling
    
    > Note: All API calls require authentication.
    """
    
    print("\n=== 测试翻译工作流 ===")
    
    # 1. 初始翻译
    print("\n第一阶段：初始翻译")
    translation_1 = one_chunk_initial_translation(
        source_lang="en",
        target_lang="zh",
        source_text=source_text,
        country="CN"
    )
    print(f"\n初始翻译结果：\n{translation_1}")
    
    # 验证初始翻译
    assert "#" in translation_1  # 保留标题格式
    assert "**" in translation_1  # 保留加粗格式
    assert "*" in translation_1  # 保留斜体格式
    assert "API" in translation_1  # 保留专业术语
    
    # 2. 翻译反思
    print("\n第二阶段：翻译反思")
    reflection = one_chunk_reflect_on_translation(
        source_lang="en",
        target_lang="zh",
        source_text=source_text,
        translation_1=translation_1,
        country="CN"
    )
    print(f"\n反思结果：\n{reflection}")
    
    # 验证反思内容
    assert len(reflection) > 0
    assert any(term in reflection.lower() for term in ["术语", "格式", "翻译"])
    
    # 3. 翻译改进
    print("\n第三阶段：翻译改进")
    translation_2 = one_chunk_improve_translation(
        source_lang="en",
        target_lang="zh",
        source_text=source_text,
        translation_1=translation_1,
        reflection=reflection,
        country="CN"
    )
    print(f"\n改进后的翻译：\n{translation_2}")
    
    # 验证改进后的翻译
    assert "#" in translation_2  # 保留标题格式
    assert "**" in translation_2  # 保留加粗格式
    assert "*" in translation_2  # 保留斜体格式
    assert "API" in translation_2  # 保留专业术语
    assert ">" in translation_2  # 保留引用格式

def test_complete_translation():
    """测试完整的翻译功能"""
    # 测试数据
    source_text = """
    # System Architecture
    
    ## Components
    1. **Frontend**: User interface
    2. *Backend*: Server logic
    3. **Database**: Data storage
    
    ### Technical Stack
    - React.js
    - Node.js
    - MongoDB
    
    > Important: Follow coding standards.
    
    ```python
    def example():
        print("Hello, World!")
    ```
    """
    
    print("\n=== 测试完整翻译功能 ===")
    
    # 执行完整翻译
    final_translation = one_chunk_translate_text(
        source_lang="en",
        target_lang="zh",
        source_text=source_text,
        country="CN"
    )
    
    print(f"\n最终翻译结果：\n{final_translation}")
    
    # 验证翻译结果
    assert "#" in final_translation  # 标题格式
    assert "**" in final_translation  # 加粗格式
    assert "*" in final_translation  # 斜体格式
    assert "```" in final_translation  # 代码块
    assert "def" in final_translation  # 保留代码
    assert "print" in final_translation  # 保留函数名
    assert "MongoDB" in final_translation  # 保留专有名词
    assert ">" in final_translation  # 引用格式

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 