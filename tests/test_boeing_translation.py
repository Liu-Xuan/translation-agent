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