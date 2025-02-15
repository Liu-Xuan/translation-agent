"""
测试波音737 MAX技术文档的翻译
重点关注专业术语和格式保留
"""
import os
import pytest
from dotenv import load_dotenv
import sys
from pathlib import Path
import logging
import json
import time
from datetime import datetime
import asyncio
from openai import OpenAI
from openai import AsyncOpenAI
import re

# 加载环境变量
load_dotenv()

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# 添加项目根目录到Python路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

class DeepSeekClient:
    """DeepSeek模型客户端，支持同步和异步操作"""
    def __init__(self):
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("请在.env文件中设置DASHSCOPE_API_KEY环境变量")
            
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        # 同步客户端
        self.sync_client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=5,
            timeout=300.0  # 增加到5分钟
        )
        
        # 异步客户端
        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=300.0  # 增加到5分钟
        )
        
        # 模型配置 - 移除重复的 stream 参数
        self.model_configs = {
            "deepseek-r1": {
                "temperature": 0.3,
                "top_p": 0.8,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0
            },
            "deepseek-v3": {
                "temperature": 0.7,
                "top_p": 0.6,
                "presence_penalty": 0.95,
                "frequency_penalty": 0.0
            }
        }
    
    async def translate_text_stream(self, text: str, model: str = "deepseek-v3") -> str:
        """流式翻译文本"""
        try:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=[{'role': 'user', 'content': text}],
                stream=True,  # 在这里显式设置 stream 参数
                **self.model_configs[model]
            )
            
            full_content = []
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content.append(content)
                    print(content, end='', flush=True)
            
            return ''.join(full_content)
            
        except Exception as e:
            logger.error(f"流式翻译失败: {str(e)}")
            raise

