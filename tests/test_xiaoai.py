import os
import pytest
from dotenv import load_dotenv
import sys
sys.path.append(".")  # 添加项目根目录到Python路径

from app.patch import model_load, get_completion

# 加载环境变量
load_dotenv()

# 测试模型列表
TEST_MODELS = [
    "gpt-4-1106-preview",
    "gpt-3.5-turbo",
    "claude-3-sonnet-20240229"
]

def test_xiaoai_connection():
    """测试小爱API连接"""
    # 初始化API客户端
    model_load(
        endpoint="XiaoAI",
        base_url=os.getenv("XIAOAI_API_BASE", "https://xiaoai.plus/v1"),
        model="gpt-3.5-turbo",
        api_key=os.getenv("XIAOAI_API_KEY"),
    )
    
    # 测试简单对话
    response = get_completion(
        prompt="你好，这是一个测试消息。",
        system_message="你是一个翻译助手。",
    )
    
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0

def test_xiaoai_models():
    """测试小爱API支持的模型"""
    for model in TEST_MODELS:
        # 初始化API客户端
        model_load(
            endpoint="XiaoAI",
            base_url=os.getenv("XIAOAI_API_BASE", "https://xiaoai.plus/v1"),
            model=model,
            api_key=os.getenv("XIAOAI_API_KEY"),
        )
        
        try:
            # 测试翻译功能
            response = get_completion(
                prompt="Translate this text to Chinese: Hello, world!",
                system_message="你是一个专业的翻译助手。",
            )
            
            assert response is not None
            assert isinstance(response, str)
            assert len(response) > 0
            print(f"✅ 模型 {model} 测试成功")
            
        except Exception as e:
            print(f"❌ 模型 {model} 测试失败: {str(e)}")
            raise

def test_xiaoai_translation():
    """测试小爱API的翻译功能"""
    # 初始化API客户端
    model_load(
        endpoint="XiaoAI",
        base_url=os.getenv("XIAOAI_API_BASE", "https://xiaoai.plus/v1"),
        model="gpt-4-1106-preview",
        api_key=os.getenv("XIAOAI_API_KEY"),
    )
    
    # 测试英译中
    en_to_zh = get_completion(
        prompt="Translate this text to Chinese: The weather is nice today.",
        system_message="你是一个专业的翻译助手。请将文本翻译成中文。",
    )
    print(f"\n英译中结果: {en_to_zh}")
    assert any(word in en_to_zh for word in ["天气", "今天"])
    
    # 测试中译英
    zh_to_en = get_completion(
        prompt="将这段文字翻译成英文：今天是个好天气。",
        system_message="You are a professional translator. Please translate the text to English.",
    )
    print(f"\n中译英结果: {zh_to_en}")
    assert any(word in zh_to_en.lower() for word in ["weather", "today", "nice", "good"])

if __name__ == "__main__":
    print("开始测试小爱API...")
    test_xiaoai_connection()
    print("✅ API连接测试通过")
    
    test_xiaoai_models()
    print("✅ 模型可用性测试通过")
    
    test_xiaoai_translation()
    print("✅ 翻译功能测试通过")
    
    print("\n所有测试完成！") 