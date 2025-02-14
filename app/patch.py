# 导入系统相关模块
import os  # 用于操作系统相关功能，如环境变量读取
import time  # 用于时间相关操作，如延时控制
from functools import wraps  # 用于装饰器功能，保持函数元数据
from threading import Lock  # 用于线程同步，确保并发安全
from typing import Optional, Union  # 类型提示，用于静态类型检查
import logging  # 导入日志模块

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入第三方依赖库
import openai  # OpenAI API客户端，用于与各种LLM服务通信
import translation_agent.utils as utils  # 导入项目的核心工具函数模块

# 定义全局配置常量，这些常量会影响整个翻译系统的行为
RPM = 60  # 每分钟最大请求次数（Rate Per Minute），用于API调用频率限制
MODEL = ""  # 当前使用的模型名称，会在运行时被设置
TEMPERATURE = 0.3  # 模型输出的随机性参数，越低越确定性，越高越创造性
# 当前在UI中隐藏了JSON模式选项，计划在后续版本中更新此功能
JS_MODE = False  # JSON输出模式开关，控制API返回格式
ENDPOINT = ""  # 当前使用的API端点，用于选择不同的LLM服务提供商

class TranslationError(Exception):
    """翻译过程中的自定义异常类"""
    pass

def model_load(
    endpoint: str,  # API服务提供商标识，如"OpenAI"、"Groq"等
    base_url: str,  # API基础URL地址，用于自定义端点
    model: str,  # 具体的模型名称，如"gpt-4-turbo"
    api_key: Optional[str] = None,  # API访问密钥，可选参数
    temperature: float = TEMPERATURE,  # 模型输出随机性参数
    rpm: int = RPM,  # 每分钟最大请求次数限制
    js_mode: bool = JS_MODE,  # JSON输出模式开关
):
    """
    初始化并加载指定的语言模型
    
    该函数负责配置和初始化与不同LLM提供商的连接。支持多个主流服务商，
    包括OpenAI、Groq、TogetherAI等，也支持自定义API端点。
    
    函数会根据提供的参数更新全局配置，并初始化相应的API客户端。
    """
    # 声明要使用的全局变量
    global client, RPM, MODEL, TEMPERATURE, JS_MODE, ENDPOINT
    
    # 更新全局配置
    ENDPOINT = endpoint  # 设置当前使用的API端点
    RPM = rpm  # 更新API请求频率限制
    MODEL = model  # 设置当前使用的模型
    TEMPERATURE = temperature  # 设置模型温度参数
    JS_MODE = js_mode  # 设置JSON模式状态

    # 根据不同的API提供商配置对应的客户端
    match endpoint:
        case "XiaoAI":  # 添加小爱API支持
            client = openai.OpenAI(
                api_key=api_key if api_key else os.getenv("XIAOAI_API_KEY"),
                base_url=os.getenv("XIAOAI_API_BASE", "https://xiaoai.plus/v1"),
            )
        case "OpenAI":  # OpenAI官方API配置
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # 使用环境变量中的API密钥
        case "Groq":  # Groq高性能推理服务配置
            client = openai.OpenAI(
                api_key=api_key if api_key else os.getenv("GROQ_API_KEY"),  # 优先使用传入的API密钥
                base_url="https://api.groq.com/openai/v1",  # Groq的API端点
            )
        case "TogetherAI":  # TogetherAI开源模型平台配置
            client = openai.OpenAI(
                api_key=api_key if api_key else os.getenv("TOGETHER_API_KEY"),
                base_url="https://api.together.xyz/v1",  # TogetherAI的API端点
            )
        case "CUSTOM":  # 自定义API端点配置
            client = openai.OpenAI(api_key=api_key, base_url=base_url)  # 使用自定义的URL和密钥
        case "Ollama":  # Ollama本地部署模型配置
            client = openai.OpenAI(
                api_key="ollama",  # Ollama使用固定的API密钥
                base_url="http://localhost:11434/v1"  # Ollama本地服务地址
            )
        case _:  # 默认使用OpenAI配置
            client = openai.OpenAI(
                api_key=api_key if api_key else os.getenv("OPENAI_API_KEY")
            )

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

def retry_on_error(initial_delay=1, backoff_factor=2):
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

@retry_on_error(initial_delay=1, backoff_factor=2)
def get_completion(
    prompt: str,
    system_message: str = "You are a helpful assistant.",
    model: str = "gpt-4-turbo",
    temperature: float = 0.3,
    json_mode: bool = False,
    timeout: float = 60.0,
) -> Union[str, dict]:
    """
    使用OpenAI API生成补全，包含无限重试机制
    
    Args:
        prompt: 用户提示
        system_message: 系统消息
        model: 模型名称
        temperature: 温度参数
        json_mode: JSON输出模式
        timeout: 请求超时时间（秒）
    Returns:
        生成的回复
    """
    try:
        if json_mode:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                timeout=timeout
            )
        else:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                timeout=timeout
            )
        return response.choices[0].message.content
                
    except Exception as e:
        logger.error(f"API调用失败: {str(e)}")
        raise TranslationError(f"API调用失败: {str(e)}") from e

# 将当前模块的API调用函数注入到utils模块中，使其可以使用相同的API调用功能
utils.get_completion = get_completion

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
