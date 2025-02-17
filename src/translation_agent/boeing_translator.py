"""
波音737 MAX技术文档翻译工具
包含完整的翻译、反思和改进功能

依赖安装：
pip install python-dotenv openai pytest

环境变量设置：
DASHSCOPE_API_KEY=your_api_key

项目结构要求：
project_root/
├── data/
│   └── glossary.json         # 术语表文件
├── docs/                    # 待翻译的文档
└── output/                 # 输出目录
"""

import os
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
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

class DeepSeekClient:
    """DeepSeek模型客户端，支持同步和异步操作"""
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请提供API密钥或在环境变量中设置DASHSCOPE_API_KEY")
            
        self.base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        # 同步客户端
        self.sync_client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            max_retries=5,
            timeout=300.0
        )
        
        # 异步客户端
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=300.0
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

def load_and_filter_terms(source_text: str, glossary_path: Path) -> list:
    """
    加载术语表并根据源文本筛选相关术语
    Args:
        source_text: 源文本
        glossary_path: 术语表文件路径
    Returns:
        list: 筛选后的术语列表
    """
    # 从术语表中获取术语
    with open(glossary_path, 'r', encoding='utf-8') as f:
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
    
    prompt = "请将以下英文文本翻译成中文。\n"
    prompt += "保持原文的格式和标点符号。如有HTML标签或Markdown标记，请保留不变。\n\n"
    
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

async def translate_boeing_doc(
    source_file: Path,
    output_dir: Path,
    glossary_path: Path,
    api_key: str = None,
    base_url: str = None
) -> str:
    """
    翻译波音文档的主函数
    Args:
        source_file: 源文档路径
        output_dir: 输出目录
        glossary_path: 术语表路径
        api_key: API密钥（可选）
        base_url: API基础URL（可选）
    Returns:
        str: 翻译后的文本
    """
    logger.info("="*50)
    logger.info("开始波音文档翻译")
    logger.info("="*50)
    
    # 初始化客户端和记录器
    client = DeepSeekClient(api_key, base_url)
    recorder = TranslationRecorder(output_dir)
    
    try:
        # 读取源文档
        with open(source_file, 'r', encoding='utf-8') as f:
            source_text = f.read()
        
        # 记录源文档信息
        recorder.add_section("源文档信息")
        recorder.add_content(f"- 文件路径: {source_file}")
        recorder.add_content(f"- 文本长度: {len(source_text)} 字符")
        
        # 加载和筛选术语
        used_terms = load_and_filter_terms(source_text, glossary_path)
        
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
        output_path = output_dir / f"{source_file.stem}_CN{source_file.suffix}"
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

def main():
    """主函数"""
    # 设置项目路径
    project_root = Path(__file__).parent.parent.parent
    
    # 设置输入输出路径
    source_file = project_root / "docs/737MAX-FTD-46-19002_Doc_01092023.md"
    output_dir = project_root / "output"
    glossary_path = project_root / "data/glossary.json"
    
    # 运行翻译
    asyncio.run(translate_boeing_doc(
        source_file=source_file,
        output_dir=output_dir,
        glossary_path=glossary_path
    ))

if __name__ == "__main__":
    main() 