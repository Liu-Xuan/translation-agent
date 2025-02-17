"""
测试波音737 MAX技术文档的分析评估
重点关注文档内容理解、资源评估和决策建议
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
import random

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
                "frequency_penalty": 0.0,
                "max_tokens": 4000
            },
            "deepseek-v3": {
                "temperature": 0.7,
                "top_p": 0.6,
                "presence_penalty": 0.95,
                "frequency_penalty": 0.0,
                "max_tokens": 4000
            }
        }
    
    async def analyze_text_stream(self, text: str, model: str) -> str:
        """流式分析文本"""
        try:
            # 设置重试次数
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    response = await self.async_client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "你是一个专业的技术文档分析专家。"},
                            {"role": "user", "content": text}
                        ],
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
                    retry_count += 1
                    if retry_count == max_retries:
                        raise
                    
                    # 指数退避延迟
                    delay = (2 ** retry_count) + (random.random() * 0.1)
                    logger.warning(f"API调用失败，第{retry_count}次重试，等待{delay:.2f}秒: {str(e)}")
                    await asyncio.sleep(delay)
            
        except Exception as e:
            logger.error(f"流式分析失败: {str(e)}")
            raise

class AnalysisRecorder:
    """分析过程记录器"""
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.report_path = self.output_dir / f"document_analysis_{self.timestamp}.md"
        self.current_section = None
        
        # 初始化文档
        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write(f"# 波音737 MAX技术文档分析评估报告\n\n")
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
    
    def add_term_analysis(self, source_text: str, used_terms: list):
        """添加术语匹配分析"""
        with open(self.report_path, 'a', encoding='utf-8') as f:
            f.write("## 术语匹配分析\n\n")
            
            # 记录识别到的关键术语
            f.write("### 识别到的关键术语\n")
            tech_terms = [t for t in used_terms if any(x in t['source']['text'].lower() for x in ['serial', 'fault', 'software', 'deck', 'service'])]
            for term in tech_terms:
                f.write(f"   - `{term['source']['text']}` → `{term['target']['text']}`\n")
            
            f.write("\n2. **流程术语**\n")
            process_terms = [t for t in used_terms if any(x in t['source']['text'].lower() for x in ['action', 'procedure', 'step', 'operation'])]
            for term in process_terms:
                f.write(f"   - `{term['source']['text']}` → `{term['target']['text']}`\n")
            
            f.write("\n3. **通用术语**\n")
            general_terms = [t for t in used_terms if t not in tech_terms and t not in process_terms]
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
            for term, count in sorted_terms[:5]:
                f.write(f"  * `{term}`（出现{count}次）\n")

async def analyze_document_structure(client: DeepSeekClient, text: str, used_terms: list = None) -> str:
    """
    第一阶段：使用V3模型对文档进行结构分解
    Args:
        client: DeepSeek客户端
        text: 待分析文本
        used_terms: 筛选后的术语列表
    """
    logger.info("开始文档结构分析...")
    
    prompt = "作为资深民航维修工程师和技术文档专家，请对以下文档进行结构化分析。\n\n"
    prompt += """分析要求：
        作为一名资深民航维修工程师和技术文档专家，请阅读以下文本内容，对其进行系统的结构化分解。
        请务必识别和输出以下信息：
        1. 文档主要段落或章节及其标题（如：Issue Title, Background, Applicability, Description, Status, Interim Action, Final Action, Operator Action, Milestone, References, Parts List, Related Categories 等），并根据实际文档情况进行灵活调整。
        2. 对每个段落的主要内容进行简要概述：用简明扼要的语言说明该段落的核心内容。
        3. 结构化给出每个段落的内容，不要遗漏信息。
        4. 指出文档结构是否完整、逻辑是否合理，有无缺失或混乱之处。
        5. 识别文档中出现的关键实体（如飞机型号、系统名称、关键LRU（航线可更换件）名称和件号、关键故障、服务通告（SB）编号、其他关联文档编号、软件名称和软件件号等）。
        6. 对关键实体之间的关系进行简要描述（例如，某个服务公告与哪一型飞机或哪个软件版本相关）。
        7. 最后输出以下结果：
        - 文档结构图（以树状或分层方式呈现各段落/章节）
        - 各章节主要内容概述（可用小段落或列表方式）
        - 保持文档中所有原文信息的完整性，无缺失
        - 结构化给出每个段落的内容，不要遗漏信息。
        - 关键要素/实体清单及其关系

        请确保在输出中，对文档内容不做任意改动或省略，只对其进行合理的拆分和标记。
   """
    
    if used_terms:
        prompt += "## 需要重点关注的术语：\n"
        for term in used_terms:
            prompt += f"- {term['source']['text']}"
            if term.get('context'):
                prompt += f"（上下文：{term['context']}）"
            prompt += "\n"
        prompt += "\n"
    
    prompt += f"待分析文档：\n{text}"
    
    return await client.analyze_text_stream(prompt, "deepseek-v3")

async def analyze_document_content(client: DeepSeekClient, text: str, structure_analysis: str, used_terms: list = None) -> str:
    """
    第二阶段：使用R1模型对文档内容进行深入分析
    Args:
        client: DeepSeek客户端
        text: 待分析文本
        structure_analysis: 结构分析结果
        used_terms: 筛选后的术语列表
    """
    logger.info("开始文档内容深入分析...")
    
    prompt = "作为资深民航维修工程师和技术专家，请对以下文档进行深入的技术内容分析。\n\n"
    prompt += """分析要求：
            作为一名资深民航维修工程师和技术专家，请在第一阶段的结构化结果基础上，对以下文档内容进行深入技术分析。重点关注：

            1. 适用性：
            - 该文档是否适用于我们的机队（如国航机队）？
            - Related Categories 中提到的影响范围或分类是什么？为每一个影响分类，进行一段总结分析。

            2. 问题根本原因与现状：
            - 是否已经查明问题的成因？与哪些系统或情况相关？
            - 是否已经提出临时措施（Interim Action）及其可行性？
            - 是否已有最终措施（Final Action）或软件/硬件版本升级计划？

            3. 实施评估：
            - 执行难度：是否需要特殊工具、是否需要停场等？
            - 资源需求： Boeing、厂家相关技术文件的颁发计划和时间、航材问题（是否需要订购航材，订购改装周转件等）、Boeing 及其他厂家的支持。
            - 风险分析：若不及时实施，会否产生合规风险或潜在安全隐患？
            - 时间与成本估算：需多少维修人时、预计多久可完成？
            - 工程文件发布：是否需要 AEO、CEO、MT、OT 等内部或外部工程文件来执行改装/维护提示/飞行机组通告等？

            4. 对运营与其它部门的影响：
            - 是否需要告知飞行员、运行管理部、航材部或其他部门？


            5. 最终输出：
            - 详细技术评估报告：包含以上要点的分析结论
            - 实施建议：如需临时修复或等待最终修复的权衡，或需要等待哪些信息以进行进一步决策
            - 风险提示：对运营、技术、合规等方面
            - 资源需求：Boeing、厂家相关技术文件的颁发计划和时间、航材问题（是否需要订购航材，订购改装周转件等）、Boeing 及其他厂家的支持。 \n\n"""
    
    if used_terms:
        prompt += "## 术语表参考：\n"
        for term in used_terms:
            prompt += f"- {term['source']['text']}"
            if term.get('context'):
                prompt += f"（上下文：{term['context']}）"
            prompt += "\n"
        prompt += "\n"
    
    prompt += f"文档结构分析结果：\n{structure_analysis}\n\n"
    prompt += f"待分析文档：\n{text}"
    
    return await client.analyze_text_stream(prompt, "deepseek-r1")

async def generate_final_report(client: DeepSeekClient, text: str, structure_analysis: str, content_analysis: str, used_terms: list = None) -> str:
    """
    第三阶段：使用V3模型整合分析结果，生成最终报告
    Args:
        client: DeepSeek客户端
        text: 原始文档
        structure_analysis: 结构分析结果
        content_analysis: 内容分析结果
        used_terms: 筛选后的术语列表
    """
    logger.info("开始生成最终分析报告...")
    
    prompt = "作为资深技术文档分析专家，请整合前期分析结果，生成最终的评估报告。\n\n"
    prompt += """报告要求：
            作为一名资深技术文档分析专家，请综合第一阶段的文档结构分析结果和第二阶段的深入技术分析结论，为此文档生成一份最终的评估报告。报告需包含但不限于：

            1. 总体评估：
            - 文档质量综合评价：是否清晰、完整，是否存在信息缺失
            - 主要发现与问题：本次分析中识别到的关键矛盾、风险点或改进空间
            - Related Categories 中提到的影响范围或分类，为每一个影响分类，进行一段总结分析。

            2. 实施建议：
            - 短期行动计划：需立刻执行的措施，或临时性解决方案
            - 中长期改进方案：涉及后续软件升级、硬件改装等

            3. 资源评估：
            - 是否需要等待相关文件的颁发：列出文件名称、编号、预计发布时间、作用、影响
            - 时间和成本估算：可能的项目周期、预算范围

            4. 风险管理计划：
            - 潜在风险列表：安全合规、进度延误、成本等
            - 风险级别与应对策略：如何减轻或避免风险的影响

            5. 输出格式：
            - 执行摘要：高度概括核心结论
            - 详细发现：分条列出从结构分析与深度评估得出的关键信息
            - 建议措施：针对不同领域和部门的可执行操作清单
            - 风险管理：风险列表与应对策略

            请在报告中引用必要的文档原文或分析细节，以支持结论，并提供清晰的结构化结果，便于后续跟踪与实施。\n\n"""
    
    if used_terms:
        prompt += "## 术语使用情况：\n"
        term_counts = {}
        for term in used_terms:
            count = text.lower().count(term['source']['text'].lower())
            term_counts[term['source']['text']] = count
        
        sorted_terms = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)
        for term, count in sorted_terms[:5]:
            prompt += f"- {term}（出现{count}次）\n"
        prompt += "\n"
    
    prompt += f"结构分析结果：\n{structure_analysis}\n\n"
    prompt += f"内容分析结果：\n{content_analysis}\n\n"
    prompt += f"原始文档：\n{text}"
    
    return await client.analyze_text_stream(prompt, "deepseek-v3")

@pytest.mark.asyncio
async def test_boeing_doc_analysis():
    """测试波音文档分析评估流程"""
    logger.info("="*50)
    logger.info("开始波音文档分析评估")
    logger.info("="*50)
    
    # 初始化客户端和记录器
    client = DeepSeekClient()
    recorder = AnalysisRecorder(Path(project_root) / "test_reports")
    
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
        
        # 第一阶段：文档结构分析
        logger.info("正在进行文档结构分析...")
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                structure_analysis = await analyze_document_structure(client, source_text, used_terms)
                recorder.add_step_result("文档结构分析结果", structure_analysis)
                break
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    raise
                delay = (2 ** retry_count) + (random.random() * 0.1)
                logger.warning(f"文档结构分析失败，第{retry_count}次重试，等待{delay:.2f}秒: {str(e)}")
                await asyncio.sleep(delay)
        
        # 第二阶段：深入内容分析
        logger.info("正在进行深入内容分析...")
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                content_analysis = await analyze_document_content(
                    client,
                    source_text,
                    structure_analysis,
                    used_terms
                )
                recorder.add_step_result("深入内容分析结果", content_analysis)
                break
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    raise
                delay = (2 ** retry_count) + (random.random() * 0.1)
                logger.warning(f"深入内容分析失败，第{retry_count}次重试，等待{delay:.2f}秒: {str(e)}")
                await asyncio.sleep(delay)
        
        # 第三阶段：生成最终报告
        logger.info("正在生成最终分析报告...")
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                final_report = await generate_final_report(
                    client,
                    source_text,
                    structure_analysis,
                    content_analysis,
                    used_terms
                )
                recorder.add_step_result("最终分析报告", final_report)
                break
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    raise
                delay = (2 ** retry_count) + (random.random() * 0.1)
                logger.warning(f"最终报告生成失败，第{retry_count}次重试，等待{delay:.2f}秒: {str(e)}")
                await asyncio.sleep(delay)
        
        # 保存结果
        output_path = doc_path.parent / f"737MAX-FTD-31-23004_Doc_09202023_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_report)
            
        logger.info(f"分析报告已保存至: {output_path}")
        return final_report
        
    except Exception as e:
        logger.error(f"分析过程出错: {str(e)}")
        recorder.add_section("错误信息")
        recorder.add_content(f"- 错误类型: {type(e)}")
        recorder.add_content(f"- 错误详情: {str(e)}")
        raise

if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=DEBUG", __file__]) 