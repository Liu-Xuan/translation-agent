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
import requests
import time
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 添加src目录到Python路径
src_path = str(Path(project_root) / 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

from app.patch import model_load, TranslationError
from translation_agent.utils import (
    one_chunk_translate_text,
    one_chunk_initial_translation,
    one_chunk_reflect_on_translation,
    one_chunk_improve_translation
)

# 加载环境变量
load_dotenv()

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

def test_api_connection():
    """测试API连接"""
    api_base = os.getenv("XIAOAI_API_BASE", "https://xiaoai.plus/v1")
    api_key = os.getenv("XIAOAI_API_KEY")
    
    logger.info(f"测试API连接: {api_base}")
    logger.info(f"API密钥前6位: {api_key[:6] if api_key else 'None'}...")
    
    try:
        response = requests.get(
            f"{api_base}/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        logger.info(f"API响应状态码: {response.status_code}")
        logger.info(f"API响应内容: {response.text[:200]}...")
        
        assert response.status_code == 200, f"API连接失败: {response.text}"
        logger.info("API连接测试成功")
        
    except Exception as e:
        logger.error(f"API连接测试失败: {str(e)}")
        raise

def setup_module():
    """初始化测试环境"""
    logger.info("开始初始化测试环境")
    
    api_base = os.getenv("XIAOAI_API_BASE", "https://xiaoai.plus/v1")
    api_key = os.getenv("XIAOAI_API_KEY")
    model = "gpt-4-1106-preview"
    
    logger.info(f"使用API基础URL: {api_base}")
    logger.info(f"使用模型: {model}")
    
    try:
        model_load(
            endpoint="XiaoAI",
            base_url=api_base,
            model=model,
            api_key=api_key,
        )
        logger.info("模型加载成功")
        
    except Exception as e:
        logger.error(f"模型加载失败: {str(e)}")
        raise

def test_boeing_doc_translation():
    """测试波音技术文档翻译"""
    logger.info("开始波音文档翻译测试")
    
    # 初始化记录器
    recorder = TranslationRecorder(Path(project_root) / "test_reports")
    
    # 读取源文档
    doc_path = Path(project_root) / "testcases/737MAX-FTD-46-19002_Doc_01092023/auto/737MAX-FTD-46-19002_Doc_01092023.md"
    logger.info(f"源文档路径: {doc_path}")
    
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            source_text = f.read()
        logger.info(f"成功读取源文档，长度: {len(source_text)} 字符")
        
        # 记录源文档信息
        recorder.add_section("源文档信息")
        recorder.add_content(f"- 文件路径: {doc_path}")
        recorder.add_content(f"- 文本长度: {len(source_text)} 字符")
        recorder.add_content("- 文本预览:")
        recorder.add_content(f"```\n{source_text[:500]}...\n```")
        
        # 添加术语匹配分析
        recorder.add_term_analysis(source_text)
        
        # 添加提示词嵌入分析
        recorder.add_prompt_analysis()
        
        # 第一阶段：初始翻译
        recorder.add_section("第一阶段：初始翻译")
        recorder.add_content("### 翻译提示词")
        initial_translation = one_chunk_initial_translation(
            source_lang="en",
            target_lang="zh",
            source_text=source_text,
            country="CN"
        )
        recorder.add_step_result("初始翻译结果", initial_translation)
        
        # 第二阶段：翻译反思
        recorder.add_section("第二阶段：翻译反思")
        recorder.add_content("### 反思提示词")
        reflection = one_chunk_reflect_on_translation(
            source_lang="en",
            target_lang="zh",
            source_text=source_text,
            translation_1=initial_translation,
            country="CN"
        )
        recorder.add_step_result("反思结果", reflection)
        
        # 第三阶段：翻译改进
        recorder.add_section("第三阶段：翻译改进")
        recorder.add_content("### 改进提示词")
        final_translation = one_chunk_improve_translation(
            source_lang="en",
            target_lang="zh",
            source_text=source_text,
            translation_1=initial_translation,
            reflection=reflection,
            country="CN"
        )
        recorder.add_step_result("最终翻译结果", final_translation)
        
        # 验证翻译结果
        recorder.add_section("翻译结果验证")
        validation_results = {
            "标题格式 (#)": "√" if "#" in final_translation else "×",
            "加粗格式 (**)": "√" if "**" in final_translation else "×",
            "斜体格式 (*)": "√" if "*" in final_translation else "×",
            "图片链接 (![])": "√" if "![" in final_translation else "×",
            "专业缩写 (NFS)": "√" if "NFS" in final_translation else "×",
            "型号名称 (737 MAX)": "√" if "737 MAX" in final_translation else "×"
        }
        recorder.add_validation_result(validation_results)
        
        # 保存最终翻译结果
        output_path = doc_path.parent / "737MAX-FTD-46-19002_Doc_01092023_CN.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_translation)
        logger.info(f"翻译结果已保存至: {output_path}")
        
        # 记录完成信息
        recorder.add_section("翻译完成信息")
        recorder.add_content(f"- 完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        recorder.add_content(f"- 最终文件路径：{output_path}")
        recorder.add_content(f"- 最终文本长度：{len(final_translation)} 字符")
        
        return final_translation
        
    except Exception as e:
        logger.error(f"翻译过程出错: {str(e)}")
        logger.error(f"错误类型: {type(e)}")
        logger.error(f"错误详情: {str(e)}")
        # 记录错误信息
        recorder.add_section("错误信息")
        recorder.add_content(f"- 错误类型: {type(e)}")
        recorder.add_content(f"- 错误详情: {str(e)}")
        raise

if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=DEBUG", __file__]) 