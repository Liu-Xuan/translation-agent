def test_direct_connection():
    """测试直连API端点"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('api.siliconflow.cn', 443))
    assert result == 0, f"API端点不可达，错误码: {result}"
    
def test_proxy_config():
    """验证代理配置"""
    assert not os.environ.get("HTTP_PROXY"), "存在HTTP代理配置"
    assert not os.environ.get("HTTPS_PROXY"), "存在HTTPS代理配置"

def test_sustained_connection():
    """持续连接压力测试"""
    import socket
    success = 0
    for _ in range(10):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('api.siliconflow.cn', 443))
        if result == 0:
            success +=1
        sock.close()
    assert success >= 8, f"持续连接成功率不足80% ({success}/10)"

def test_large_request_handling():
    """测试大规模请求处理能力"""
    import socket
    import time
    
    def test_connection(size: int) -> float:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('api.siliconflow.cn', 443))
        sock.send(b'X' * size)
        sock.close()
        return time.time() - start
    
    # 测试不同大小的请求
    sizes = [1000, 5000, 10000]
    for size in sizes:
        latency = test_connection(size)
        assert latency < 5.0, f"{size}字节请求延迟过高: {latency:.2f}秒"

def test_network_stability():
    """持续30秒的网络稳定性测试"""
    import socket
    import time
    
    success = 0
    total = 0
    start_time = time.time()
    
    while time.time() - start_time < 30:  # 持续30秒
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('api.siliconflow.cn', 443))
            if result == 0:
                success +=1
            total +=1
        finally:
            sock.close()
        time.sleep(0.5)  # 每0.5秒测试一次
    
    success_rate = success / total if total >0 else 0
    assert success_rate >= 0.95, f"网络稳定性不足95% ({success}/{total})" 