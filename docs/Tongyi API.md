本文介绍了在百炼平台通过API调用DeepSeek系列模型的方法 。其中 deepseek-r1 与 deepseek-v3 分别有 100万的免费 Token，部分蒸馏模型限时免费体验。

支持的模型

DeepSeek系列模型是由深度求索（DeepSeek）公司推出的大语言模型。

DeepSeek-R1 模型包含 671B 参数，激活 37B，在后训练阶段大规模使用了强化学习技术，在仅有极少标注数据的情况下，极大提升了模型推理能力，尤其在数学、代码、自然语言推理等任务上。

DeepSeek-V3 为MoE 模型，671B 参数，激活 37B，在 14.8T Token 上进行了预训练，在长文本、代码、数学、百科、中文能力上表现优秀。

DeepSeek-R1-Distill 系列模型是基于知识蒸馏技术，通过使用 DeepSeek-R1 生成的训练样本对 Qwen、Llama 等开源大模型进行微调训练后，所得到的增强型模型。

DeepSeek-R1 （671B）与 DeepSeek-V3 模型享五折优惠，活动时间为2025年02月12日18:00:00~2025年02月23日23:59:59，活动结束后恢复原价。

模型名称
上下文长度
最大输入
最大输出
输入成本
输出成本
免费额度
（注）
（Token数）
（每千Token）
deepseek-r1
671B 满血版模型
65,792
57,344
32,768
0.002元
原0.004元
0.008元
原0.016元
100万Token
有效期：百炼开通后180天内
deepseek-v3
参数量为 671B
8,192
0.001元
原0.002元
0.004元
原0.008元
deepseek-r1-distill-qwen-1.5b
基于 Qwen2.5-Math-1.5B
32,768
32,768
16,384
限时免费体验
deepseek-r1-distill-qwen-7b
基于 Qwen2.5-Math-7B
0.0005元
0.001元
100万Token
有效期：百炼开通后180天内
deepseek-r1-distill-qwen-14b
基于 Qwen2.5-14B
0.001元
0.003元
deepseek-r1-distill-qwen-32b
基于 Qwen2.5-32B
0.002元
0.006元
deepseek-r1-distill-llama-8b
基于 Llama-3.1-8B
限时免费体验
deepseek-r1-distill-llama-70b
基于 Llama-3.3-70B
以上模型非集成第三方服务，均部署在阿里云百炼服务器上。
最大输出的 Token 数包含思考过程（reasoning_content字段）与最终输出（content字段）的 Token 之和。
并发限流请参考DeepSeek 限流条件。
快速开始

API 使用前提：已获取API Key并完成配置API Key到环境变量。如果通过SDK调用，需要安装 OpenAI 或 DashScope SDK（DashScope Java SDK 版本需要不低于2.18.2）。

如果您首次使用百炼，请参考首次调用通义千问API文档进行百炼服务的开通与计算环境的配置，并将步骤 2：调用大模型API代码中的model参数修改为上表中您需要调用的模型名称。
由于 DeepSeek-R1 类模型的思考过程可能较长，可能导致响应慢或超时，建议您优先使用流式输出方式调用。
OpenAI兼容DashScope
您可以通过 OpenAI SDK 或 OpenAI 兼容的HTTP方式快速体验DeepSeek模型。

PythonNode.jsHTTP
示例代码

 
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"),  # 如何获取API Key：https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

completion = client.chat.completions.create(
    model="deepseek-r1",  # 此处以 deepseek-r1 为例，可按需更换模型名称。
    messages=[
        {'role': 'user', 'content': '9.9和9.11谁大'}
    ]
)

# 通过reasoning_content字段打印思考过程
print("思考过程：")
print(completion.choices[0].message.reasoning_content)

# 通过content字段打印最终答案
print("最终答案：")
print(completion.choices[0].message.content)
返回结果

 
思考过程：

嗯，用户问的是9.9和9.11谁大。首先，我需要确认这两个数字的数值到底是多少。表面上看起来都是小数，但可能用户有不同的表示方式需要注意。

首先，9.9应该就是平常的小数，也就是9加9/10，等于9.9。而9.11可能有两种解读：一种是直接的小数，即9加11/100，也就是9.11；另一种可能是版本号或者某种编号，比如软件版本中的9.9和9.11，这时候可能需要按顺序比较，比如9.9之后是9.10，再是9.11，所以9.11会比9.9大。不过通常情况下，数学问题中的数字还是按照数值来比较的，所以应该排除版本号的解释，直接比较数值大小。

...

总结一下，正确的数值比较中，9.9等于9.90，而9.11等于9.11，所以9.90大于9.11，也就是9.9大于9.11。不过为了避免混淆，可能用户需要更详细的步骤解释。

最终答案：
9.9比9.11大。

**详细比较步骤：**