class TranslationRecorder:
    """翻译过程记录器"""
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.report_path = self.output_dir / f"translation_process_{self.timestamp}.md"
        self.current_section = None
        
        # 初始化文档
        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write(f"# 波音737 MAX技术文档翻译过程记录\n\n")
            f.write(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    def add_section(self, section_name: str):
        """添加新的章节"""
        self.current_section = section_name
        with open(self.report_path, 'a', encoding='utf-8') as f:
            f.write(f"\n## {section_name}\n\n")
    
    def add_content(self, content: str):
        """添加内容到当前章节"""
        with open(self.report_path, 'a', encoding='utf-8') as f:
            f.write(f"{content}\n\n")
    
    def add_step_result(self, step_name: str, result: str):
        """记录步骤结果"""
        with open(self.report_path, 'a', encoding='utf-8') as f:
            f.write(f"### {step_name}\n\n")
            f.write(f"```\n{result}\n```\n\n")
    
    def add_validation_result(self, validation_items: dict):
        """记录验证结果"""
        with open(self.report_path, 'a', encoding='utf-8') as f:
            f.write("### 验证结果\n\n")
            for item, status in validation_items.items():
                f.write(f"- [{status}] {item}\n")
            f.write("\n")
    
    def add_term_analysis(self, source_text: str):
        """添加术语匹配分析"""
        # 从术语表中获取术语
        with open(Path(project_root) / "data/glossary.json", 'r', encoding='utf-8') as f:
            glossary = json.load(f)
        terms = glossary['terms']
        
        # 统计术语使用频率
        term_counts = {}
        for term in terms:
            source_text_lower = source_text.lower()
            term_text = term['source']['text'].lower()
            count = source_text_lower.count(term_text)
            if count > 0:  # 只记录在源文本中出现的术语
                term_counts[term['source']['text']] = count
        
        # 过滤掉未使用的术语
        used_terms = [term for term in terms if term['source']['text'] in term_counts]
        
        # 按使用频率排序
        sorted_terms = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)
        
        with open(self.report_path, 'a', encoding='utf-8') as f:
            f.write("## 术语匹配分析\n\n")
            
            # 记录识别到的关键术语
            f.write("### 识别到的关键术语\n")
            f.write("1. **文档标题相关**\n")
            title_terms = [t for t in used_terms if any(x in t['source']['text'].lower() for x in ['description', 'action', 'list', 'digest'])]
            for term in title_terms:
                f.write(f"   - `{term['source']['text']}` → `{term['target']['text']}`\n")
            
            f.write("\n2. **技术术语**\n")
            tech_terms = [t for t in used_terms if any(x in t['source']['text'].lower() for x in ['serial', 'fault', 'software', 'deck', 'service'])]
            for term in tech_terms:
                f.write(f"   - `{term['source']['text']}` → `{term['target']['text']}`\n")
            
            f.write("\n3. **通用术语**\n")
            general_terms = [t for t in used_terms if t not in title_terms and t not in tech_terms]
            for term in general_terms:
                f.write(f"   - `{term['source']['text']}` → `{term['target']['text']}`\n")
            
            # 记录术语使用统计
            f.write("\n### 术语使用统计\n")
            f.write(f"- 总识别术语数：{len(used_terms)}个\n")  # 修改为使用实际使用的术语数量
            f.write("- 高频术语：\n")
            for term, count in sorted_terms[:3]:
                f.write(f"  * `{term}`（出现{count}次）\n")
            
            # 记录专有名词保留
            f.write("- 专有名词保留：\n")
            abbrs = [t['source']['text'] for t in used_terms if '(' in t['source']['text']]  # 只显示使用的术语中的缩写
            for abbr in abbrs:
                if '(' in abbr:
                    short_form = abbr[abbr.find('(')+1:abbr.find(')')]
                    f.write(f"  * {short_form}\n")
    
    def add_prompt_analysis(self):
        """添加提示词嵌入分析"""
        with open(self.report_path, 'a', encoding='utf-8') as f:
            f.write("\n## 提示词嵌入分析\n\n")
            
            # 翻译提示词结构
            f.write("### 翻译提示词结构\n")
            f.write("```\n")
            f.write("""请将以下英文文本翻译成中文。
保持原文的格式和标点符号。如有HTML标签或Markdown标记，请保留不变。

翻译要求：
1. 准确性：确保翻译准确传达原文含义
2. 格式保留：保持所有格式标记和特殊符号
3. 术语一致性：严格遵守术语表要求
4. 语言自然度：确保译文符合目标语言表达习惯
5. 地区适配：使用CN地区的用语习惯和表达方式

## 术语表要求：
- 【强制】'FLEET TEAM DIGEST' → 'FLEET TEAM DIGEST（FTD）'（上下文：机队技术文件摘要）
- 【强制】'Revision Description' → '改版说明'（上下文：文档修订信息）
- 【强制】'Final Action' → '最终措施'（上下文：维修或故障处理的最终解决方案）
[...其他术语...]

请严格遵守以上术语表的翻译要求。对于术语的处理：
1. 优先使用术语表中的对应翻译
2. 保持术语的一致性
3. 注意术语的上下文含义
4. 保留术语的专业性

源文本：
[源文本内容]
```\n""")
            
            # 反思提示词结构
            f.write("\n### 反思提示词结构\n")
            f.write("```\n")
            f.write("""请分析以下从英文到中文的翻译，重点关注以下方面：

1. 术语翻译：
   - 术语使用的准确性
   - 术语翻译的一致性
   - 术语上下文的适当性
   - 专业术语的规范性

2. 翻译质量：
   - 内容的完整性
   - 含义的准确性
   - 表达的自然度
   - 语言的流畅度

3. 格式规范：
   - 格式标记的保留
   - 标点符号的正确性
   - 特殊标记的处理
   - 排版的一致性

4. 地区适配：
   - 符合CN地区的语言习惯
   - 使用地区常用表达
   - 考虑文化差异

## 需要重点关注的术语：
[术语列表]

请特别注意：
1. 检查每个术语是否按照术语表正确翻译
2. 验证术语在上下文中的使用是否恰当
3. 确认术语的专业性是否得到保持
4. 评估术语翻译的一致性

原文：
[原文内容]

当前译文：
[译文内容]
```\n""")
            
            # 改进提示词结构
            f.write("\n### 改进提示词结构\n")
            f.write("```\n")
            f.write("""请根据以下反馈改进这段从英文到中文的翻译。

改进重点：
1. 术语处理
   - 严格遵守术语表要求
   - 保持术语翻译一致性
   - 确保术语使用准确
   - 维护专业术语规范

2. 翻译质量
   - 提高表达准确性
   - 增强语言流畅度
   - 保持内容完整性
   - 改进表达自然度

3. 格式规范
   - 保持格式标记完整
   - 规范标点符号使用
   - 正确处理特殊标记
   - 统一排版风格

4. 地区适配
   - 符合CN地区表达习惯
   - 使用地区常用用语
   - 注意文化差异处理

## 术语表要求：
[术语列表]

术语处理原则：
1. 必须使用术语表规定的译法
2. 确保术语在上下文中使用恰当
3. 保持术语翻译的专业性
4. 维护术语使用的一致性

原文：
[原文内容]

当前译文：
[译文内容]

改进建议：
[改进建议内容]

请根据以上要求提供改进后的译文。注意：
1. 认真考虑所有改进建议
2. 确保术语使用准确
3. 保持格式完整性
4. 提升整体翻译质量
```\n""")

