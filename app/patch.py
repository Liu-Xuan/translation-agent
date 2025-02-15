# 导入系统相关模块
import os  # 用于操作系统相关功能，如环境变量读取
import time  # 用于时间相关操作，如延时控制
from functools import wraps  # 用于装饰器功能，保持函数元数据
from threading import Lock  # 用于线程同步，确保并发安全
from typing import Optional, Union  # 类型提示，用于静态类型检查
import logging  # 导入日志模块
from datetime import datetime
import asyncio
import requests

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入第三方依赖库
import openai  # OpenAI API客户端，用于与各种LLM服务通信
import translation_agent.utils as utils  # 导入项目的核心工具函数模块
import httpx  # 用于HTTP客户端的增强功能
from openai import OpenAI

# 定义全局配置常量，这些常量会影响整个翻译系统的行为
RPM = 60  # 每分钟最大请求次数（Rate Per Minute），用于API调用频率限制
MODEL = ""  # 当前使用的模型名称，会在运行时被设置
TEMPERATURE = 0.3  # 模型输出的随机性参数，越低越确定性，越高越创造性
# 当前在UI中隐藏了JSON模式选项，计划在后续版本中更新此功能
JS_MODE = False  # JSON输出模式开关，控制API返回格式
ENDPOINT = ""  # 当前使用的API端点，用于选择不同的LLM服务提供商

# 在文件顶部添加模型注册表
model_registry = {}

# 初始化OpenAI客户端
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    timeout=60.0,
    http_client=httpx.Client(
        proxies="http://127.0.0.1:7897",  # 明确指定代理
        transport=httpx.HTTPTransport(
            retries=3,
            verify=os.getenv("SSL_VERIFY", True),  # 允许通过环境变量控制证书验证
            cert=os.getenv("SSL_CLIENT_CERT"),     # 客户端证书路径
            trust_env=False  # 禁用环境变量代理，使用显式配置
        ),
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20
        )
    )
)

class TranslationError(Exception):
    """翻译过程中的自定义异常类"""
    pass

class APIMonitor:
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'successful_chunks': 0,
            'failed_chunks': 0,
            'average_speed': 0.0,
            'max_chunk_size': 0,
            'timeout_events': 0
        }
    
    def record_request(self, chunk_size: int, success: bool, duration: float):
        """记录请求指标"""
        self.metrics['total_requests'] += 1
        if success:
            speed = chunk_size / duration if duration > 0 else 0
            self.metrics['successful_chunks'] += 1
            self.metrics['average_speed'] = (
                (self.metrics['average_speed'] * (self.metrics['successful_chunks']-1) + speed) 
                / self.metrics['successful_chunks']
            )
            self.metrics['max_chunk_size'] = max(self.metrics['max_chunk_size'], chunk_size)
        else:
            self.metrics['failed_chunks'] += 1
            self.metrics['timeout_events'] += 1

api_monitor = APIMonitor()

def model_load(endpoint: str, base_url: str, model: str, **kwargs):
    """增强的模型加载函数"""
    global client
    
    # 根据模型类型配置客户端
    if "DeepSeek" in model:
        # 配置超时和重试
        timeout_config = httpx.Timeout(
            connect=30.0,  # 连接超时
            read=180.0,    # 读取超时
            write=30.0,    # 写入超时
            pool=300.0     # 连接池超时
        )
        
        client = openai.OpenAI(
            api_key=kwargs.get('api_key', os.getenv("DASHSCOPE_API_KEY")),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            timeout=timeout_config,
            max_retries=3
        )
        
        # 记录模型加载信息
        logger.info(f"模型 {model} 加载成功")
        logger.debug(f"客户端配置: 超时={timeout_config}, 最大重试次数=3")
        
        # 更新模型注册表
        model_registry[model] = {
            "status": "loaded",
            "endpoint": endpoint,
            "base_url": base_url,
            "load_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timeout_config": str(timeout_config)
        }

def rate_limit(get_max_per_minute):
    """
    实现API调用的速率限制装饰器
    
    通过线程锁和时间间隔控制，确保API调用不超过指定的频率限制。
    这对于遵守API提供商的使用限制和避免请求被拒绝非常重要。
    
    Args:
        get_max_per_minute: 获取每分钟最大请求次数的函数
    Returns:
        function: 装饰器函数
    """
    def decorator(func):  # 定义装饰器函数
        lock = Lock()  # 创建线程锁，用于并发控制
        last_called = [0.0]  # 记录上次调用时间，使用列表便于在闭包中修改

        @wraps(func)  # 保持被装饰函数的元数据
        def wrapper(*args, **kwargs):  # 包装函数，处理实际的调用
            with lock:  # 进入临界区，确保线程安全
                max_per_minute = get_max_per_minute()  # 获取当前的频率限制
                min_interval = 60.0 / max_per_minute  # 计算最小调用时间间隔（秒）
                elapsed = time.time() - last_called[0]  # 计算距离上次调用的时间
                left_to_wait = min_interval - elapsed  # 计算需要等待的时间

                if left_to_wait > 0:  # 如果需要等待
                    time.sleep(left_to_wait)  # 休眠指定时间，确保不超过频率限制

                ret = func(*args, **kwargs)  # 执行被装饰的函数
                last_called[0] = time.time()  # 更新最后调用时间
                return ret  # 返回函数执行结果

        return wrapper  # 返回包装后的函数
    return decorator  # 返回装饰器函数

