import translation_agent as ta

# 测试翻译
source_text = "Hello world! This is a test."
source_lang = "English"
target_lang = "Spanish"
country = "Mexico"

translation = ta.translate(source_lang, target_lang, source_text, country)
print(translation) 