1. **统一小数位数**：将9.9写成9.90，使其与9.11的小数位数一致。
2. **逐位比较**：
   - **整数部分**：两者均为9，相等。
   - **小数部分**：比较0.90（9.9的小数部分）和0.11（9.11的小数部分）。由于0.90 > 0.11，因此9.90 > 9.11。
   
**结论**：9.9的数值大于9.11。

若涉及版本号（如软件版本），通常按顺序排列为9.9 → 9.10 → 9.11，此时9.11较新。但按纯数学数值比较，9.9更大。
多轮对话

百炼提供的 DeepSeek API 默认不会记录您的历史对话信息。多轮对话功能可以让大模型“拥有记忆”，满足如追问、信息采集等需要连续交流的场景。如果您使用 DeepSeek-R1 类模型，会收到reasoning_content字段（思考过程）与content（回复内容），您可以将content字段通过{'role': 'assistant', 'content':API 返回的content}添加到上下文，无需添加reasoning_content字段。

OpenAI兼容DashScope
您可以通过 OpenAI SDK 或 OpenAI 兼容的 HTTP 方式使用多轮对话功能。

PythonNode.jsHTTP
示例代码

 
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"), # 如何获取API Key：https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 通过 messages 数组实现上下文管理
messages = [
    {'role': 'user', 'content': '你好'}
]

completion = client.chat.completions.create(
    model="deepseek-r1",  # 此处以 deepseek-r1 为例，可按需更换模型名称。
    messages=messages
)

print("="*20+"第一轮对话"+"="*20)
# 通过reasoning_content字段打印思考过程
print("="*20+"思考过程"+"="*20)
print(completion.choices[0].message.reasoning_content)
# 通过content字段打印最终答案
print("="*20+"最终答案"+"="*20)
print(completion.choices[0].message.content)

messages.append({'role': 'assistant', 'content': completion.choices[0].message.content})
messages.append({'role': 'user', 'content': '你是谁'})
print("="*20+"第二轮对话"+"="*20)
completion = client.chat.completions.create(
    model="deepseek-r1",  # 此处以 deepseek-r1 为例，可按需更换模型名称。
    messages=messages
)
# 通过reasoning_content字段打印思考过程
print("="*20+"思考过程"+"="*20)
print(completion.choices[0].message.reasoning_content)
# 通过content字段打印最终答案
print("="*20+"最终答案"+"="*20)
print(completion.choices[0].message.content)
返回结果

 
====================第一轮对话====================
====================思考过程====================
嗯，用户发来了“你好”，这是一个非常常见的中文问候。我需要用中文回应，保持友好和自然。首先，应该回复一个问候，比如“你好！有什么可以帮助你的吗？”这样可以邀请用户进一步说明他们的需求。另外，考虑到用户可能刚接触这个平台，可能需要指导或者有其他问题，所以保持开放式的提问比较合适。同时，要注意语气亲切，避免太过机械。检查一下有没有语法错误，确保回答正确。可能用户只是想打个招呼，也可能接下来有具体的问题，所以准备好后续的支持。另外，根据之前的对话历史，用户可能没有特定的上下文，所以保持回答简洁通用比较好。最后，确认回复符合所有指南，没有涉及敏感或不适当的内容。现在发送回复应该没问题。
====================最终答案====================
你好！有什么可以帮助你的吗？
====================第二轮对话====================
====================思考过程====================
好的，用户问我“你是谁”，需要回答这个问题。首先，我得按照之前设定的角色来回应，也就是深度求索的智能助手DeepSeek-R1。要介绍自己的身份，说明是由深度求索公司开发的，专注于帮助解决问题和提供信息。同时要保持友好和简洁，避免技术术语，让用户容易理解。还要注意格式，用中文口语化的方式，分步骤思考，但不需要用markdown。用户之前用过中文，所以继续用中文回应。另外，用户可能想了解我的功能或背后的技术，但不需要主动扩展，直接回答问题即可。最后，确保回答符合公司的指导方针，没有不适当的内容。检查有没有错别字，语句是否通顺。准备好回答后，就可以给出最终回复了。
====================最终答案====================
您好！我是由中国的深度求索（DeepSeek）公司开发的智能助手DeepSeek-R1。如您有任何问题，我会尽我所能为您提供帮助。
流式输出

DeepSeek-R1 类模型可能会输出较长的思考过程，为了降低超时风险，建议您使用流式输出方式调用 DeepSeek-R1 类模型。

OpenAI兼容DashScope
PythonNode.jsHTTP
示例代码

 
from openai import OpenAI
import os

