import time
from log import logger

def test_model_selection_per_chunk():
    """验证不同分块使用不同模型"""
    test_text = "Sample text " * 500  # 6000字符
    
    # 测试模型切换
    result1 = utils.translate("en", "zh", test_text, "CN", model="Pro/deepseek-ai/DeepSeek-V3")
    result2 = utils.translate("en", "zh", test_text, "CN", model="Pro/deepseek-ai/DeepSeek-R1")
    
    # 验证模型差异
    assert result1 != result2, "模型切换未生效"
    
    # 验证分块日志
    with open("test.log") as f:
        log = f.read()
        assert "使用模型: Pro/deepseek-ai/DeepSeek-V3" in log
        assert "使用模型: Pro/deepseek-ai/DeepSeek-R1" in log 

def test_large_text_translation():
    """测试大文本翻译性能"""
    # 生成测试文本
    test_text = "Sample text " * 1000  # 约10000字符
    
    # 记录开始时间
    start_time = time.time()
    
    # 使用不同模型翻译
    for model in ["Pro/deepseek-ai/DeepSeek-V3", "Pro/deepseek-ai/DeepSeek-R1"]:
        result = utils.translate(
            "en", "zh", test_text, "CN",
            model=model
        )
        
        # 验证结果
        assert len(result) > len(test_text) * 0.5, f"{model}翻译结果过短"
        
        # 记录性能指标
        duration = time.time() - start_time
        chars_per_second = len(test_text) / duration
        logger.info(f"{model}翻译性能: {chars_per_second:.2f}字符/秒") 