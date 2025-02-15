# 翻译系统架构文档

## 系统架构概述

### 1. 核心组件
1. 翻译引擎
   - 初始翻译模块 (Pro/deepseek-ai/DeepSeek-V3)
   - 翻译反思模块 (Pro/deepseek-ai/DeepSeek-R1)
   - 翻译改进模块 (Pro/deepseek-ai/DeepSeek-V3)

2. API系统
   - 统一API接口
   - 多模型支持
   - 错误处理机制
   - 重试策略

3. 日志系统
   - 分级日志记录
   - 详细调试信息
   - 错误追踪
   - 性能监控

### 2. 工作流程
1. 初始翻译阶段
   - 使用 Pro/deepseek-ai/DeepSeek-V3 模型
   - 保持格式和标记
   - 术语表集成
   - 地区适配

2. 翻译反思阶段
   - 使用 Pro/deepseek-ai/DeepSeek-R1 模型
   - 质量评估
   - 问题识别
   - 改进建议

3. 翻译改进阶段
   - 使用 Pro/deepseek-ai/DeepSeek-V3 模型
   - 应用改进建议
   - 质量验证
   - 最终输出

### 3. 数据流
1. 输入处理
   - 源文本解析
   - 格式识别
   - 术语提取
   - 分块处理

2. 翻译处理
   - API调用
   - 模型切换
   - 结果验证
   - 错误恢复

3. 输出处理
   - 结果合并
   - 格式重建
   - 质量检查
   - 报告生成

### 4. 质量保证
1. 术语管理
   - 术语库维护
   - 一致性检查
   - 上下文验证
   - 专业性保持

2. 格式控制
   - 标记保留
   - 结构维护
   - 样式一致
   - 特殊处理

3. 质量监控
   - 实时验证
   - 错误检测
   - 性能监控
   - 结果评估

### 5. 系统集成
1. API集成
   - 多模型支持
   - 统一接口
   - 配置管理
   - 性能优化

2. 日志集成
   - 统一日志
   - 错误追踪
   - 性能监控
   - 调试支持

3. 测试集成
   - 单元测试
   - 集成测试
   - 性能测试
   - 回归测试

## 系统架构更新 (2024-03-15)

### 多模型协作架构 

## 网络层优化方案 (2024-03-28)

### 连接管理
1. 多路复用连接池
   - 最大连接数：20
   - 空闲连接超时：300秒
   - 心跳检测间隔：60秒

2. 智能路由
   - 自动代理检测
   - 直连/代理模式切换
   - 地域最优节点选择

3. 超时策略
   ```python
   timeout_config = {
       "connect": 10.0,    # 连接建立超时
       "read": 120.0,      # 数据读取超时
       "write": 30.0,      # 数据发送超时
       "pool": 300.0       # 连接池等待超时
   }
   ``` 

## 网络层增强方案 (2024-03-28)

### 连接管理优化
1. 智能代理检测
   ```python
   def detect_proxy():
       """自动检测系统代理设置"""
       proxy_config = {
           "http": os.environ.get("HTTP_PROXY"),
           "https": os.environ.get("HTTPS_PROXY")
       }
       return proxy_config if any(proxy_config.values()) else None
   ```

2. 连接池配置
   ```python
   connection_pool = httpx.HTTPConnectionPool(
       max_connections=20,
       max_keepalive_connections=10,
       keepalive_expiry=300
   )
   ```

3. 自适应超时策略
   ```python
   adaptive_timeout = {
       "connect": 10.0,
       "read": lambda size: min(120.0, 0.1 * size),  # 根据响应大小动态调整
       "write": 30.0,
       "pool": 300.0
   }
   ``` 

## 连接可靠性增强方案 (2024-03-28)

### 分层超时策略
```python
timeout_config = {
    "small_request": {  # <1KB
        "connect": 5.0,
        "read": 30.0
    },
    "medium_request": {  # 1KB-10KB
        "connect": 10.0,
        "read": 60.0
    },
    "large_request": {  # >10KB
        "connect": 15.0,
        "read": 120.0
    }
}
```