# 初始化OpenAI客户端
client = OpenAI(
    # 如果没有配置环境变量，请用百炼API Key替换：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

def main():
    reasoning_content = ""  # 定义完整思考过程
    answer_content = ""     # 定义完整回复
    is_answering = False   # 判断是否结束思考过程并开始回复

    # 创建聊天完成请求
    stream = client.chat.completions.create(
        model="deepseek-r1",  # 此处以 deepseek-v3 为例，可按需更换模型名称
        messages=[
            {"role": "user", "content": "9.9和9.11谁大"}
        ],
        stream=True
        # 解除以下注释会在最后一个chunk返回Token使用量
        # stream_options={
        #     "include_usage": True
        # }
    )

    print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")

    for chunk in stream:
        # 处理usage信息
        if not getattr(chunk, 'choices', None):
            print("\n" + "=" * 20 + "Token 使用情况" + "=" * 20 + "\n")
            print(chunk.usage)
            continue

        delta = chunk.choices[0].delta

        # 检查是否有reasoning_content属性
        if not hasattr(delta, 'reasoning_content'):
            continue

        # 处理空内容情况
        if not getattr(delta, 'reasoning_content', None) and not getattr(delta, 'content', None):
            continue

        # 处理开始回答的情况
        if not getattr(delta, 'reasoning_content', None) and not is_answering:
            print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
            is_answering = True

        # 处理思考过程
        if getattr(delta, 'reasoning_content', None):
            print(delta.reasoning_content, end='', flush=True)
            reasoning_content += delta.reasoning_content
        # 处理回复内容
        elif getattr(delta, 'content', None):
            print(delta.content, end='', flush=True)
            answer_content += delta.content

    # 如果需要打印完整内容，解除以下的注释
    """
    print("=" * 20 + "完整思考过程" + "=" * 20 + "\n")
    print(reasoning_content)
    print("=" * 20 + "完整回复" + "=" * 20 + "\n")
    print(answer_content)
    """

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"发生错误：{e}")
返回结果

 
====================思考过程====================

嗯，今天老师布置了一个问题，要比较9.9和9.11哪个大。一开始看起来好像挺简单的，但仔细想想可能有哪里需要注意的地方吧。让我仔细想想看。

首先，我需要明确这两个数的形式。9.9应该是一个小数，也就是9又十分之九，对吧？而9.11可能是9又百分之十一，也就是9.11。不过有时候小数点后面可能有不同的位数，比如有时候会写成9.1和9.10，这时候位数不同但数值其实是一样的，比如9.1等于9.10，因为后面的0不影响大小。不过这里的情况是9.9和9.11，它们的位数不同，一个是十分位，一个是百分位，所以可能需要转换一下单位来比较。

...

所以结论是9.9比9.11大。

不过可能还是有人会混淆，因为看到9.11的小数点后有两位，可能会觉得比一位的大，但实际上是小数点后的每一位代表的是更小的单位。比如十分位是0.1，百分位是0.01，所以第一位小数是十分位，第二位是百分位，所以9.9的十分位是9，也就是0.9，而9.11的十分位是1，百分位是1，所以总共是0.11，所以显然0.9比0.11大很多。

因此，最终的结论应该是9.9大于9.11。
====================完整回复====================

要比较9.9和9.11的大小，可以按照以下步骤进行：

1. **统一小数位数**：将9.9转换为9.90（保持两位小数），以便与9.11直接比较。
2. **逐位比较**：
   - **整数部分**：两者整数部分均为9，相等。
   - **小数部分**：比较0.90（9.90的小数部分）与0.11（9.11的小数部分）。显然，0.90 > 0.11。
3. **结论**：由于小数部分0.90 > 0.11，因此**9.9 > 9.11**。

**答案：9.9比9.11大。**
注意事项

稳定性：如果执行后没有响应、响应超时或者报错An internal error has occured, please try again later or contact service support，请尝试重试或者更换其他DeepSeek模型，也可以尝试使用Qwen最新模型qwen-max-2025-01-25。
高峰期任务可能排队或失败，阿里云百炼持续扩容中，调用失败请稍后重试。
DeepSeek-R1 类模型
不支持的功能
Function Calling、JSON Output、对话前缀续写、上下文硬盘缓存
不支持的参数
temperature、top_p、presence_penalty、frequency_penalty、logprobs、top_logprobs
设置这些参数都不会生效，即使没有输出错误提示。
不建议设置 System Message。
DeepSeek-V3：
参数默认值：
temperature：0.7（取值范围是[0:2)）；
top_p：0.6；
presence_penalty：0.95。
不支持设置的参数和功能：frequency_penalty、logprobs、top_logprobs参数；不支持 Function Call、JSON Output 等功能，敬请关注后续动态。
我的应用和模型在线体验：暂未支持DeepSeek模型，敬请关注后续动态。
联网搜索与深度思考：当前暂不支持联网搜索；只要调用 DeepSeek-R1 类模型即代表开启深度思考（深度思考过程通过reasoning_content返回）。
常见问题