def retry_on_error(initial_delay=5, backoff_factor=2):
    """
    装饰器：为函数添加无限重试机制
    
    Args:
        initial_delay (int): 初始延迟时间（秒）
        backoff_factor (int): 退避因子，每次重试后延迟时间将乘以此因子
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            attempt = 1
            last_exception = None
            
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"尝试 {attempt} 失败: {str(e)}")
                    logger.info(f"等待 {delay} 秒后重试...")
                    time.sleep(delay)
                    delay *= backoff_factor
                    attempt += 1
            
            return None  # 不应该到达这里
        return wrapper
    return decorator

@retry_on_error(initial_delay=5, backoff_factor=2)
async def get_completion_with_retry(
    prompt: str,
    system_message: str,
    model: str,
    temperature: float = 0.3,
    timeout: float = 120.0
):
    """带有增强重试机制的完成请求函数"""
    try:
        # 记录请求开始
        logger.info(f"开始API请求 - 模型: {model}")
        logger.debug(f"请求参数: temperature={temperature}, timeout={timeout}")

        # 发送请求
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            stream=False
        )

        # 记录成功响应
        logger.info(f"API请求成功 - 模型: {model}")
        return response.choices[0].message.content

    except openai.APIConnectionError as e:
        error_msg = f"SSL连接失败: {str(e.__cause__)}"
        logger.error(error_msg)
        logger.error("建议检查：\n1. 本地代理设置\n2. 防火墙配置\n3. SSL证书有效性")
        raise TranslationError(error_msg) from e

# 将当前模块的API调用函数注入到utils模块中，使其可以使用相同的API调用功能
utils.get_completion = get_completion_with_retry

# 从utils模块导入所有翻译相关的功能函数，并提供中文注释说明其用途
one_chunk_initial_translation = utils.one_chunk_initial_translation  # 单块文本初始翻译函数
one_chunk_reflect_on_translation = utils.one_chunk_reflect_on_translation  # 单块文本翻译质量反思函数
one_chunk_improve_translation = utils.one_chunk_improve_translation  # 单块文本翻译改进函数
one_chunk_translate_text = utils.one_chunk_translate_text  # 单块文本完整翻译流程函数
num_tokens_in_string = utils.num_tokens_in_string  # 计算文本中token数量的函数
multichunk_initial_translation = utils.multichunk_initial_translation  # 多块文本初始翻译函数
multichunk_reflect_on_translation = utils.multichunk_reflect_on_translation  # 多块文本翻译质量反思函数
multichunk_improve_translation = utils.multichunk_improve_translation  # 多块文本翻译改进函数
multichunk_translation = utils.multichunk_translation  # 多块文本完整翻译流程函数
calculate_chunk_size = utils.calculate_chunk_size  # 计算最优文本分块大小的函数

def api_call_with_retry(func):
    """增强的重试装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        max_retries = 5  # 增加最大重试次数
        base_delay = 1.5  # 调整基础延迟时间
        timeout_config = {
            1: 60.0,  # 第一次超时
            2: 120.0, # 第二次延长
            3: 180.0  # 最大超时时间
        }
        
        for attempt in range(1, max_retries+1):
            try:
                # 动态调整超时时间
                current_timeout = timeout_config.get(attempt, 180.0)
                kwargs["timeout"] = current_timeout
                
                logger.debug(f"第{attempt}次尝试，超时设置为{current_timeout}s")
                return await func(*args, **kwargs)
            except httpx.ReadTimeout as e:
                if attempt == max_retries:
                    logger.error(f"达到最大重试次数{max_retries}次")
                    raise
                delay = base_delay * (2 ** attempt)
                logger.warning(f"请求超时，{delay}秒后重试...")
                await asyncio.sleep(delay)
            except httpx.ConnectError as e:
                logger.error("网络连接异常，建议检查：\n1. 本地网络连接\n2. 防火墙设置\n3. 代理配置")
                raise
    return wrapper

class ChunkConfig:
    """分块配置管理类"""
    def __init__(self):
        self.size_mapping = {
            "Pro/deepseek-ai/DeepSeek-V3": 5000,  # 增加到5000字符
            "Pro/deepseek-ai/DeepSeek-R1": 5000,  # 增加到5000字符
            "gpt-4": 5000  # 其他模型也相应调整
        }
        
        # 模型超时配置（秒）
        self.timeout_mapping = {
            "Pro/deepseek-ai/DeepSeek-V3": {
                "base": 120,
                "per_1k_chars": 20  # 每1000字符增加20秒
            },
            "Pro/deepseek-ai/DeepSeek-R1": {
                "base": 180,
                "per_1k_chars": 30  # 推理模型需要更多时间
            }
        }
    
    def get_chunk_size(self, model: str) -> int:
        """获取指定模型的分块大小"""
        return self.size_mapping.get(model, 3000)  # 默认3000字符
    
    def get_timeout(self, model: str, text_length: int) -> float:
        """计算动态超时时间"""
        config = self.timeout_mapping.get(model, {
            "base": 120,
            "per_1k_chars": 20
        })
        return config["base"] + (text_length / 1000) * config["per_1k_chars"]

chunk_config = ChunkConfig()
