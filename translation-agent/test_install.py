import translation_agent as ta

def test_translation():
    source_text = "Hello world! This is a test."
    source_lang = "English"
    target_lang = "Chinese"
    country = "China"
    
    try:
        translation = ta.translate(source_lang, target_lang, source_text, country)
        print(f"翻译结果: {translation}")
        return True
    except Exception as e:
        print(f"测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    test_translation() 