Q：免费额度用完后如何购买 Token？

A：您可以访问费用与成本中心进行充值，确保您的账户没有欠费即可调用 DeepSeek 模型。

调用 DeepSeek 模型会自动扣费，出账周期为一小时，消费明细请前往账单详情进行查看。
Q：如何接入 Chatbox 或 Dify？

A：请根据您的使用情况参考以下步骤：

此处以使用较多的 Chatbox 与 Dify 为例，其它大模型工具接入的方法较为类似。
ChatboxDify
在设置界面的模型提供方选择添加自定义提供方。
image.png

进行 API 设置
名称输入“阿里云-DeepSeek-R1”（可自定义）；
API 域名输入https://dashscope.aliyuncs.com/compatible-mode/v1；
API 路径输入/chat/completions；
API 密钥输入您的 API Key，获取方法请参见：获取API Key；
模型输入您需要使用的 DeepSeek 模型，此处以 deepseek-r1 为例；
单击保存，完成设置。
image.png

进行对话测试
在输入框输入“你是谁？”进行测试：
image.png

Q：可以上传图片或文档进行提问吗？

A：DeepSeek 模型仅支持文本输入，不支持输入图片或文档。通义千问VL模型支持图片输入，Qwen- Long模型支持文档输入。

错误码

如果执行报错，请参见错误信息进行解决。


首次调用通义千问API
更新时间：2025-02-11 14:08:20
产品详情
我的收藏
百炼支持通过API调用大模型，涵盖OpenAI兼容接口、DashScope SDK等接入方式。

如果您已经熟悉大模型调用，也可以直接查看API参考文档文本生成-通义千问。
本文以通义千问为例，引导您完成大模型API调用。您将了解到：

如何获取 API Key
如何配置本地开发环境
如何调用通义千问 API
账号设置

注册账号：如果没有阿里云账号，您需要先注册阿里云账号。
开通百炼：前往百炼控制台，如果页面顶部显示以下消息，您需要开通百炼的模型服务，以获得免费额度。如果未显示该消息，则表示您已经开通。
image

说明
如果开通服务时提示“您尚未进行实名认证”，请先参考实名认证文档对您的阿里云账号进行实名认证。
获取API Key：在控制台的右上角选择API-KEY，然后创建API Key，用于通过API调用大模型。
image

配置API Key到环境变量

建议您把API Key配置到环境变量，从而避免在代码里显式地配置API Key，降低泄漏风险。

配置步骤
选择开发语言

选择您熟悉的语言或工具，用于调用大模型API。

PythonNode.jsJavacurl其它语言
步骤 1：配置Python环境

检查您的Python版本
配置虚拟环境（可选）
安装OpenAI Python SDK或DashScope Python SDK
步骤 2：调用大模型API

OpenAI Python SDKDashScope Python SDK
如果您安装完成了Python以及OpenAI的Python SDK，可以参考以下代码发送您的API请求。您可以新建一个python文件，命名为hello_qwen.py，将以下代码复制到hello_qwen.py中并保存。

 
import os
from openai import OpenAI

try:
    client = OpenAI(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    completion = client.chat.completions.create(
        model="qwen-plus",  # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': '你是谁？'}
            ]
    )
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"错误信息：{e}")
    print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
复制完成后，您可以通过命令行运行python hello_qwen.py或python3 hello_qwen.py。运行后您将会看到输出结果：

 
我是阿里云开发的一款超大规模语言模型，我叫通义千问。
常见问题

Q：我的免费额度已经用完了，如何付费购买通义千问模型的 Token？

A：您可以访问费用与成本中心，确保您的账户没有欠费即可调用通义千问模型。

说明
调用通义千问模型所产生的费用会在一小时后体现在账单上。
下一步

更多模型：示例代码以 qwen-plus 模型为例，百炼还支持其它通义千问模型与 DeepSeek、Llama 等第三方模型，支持的模型以及对应的API参考文档请参见模型列表。
进阶用法：示例代码仅完成了简单问答，如果您想了解通义千问 API 的更多用法，如流式输出（Stream）、结构化输出（JSON Mode）、工具调用（Function Call）等，请参见文本生成目录。
0代码创建大模型应用：请参见0代码构建私有知识问答应用。
通过代码创建大模型应用：请参见Assistant API。
直接与大模型互动：如果您想像通义官网一样，通过对话框与大模型互动，请访问模型体验。
通义官网将通义千问 API 与联网搜索、网页解析等工具进行了集成，与直接调用通义千问 API 效果略有差异。
零代码进行大模型微调：通常来说，对大模型微调需要有人工智能知识背景与工程能力，百炼提供了零代码对大模型进行微调的功能，您仅需提供数据集即可。详情请参见在控制台使用模型调优。