def split_markdown_sections(text: str, max_length: int = 200000) -> list[str]:
    """
    将Markdown文本按章节分块，保持文档结构完整性
    """
    sections = []
    current_section = []
    current_length = 0
    
    # 按行分割，保持Markdown格式
    lines = text.split('\n')
    
    for line in lines:
        # 如果是标题行或当前块太大，开始新的块
        if (line.startswith('#') and current_length > 0) or current_length + len(line) > max_length:
            if current_section:
                sections.append('\n'.join(current_section))
                current_section = []
                current_length = 0
        
        current_section.append(line)
        current_length += len(line) + 1  # +1 for newline
    
    # 添加最后一个块
    if current_section:
        sections.append('\n'.join(current_section))
    
    return sections

async def translate_chunk(client: DeepSeekClient, text: str, model: str) -> str:
    """翻译单个文本块"""
    prompt = f"""请将以下英文文本翻译成中文。
保持原文的格式和标点符号。如有HTML标签或Markdown标记，请保留不变。

源文本：
{text}
"""
    return await client.translate_text_stream(prompt, model)

async def translate_document(client: DeepSeekClient, text: str, model: str) -> str:
    """分块翻译整个文档"""
    chunks = split_markdown_sections(text)
    logger.info(f"文档已分割为 {len(chunks)} 个块")
    
    translated_chunks = []
    for i, chunk in enumerate(chunks, 1):
        logger.info(f"正在翻译第 {i}/{len(chunks)} 块...")
        translated_chunk = await translate_chunk(client, chunk, model)
        translated_chunks.append(translated_chunk)
        
    return '\n'.join(translated_chunks)

async def reflect_on_translation(client: DeepSeekClient, source: str, translation: str) -> str:
    """使用deepseek-r1模型反思翻译质量"""
    prompt = f"""请分析以下从英文到中文的翻译：

原文：
{source}

译文：
{translation}

请从术语准确性、表达流畅性、格式保留等方面进行分析，并给出具体的改进建议。
"""
    return await client.translate_text_stream(prompt, "deepseek-r1")

async def improve_translation(client: DeepSeekClient, source: str, translation: str, reflection: str) -> str:
    """根据反思结果改进翻译"""
    prompt = f"""请根据以下反馈改进这段翻译：

原文：
{source}

当前译文：
{translation}

改进建议：
{reflection}

请提供改进后的译文：
"""
    return await client.translate_text_stream(prompt, "deepseek-v3")

@pytest.mark.asyncio
async def test_boeing_doc_translation():
    """测试波音文档翻译流程"""
    logger.info("="*50)
    logger.info("开始波音文档翻译测试")
    logger.info("="*50)
    
    # 初始化客户端和记录器
    client = DeepSeekClient()
    recorder = TranslationRecorder(Path(project_root) / "test_reports")
    
    # 读取源文档
    doc_path = Path(project_root) / "testcases/737MAX-FTD-46-19002_Doc_01092023/auto/737MAX-FTD-46-19002_Doc_01092023.md"
    
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            source_text = f.read()
        
        # 记录源文档信息
        recorder.add_section("源文档信息")
        recorder.add_content(f"- 文件路径: {doc_path}")
        recorder.add_content(f"- 文本长度: {len(source_text)} 字符")
        
        # 术语分析
        recorder.add_term_analysis(source_text)
        
        # 初始翻译（分块处理）
        logger.info("正在进行初始翻译...")
        initial_translation = await translate_document(client, source_text, "deepseek-v3")
        recorder.add_step_result("初始翻译结果", initial_translation)
        
        # 翻译反思
        logger.info("正在进行翻译反思...")
        reflection = await reflect_on_translation(client, source_text, initial_translation)
        recorder.add_step_result("翻译反思结果", reflection)
        
        # 翻译改进
        logger.info("正在进行翻译改进...")
        final_translation = await improve_translation(
            client,
            source_text,
            initial_translation,
            reflection
        )
        recorder.add_step_result("最终翻译结果", final_translation)
        
        # 验证结果
        validation_results = {
            "标题格式 (#)": "√" if "#" in final_translation else "×",
            "加粗格式 (**)": "√" if "**" in final_translation else "×",
            "斜体格式 (*)": "√" if "*" in final_translation else "×",
            "图片链接 (![])": "√" if "![" in final_translation else "×",
            "专业缩写 (NFS)": "√" if "NFS" in final_translation else "×",
            "型号名称 (737 MAX)": "√" if "737 MAX" in final_translation else "×"
        }
        recorder.add_validation_result(validation_results)
        
        # 保存结果
        output_path = doc_path.parent / "737MAX-FTD-46-19002_Doc_01092023_CN.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_translation)
            
        logger.info(f"翻译结果已保存至: {output_path}")
        return final_translation
        
    except Exception as e:
        logger.error(f"翻译过程出错: {str(e)}")
        recorder.add_section("错误信息")
        recorder.add_content(f"- 错误类型: {type(e)}")
        recorder.add_content(f"- 错误详情: {str(e)}")
        raise

if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=DEBUG", __file__]) 