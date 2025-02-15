import os
from openai import OpenAI
import time
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 测试配置
TEST_PROMPTS = [
    "请用一句话介绍你自己。",
    "计算1234和5678的和是多少？请展示计算过程。",
    "用Python写一个冒泡排序算法。"
]

class DeepSeekTester:
    def __init__(self):
        """
        初始化测试器
        - 设置API客户端
        - 初始化测试结果存储
        """
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("请在.env文件中设置DASHSCOPE_API_KEY环境变量")
            
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.results = []
        
    def test_model(self, model_name: str, stream: bool = False):
        """
        测试指定的模型
        
        Args:
            model_name: 模型名称 (deepseek-r1 或 deepseek-v3)
            stream: 是否使用流式输出
        """
        print(f"\n{'='*20} 测试模型: {model_name} {'='*20}")
        print(f"流式输出: {'开启' if stream else '关闭'}")
        
        for prompt in TEST_PROMPTS:
            print(f"\n提示词: {prompt}")
            start_time = time.time()
            
            try:
                if stream:
                    self._test_stream_mode(model_name, prompt)
                else:
                    self._test_normal_mode(model_name, prompt)
                    
                end_time = time.time()
                self.results.append({
                    'model': model_name,
                    'prompt': prompt,
                    'stream': stream,
                    'status': '成功',
                    'time': end_time - start_time
                })
                
            except Exception as e:
                print(f"错误: {str(e)}")
                self.results.append({
                    'model': model_name,
                    'prompt': prompt,
                    'stream': stream,
                    'status': f'失败: {str(e)}',
                    'time': time.time() - start_time
                })
    
    def _test_normal_mode(self, model_name: str, prompt: str):
        """普通模式测试"""
        response = self.client.chat.completions.create(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        if hasattr(response.choices[0].message, 'reasoning_content'):
            print("\n思考过程:")
            print(response.choices[0].message.reasoning_content)
            
        print("\n回答:")
        print(response.choices[0].message.content)
    
    def _test_stream_mode(self, model_name: str, prompt: str):
        """流式输出模式测试"""
        stream = self.client.chat.completions.create(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}],
            stream=True
        )
        
        print("\n输出:")
        for chunk in stream:
            if not hasattr(chunk, 'choices'):
                continue
                
            delta = chunk.choices[0].delta
            
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                print(delta.reasoning_content, end='', flush=True)
            elif hasattr(delta, 'content') and delta.content:
                print(delta.content, end='', flush=True)
    
    def generate_report(self):
        """生成测试报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"test_reports/deepseek_test_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# DeepSeek模型测试报告\n\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 测试结果汇总\n\n")
            f.write("| 模型 | 提示词 | 流式输出 | 状态 | 响应时间(秒) |\n")
            f.write("|------|--------|-----------|--------|---------------|\n")
            
            for result in self.results:
                f.write(f"| {result['model']} | {result['prompt'][:20]}... | "
                       f"{'是' if result['stream'] else '否'} | {result['status']} | "
                       f"{result['time']:.2f} |\n")
        
        print(f"\n测试报告已生成: {report_path}")

def main():
    """主测试流程"""
    tester = DeepSeekTester()
    
    # 测试 deepseek-r1
    tester.test_model("deepseek-r1", stream=False)
    tester.test_model("deepseek-r1", stream=True)
    
    # 测试 deepseek-v3
    tester.test_model("deepseek-v3", stream=False)
    tester.test_model("deepseek-v3", stream=True)
    
    # 生成报告
    tester.generate_report()

if __name__ == "__main__":
    main() 