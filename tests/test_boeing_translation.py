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
import openai
import re
from openai import OpenAI, AsyncOpenAI

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

def load_and_filter_terms(source_text: str) -> list:
    """
    加载术语表并根据源文本筛选相关术语
    Args:
        source_text: 源文本
    Returns:
        list: 筛选后的术语列表
    """
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
    
    # 过滤并返回使用的术语
    used_terms = [term for term in terms if term['source']['text'] in term_counts]
    return used_terms

class DeepSeekClient:
    """DeepSeek模型客户端，支持同步和异步操作"""
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请在.env文件中设置DASHSCOPE_API_KEY环境变量")
            
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        # 同步客户端
        self.sync_client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 异步客户端
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 模型配置
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
    
    async def translate_text_stream(self, text: str, model: str) -> str:
        """流式翻译文本"""
        try:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=[{'role': 'user', 'content': text}],
                stream=True,
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
    
    def add_term_analysis(self, source_text: str, used_terms: list):
        """添加术语匹配分析"""
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
            f.write(f"- 总识别术语数：{len(used_terms)}个\n")
            f.write("- 高频术语：\n")
            term_counts = {}
            for term in used_terms:
                count = source_text.lower().count(term['source']['text'].lower())
                term_counts[term['source']['text']] = count
            
            sorted_terms = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)
            for term, count in sorted_terms[:3]:
                f.write(f"  * `{term}`（出现{count}次）\n")
            
            # 记录专有名词保留
            f.write("- 专有名词保留：\n")
            abbrs = [t['source']['text'] for t in used_terms if '(' in t['source']['text']]
            for abbr in abbrs:
                if '(' in abbr:
                    short_form = abbr[abbr.find('(')+1:abbr.find(')')]
                    f.write(f"  * {short_form}\n")

async def translate_document(client: DeepSeekClient, text: str, model: str, used_terms: list = None) -> str:
    """
    翻译文档
    Args:
        client: DeepSeek客户端
        text: 待翻译文本
        model: 使用的模型
        used_terms: 筛选后的术语列表
    """
    logger.info("开始翻译文档...")
    
    prompt = "作为资深民航维修工程师，请将以下英文文本翻译成中文。请在对全文理解的基础上进行翻译。\n"
    prompt += "保持原文的格式和标点符号。如有HTML标签或Markdown标记，请保留不变。祛除多余的# FLEET TEAM DIGEST标题，只保留文档最开始的一个。 \n\n"
    
    if used_terms:
        prompt += "## 术语表要求：\n"
        for term in used_terms:
            prompt += f"- 【强制】'{term['source']['text']}' → '{term['target']['text']}'"
            if term.get('context'):
                prompt += f"（上下文：{term['context']}）"
            prompt += "\n"
        prompt += "\n请严格遵守以上术语表的翻译要求。对于术语的处理：\n"
        prompt += "1. 优先使用术语表中的对应翻译\n"
        prompt += "2. 保持术语的一致性\n"
        prompt += "3. 注意术语的上下文含义\n"
        prompt += "4. 保留术语的专业性\n\n"
        prompt += "5. 不允许任意偏离、变更术语表中的术语\n\n"
        prompt += "6. 不允许偏离原文表述的信息，不允许增删信息内容！\n\n"
    
    prompt += f"源文本：\n{text}"
    
    return await client.translate_text_stream(prompt, model)

async def reflect_on_translation(client: DeepSeekClient, source: str, translation: str, used_terms: list = None) -> str:
    """使用deepseek-r1模型反思翻译质量"""
    prompt = "请分析以下从英文到中文的翻译，重点关注以下方面：\n\n"
    
    if used_terms:
        prompt += "## 需要重点关注的术语：\n"
        for term in used_terms:
            prompt += f"- {term['source']['text']} → {term['target']['text']}"
            if term.get('context'):
                prompt += f"（上下文：{term['context']}）"
            prompt += "\n"
        prompt += "\n"
    
    prompt += """1. 术语翻译：
   - 术语使用的准确性
   - 术语翻译的一致性
   - 术语上下文的适当性
   - 专业术语的规范性
   - 不允许任意偏离、变更术语表中的术语
   
2. 翻译质量：
   - 作为资深民航维修工程师，对文章整体内容进行理解，评估翻译质量
   - 内容的完整性（祛除多余的# FLEET TEAM DIGEST标题，只保留文档最开始的一个。）
   - 含义的准确性
   - 表达的自然度
   - 语言的流畅度
   - 不允许偏离原文表述的信息，不允许增删信息内容！


3. 格式规范：
   - 格式标记的保留
   - 标点符号的正确性
   - 特殊标记的处理
   - 排版的一致性（注意理解每段内容，以及合适的标题排版，对不合理的排版进行调整）
   - FTD 文档的段落标题一般包括以下内容（请根据实际情况进行调整）：
        - Issue Title
        - Background
        - Applicability
        - Description
        - Status
        - Interim Action
        - Final Action
        - Operator Action
        - Milestone
        - Attachments
        - References
        - Parts List
        - Related Categories
        
原文：
{source}

译文：
{translation}

请从以上几个方面进行分析，并给出具体的改进建议。
"""
    return await client.translate_text_stream(prompt, "deepseek-r1")

async def improve_translation(client: DeepSeekClient, source: str, translation: str, reflection: str, used_terms: list = None) -> str:
    """根据反思结果改进翻译"""
    prompt = "请根据以下反馈改进这段翻译：\n\n"
    
    if used_terms:
        prompt += "## 术语表要求：\n"
        for term in used_terms:
            prompt += f"- 【强制】'{term['source']['text']}' → '{term['target']['text']}'"
            if term.get('context'):
                prompt += f"（上下文：{term['context']}）"
            prompt += "\n"
        prompt += "\n术语处理原则：\n"
        prompt += "1. 必须使用术语表规定的译法\n"
        prompt += "2. 确保术语在上下文中使用恰当\n"
        prompt += "3. 保持术语翻译的专业性\n"
        prompt += "4. 维护术语使用的一致性\n\n"
    
    prompt += f"""原文：
{source}

当前译文：
{translation}

改进建议：
{reflection}

请根据以上要求提供改进后的译文。注意：
1. 认真考虑所有改进建议
2. 确保术语使用准确
3. 保持格式完整性
4. 提升整体翻译质量
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
    doc_path = Path(project_root) / "testcases/737MAX-FTD-31-23004_Doc_09202023/auto/737MAX-FTD-31-23004_Doc_09202023/auto/737MAX-FTD-31-23004_Doc_09202023.md"
    
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            source_text = f.read()
        
        # 记录源文档信息
        recorder.add_section("源文档信息")
        recorder.add_content(f"- 文件路径: {doc_path}")
        recorder.add_content(f"- 文本长度: {len(source_text)} 字符")
        
        # 加载和筛选术语
        used_terms = load_and_filter_terms(source_text)
        
        # 术语分析
        recorder.add_term_analysis(source_text, used_terms)
        
        # 初始翻译
        logger.info("正在进行初始翻译...")
        initial_translation = await translate_document(client, source_text, "deepseek-v3", used_terms)
        recorder.add_step_result("初始翻译结果", initial_translation)
        
        # 翻译反思
        logger.info("正在进行翻译反思...")
        reflection = await reflect_on_translation(client, source_text, initial_translation, used_terms)
        recorder.add_step_result("翻译反思结果", reflection)
        
        # 翻译改进
        logger.info("正在进行翻译改进...")
        final_translation = await improve_translation(
            client,
            source_text,
            initial_translation,
            reflection,
            used_terms
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