### 智能代理管理
```python
def configure_proxy():
    """自动代理配置逻辑"""
    if os.getenv("CI_MODE"):  # CI环境强制直连
        return {"http://": None, "https://": None}
        
    return detect_system_proxy() or {
        "http://": None,
        "https://": None
    }
```

### 连接健康检查
```python
class ConnectionMonitor:
    def __init__(self):
        self.stats = {
            "success": 0,
            "timeout": 0,
            "errors": 0
        }
    
    def check_health(self):
        """执行健康检查"""
        if self.stats["errors"] > 10:
            self.trigger_failover()
```

# 项目框架说明

## 2025-02-15 20:55:00 更新
### 异步支持
- 核心翻译功能现在支持异步操作
- 测试框架升级为支持异步测试
- 添加了必要的异步依赖项

### 依赖更新
- tiktoken：用于文本分词
- icecream：用于调试输出
- langchain-text-splitters：用于文本分割
- pytest-asyncio：用于异步测试 

### 测试框架更新
├── tests/
│   ├── test_boeing_translation.py
│   │   ├── 测试策略
│   │   │   ├── 超时控制（300秒）
│   │   │   ├── 自动重试（3次）
│   │   │   ├── 模型服务状态检测
│   │   │   └── 异步测试支持
│   │   └── 异常处理
│   │       ├── 超时警告
│   │       ├── 服务不可用跳过
│   │       └── 关键服务断言 

## 2024-02-15 15:30 系统优化更新

### 1. 分块处理优化
- 实现智能分块策略
  - 添加10%的上下文重叠
  - 最小块大小保证为100 tokens
  - 动态调整块大小以优化翻译质量

### 2. 超时机制
- 动态超时计算
  - 基础超时时间：60秒
  - 每1000字符增加10秒处理时间
  - 最大超时限制：5分钟
  - 自动根据文本长度调整

### 3. 重试机制
- 指数退避策略
  - 基础延迟时间：5秒
  - 最大延迟时间：60秒
  - 最大重试次数：3次
  - 智能错误处理和日志记录

### 4. 待实现特性
- 会话管理
  - 实现会话上下文保持
  - 支持连续翻译的上下文关联
  - 优化多轮翻译的质量

### 5. 性能监控
- 添加详细的日志记录
  - API调用状态跟踪
  - 响应时间监控
  - 错误分析和报告 

## 2025-02-15 23:00:00 API 配置更新

### 1. API 端点架构
- 基础 URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 兼容模式支持
  - OpenAI 格式兼容
  - 统一请求结构
  - 标准化响应格式

### 2. 认证机制
```python
def get_auth_header():
    """获取认证头信息"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
```

### 3. 请求配置
```python
request_config = {
    "model": "deepseek-v3",  # 或 "deepseek-r1"
    "messages": [
        {"role": "system", "content": "系统提示"},
        {"role": "user", "content": "用户输入"}
    ],
    "temperature": 0.7,
    "max_tokens": 4096,
    "stream": True
}
```

### 4. 超时策略
```python
timeout_config = {
    "connect": 30.0,    # 连接超时
    "read": 180.0,      # 读取超时
    "write": 30.0,      # 写入超时
    "pool": 300.0       # 连接池超时
}
```

### 5. 重试策略
```python
retry_config = {
    "max_retries": 3,
    "backoff_factor": 1.5,
    "status_forcelist": [500, 502, 503, 504],
    "allowed_methods": ["HEAD", "GET", "POST"]
}
```

### 6. 错误处理
```python
class APIError(Exception):
    """API 错误基类"""
    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

def handle_api_error(error):
    """统一错误处理"""
    if isinstance(error, requests.exceptions.Timeout):
        raise APIError("请求超时", status_code=408)
    elif isinstance(error, requests.exceptions.ConnectionError):
        raise APIError("连接错误", status_code=503)
    else:
        raise APIError(str(error))
``` 