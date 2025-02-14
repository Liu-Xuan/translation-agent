import os
import sys
import json
from dotenv import load_dotenv
import translation_agent as ta
import requests
import socket
import openai

# 加载环境变量
load_dotenv()

def test_openai_connection():
    """测试与 OpenAI API 的连接"""
    # 获取代理设置
    proxies = {
        'http': os.getenv('HTTP_PROXY'),
        'https': os.getenv('HTTPS_PROXY')
    }
    print(f"当前代理设置: {proxies}")
    
    try:
        # 使用代理测试 HTTPS 请求
        print("测试与 OpenAI API 的 HTTPS 连接...")
        response = requests.get(
            "https://api.openai.com/v1/models",
            proxies=proxies,
            timeout=10,
            verify=True
        )
        if response.status_code == 401:
            print("✓ HTTPS 连接测试成功（预期的 401 未授权响应）")
            return True
        else:
            print(f"✗ HTTPS 连接测试失败: 意外的状态码 {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ HTTPS 请求失败: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        return False

def test_translation(source_text, source_lang="English", target_lang="Chinese", country="China"):
    """测试翻译功能"""
    # 检查环境变量
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("错误: 未找到 OPENAI_API_KEY 环境变量")
        return False
    else:
        print(f"✓ 找到 API Key: {api_key[:8]}...{api_key[-4:]}")
    
    # 检查代理设置
    http_proxy = os.getenv("HTTP_PROXY")
    https_proxy = os.getenv("HTTPS_PROXY")
    print(f"HTTP 代理: {http_proxy or '未设置'}")
    print(f"HTTPS 代理: {https_proxy or '未设置'}")
    
    # 设置 OpenAI 客户端
    try:
        openai.api_key = api_key
        openai.proxy = https_proxy
        models = openai.models.list()
        print("✓ OpenAI API 认证成功")
    except Exception as e:
        print(f"✗ OpenAI API 认证失败: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        return False
    
    print(f"\n开始翻译测试...")
    print(f"源语言: {source_lang}")
    print(f"目标语言: {target_lang}")
    print(f"国家/地区: {country}")
    print(f"\n源文本:\n{source_text[:200]}..." if len(source_text) > 200 else f"\n源文本:\n{source_text}")
    
    try:
        # 尝试进行翻译
        translation = ta.translate(source_lang, target_lang, source_text, country)
        print(f"\n翻译结果:\n{translation[:200]}..." if len(translation) > 200 else f"\n翻译结果:\n{translation}")
        return True
    except Exception as e:
        print(f"测试失败: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误详情: {str(e)}")
        import traceback
        print("\n完整错误堆栈:")
        traceback.print_exc()
        return False

def run_sample_tests():
    """运行示例文件测试"""
    test_files = {
        "短文本": "examples/sample-texts/sample-short1.txt",
        "长文本": "examples/sample-texts/sample-long1.txt",
        "JSON数据": "examples/sample-texts/data_points_samples.json"
    }
    
    success_count = 0
    total_tests = len(test_files)
    
    for test_name, file_path in test_files.items():
        print(f"\n=== 测试 {test_name} ===")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    # 对于 JSON 文件，我们只测试第一个样本
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        source_text = data[0].get('text', '')
                else:
                    source_text = f.read()
            
            if test_translation(source_text):
                success_count += 1
                print(f"\n✓ {test_name}测试成功")
            else:
                print(f"\n✗ {test_name}测试失败")
        except Exception as e:
            print(f"\n✗ {test_name}测试出错: {str(e)}")
    
    return success_count, total_tests

if __name__ == "__main__":
    print("=== 开始连接测试 ===")
    if not test_openai_connection():
        print("\n网络连接测试失败，请检查网络设置或代理配置")
        sys.exit(1)
    
    print("\n=== 开始基础翻译测试 ===")
    if not test_translation("Hello world! This is a test."):
        print("\n基础翻译测试失败")
        sys.exit(1)
    
    print("\n=== 开始示例文件测试 ===")
    success_count, total_tests = run_sample_tests()
    print(f"\n测试完成: 成功 {success_count}/{total_tests}") 