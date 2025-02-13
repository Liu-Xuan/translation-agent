# 导入系统模块
import os  # 操作系统功能
import re  # 正则表达式
from glob import glob  # 文件路径模式匹配

# 导入第三方库
import gradio as gr  # Web界面框架
from process import (  # 导入核心处理模块
    diff_texts,  # 文本差异比较
    extract_docx,  # Word文档提取
    extract_pdf,  # PDF文档提取
    extract_text,  # 文本文件提取
    model_load,  # 模型加载
    translator,  # 单模型翻译器
    translator_sec,  # 双模型翻译器
)


def huanik(
    endpoint: str,  # 主API端点
    base: str,  # 主API基础URL
    model: str,  # 主翻译模型
    api_key: str,  # 主API密钥
    choice: str,  # 是否使用双模型翻译
    endpoint2: str,  # 第二API端点
    base2: str,  # 第二API基础URL
    model2: str,  # 第二翻译模型
    api_key2: str,  # 第二API密钥
    source_lang: str,  # 源语言
    target_lang: str,  # 目标语言
    source_text: str,  # 源文本
    country: str,  # 目标国家/地区
    max_tokens: int,  # 最大token数
    temperature: int,  # 温度参数
    rpm: int,  # 每分钟请求限制
):
    """
    主要翻译处理函数
    
    该函数是整个翻译系统的核心，负责协调不同组件完成翻译任务。
    支持单模型和双模型两种翻译模式，并提供翻译过程的可视化比较。
    
    Args:
        endpoint: 主要API服务提供商
        base: 主要API的基础URL
        model: 主要翻译模型名称
        api_key: 主要API密钥
        choice: 是否启用双模型翻译
        endpoint2: 第二个API服务提供商
        base2: 第二个API的基础URL
        model2: 第二个翻译模型名称
        api_key2: 第二个API密钥
        source_lang: 源语言
        target_lang: 目标语言
        source_text: 待翻译的文本
        country: 目标国家/地区
        max_tokens: 单次翻译的最大token数
        temperature: 模型输出的随机性参数
        rpm: 每分钟最大请求次数
    
    Returns:
        tuple: (初始翻译, 翻译反思, 最终翻译, 差异对比)
    """
    # 输入验证
    if not source_text or source_lang == target_lang:
        raise gr.Error(
            "Please check that the content or options are entered correctly."
        )

    # 加载主要翻译模型
    try:
        model_load(endpoint, base, model, api_key, temperature, rpm)
    except Exception as e:
        raise gr.Error(f"An unexpected error occurred: {e}") from e

    # 清理源文本中的空行
    source_text = re.sub(r"(?m)^\s*$\n?", "", source_text)

    # 根据选择使用不同的翻译模式
    if choice:
        # 使用双模型翻译模式
        init_translation, reflect_translation, final_translation = (
            translator_sec(
                endpoint2=endpoint2,
                base2=base2,
                model2=model2,
                api_key2=api_key2,
                source_lang=source_lang,
                target_lang=target_lang,
                source_text=source_text,
                country=country,
                max_tokens=max_tokens,
            )
        )
    else:
        # 使用单模型翻译模式
        init_translation, reflect_translation, final_translation = translator(
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=source_text,
            country=country,
            max_tokens=max_tokens,
        )

    # 生成翻译差异对比可视化
    final_diff = gr.HighlightedText(
        diff_texts(init_translation, final_translation),  # 比较初始和最终翻译
        label="Diff translation",  # 标签
        combine_adjacent=True,  # 合并相邻的差异
        show_legend=True,  # 显示图例
        visible=True,  # 默认可见
        color_map={"removed": "red", "added": "green"},  # 差异颜色映射
    )

    return init_translation, reflect_translation, final_translation, final_diff


def update_model(endpoint):
    """
    根据选择的端点更新模型选项
    
    为不同的API服务提供商配置默认的模型选项，
    并控制自定义API设置的显示状态。
    
    Args:
        endpoint: API服务提供商名称
    Returns:
        tuple: (更新后的模型值, 基础URL输入框的显示状态)
    """
    # 定义每个端点对应的默认模型
    endpoint_model_map = {
        "Groq": "llama3-70b-8192",  # Groq的默认模型
        "OpenAI": "gpt-4o",  # OpenAI的默认模型
        "TogetherAI": "Qwen/Qwen2-72B-Instruct",  # TogetherAI的默认模型
        "Ollama": "llama3",  # Ollama的默认模型
        "CUSTOM": "",  # 自定义API不预设模型
    }
    
    # 对于自定义API，显示基础URL输入框
    if endpoint == "CUSTOM":
        base = gr.update(visible=True)
    else:
        base = gr.update(visible=False)
    
    return gr.update(value=endpoint_model_map[endpoint]), base


def read_doc(path):
    """
    根据文件类型读取文档内容
    
    支持多种文档格式的内容提取，包括PDF、Word、
    纯文本等多种格式。
    
    Args:
        path: 文档文件路径
    Returns:
        str: 提取的文本内容
    Raises:
        gr.Error: 当文件格式不支持时抛出错误
    """
    # 获取文件扩展名
    file_type = path.split(".")[-1]
    print(file_type)
    
    # 检查是否为支持的文件类型
    if file_type in ["pdf", "txt", "py", "docx", "json", "cpp", "md"]:
        # 根据文件类型选择相应的提取方法
        if file_type.endswith("pdf"):
            content = extract_pdf(path)
        elif file_type.endswith("docx"):
            content = extract_docx(path)
        else:
            content = extract_text(path)
        # 清理空行并返回内容
        return re.sub(r"(?m)^\s*$\n?", "", content)
    else:
        raise gr.Error("Oops, unsupported files.")


def enable_sec(choice):
    """
    控制二次翻译选项的显示状态
    
    Args:
        choice: 是否启用二次翻译
    Returns:
        gr.update: Gradio更新对象，控制组件可见性
    """
    if choice:
        return gr.update(visible=True)
    else:
        return gr.update(visible=False)


def update_menu(visible):
    """
    切换菜单的显示状态
    
    Args:
        visible: 当前的可见状态
    Returns:
        tuple: (新的可见状态, Gradio更新对象)
    """
    return not visible, gr.update(visible=not visible)


def export_txt(strings):
    """
    将翻译结果导出到文本文件
    
    在outputs目录下创建序号递增的文本文件，
    用于保存翻译结果。
    
    Args:
        strings: 要保存的文本内容
    Returns:
        gr.update: Gradio更新对象，包含文件路径和可见性
    """
    if strings:
        # 创建输出目录
        os.makedirs("outputs", exist_ok=True)
        # 获取当前文件数量作为新文件的序号
        base_count = len(glob(os.path.join("outputs", "*.txt")))
        # 生成新文件路径
        file_path = os.path.join("outputs", f"{base_count:06d}.txt")
        # 写入内容
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(strings)
        return gr.update(value=file_path, visible=True)
    else:
        return gr.update(visible=False)


def switch(source_lang, source_text, target_lang, output_final):
    """
    切换源语言和目标语言的函数
    
    实现源语言和目标语言的快速交换，同时处理相关文本内容的切换。
    
    Args:
        source_lang: 当前的源语言
        source_text: 当前的源文本
        target_lang: 当前的目标语言
        output_final: 当前的翻译结果
    Returns:
        tuple: 包含四个gr.update对象，分别更新相关组件的值
    """
    if output_final:
        # 如果有翻译结果，交换语言和文本
        return (
            gr.update(value=target_lang),
            gr.update(value=output_final),
            gr.update(value=source_lang),
            gr.update(value=source_text),
        )
    else:
        # 如果没有翻译结果，只交换语言
        return (
            gr.update(value=target_lang),
            gr.update(value=source_text),
            gr.update(value=source_lang),
            gr.update(value=""),
        )


def close_btn_show():
    """显示关闭按钮"""
    return gr.update(visible=False), gr.update(visible=True)


def close_btn_hide(output_diff):
    """
    控制关闭按钮的显示状态
    
    Args:
        output_diff: 差异对比结果
    Returns:
        tuple: 包含两个gr.update对象，控制按钮的可见性
    """
    if output_diff:
        return gr.update(visible=True), gr.update(visible=False)
    else:
        return gr.update(visible=False), gr.update(visible=True)


# Web界面标题HTML
TITLE = """
    <div style="display: inline-flex;">
        <div style="margin-left: 6px; font-size:32px; color: #6366f1"><b>Translation Agent</b> WebUI</div>
    </div>
"""

# CSS样式定义
CSS = """
    /* 标题样式 */
    h1 {
        text-align: center;
        display: block;
        height: 10vh;
        align-content: center;
    }
    /* 隐藏页脚 */
    footer {
        visibility: hidden;
    }
    /* 菜单按钮样式 */
    .menu_btn {
        width: 48px;
        height: 48px;
        max-width: 48px;
        min-width: 48px;
        padding: 0px;
        background-color: transparent;
        border: none;
        cursor: pointer;
        position: relative;
        box-shadow: none;
    }
    /* 菜单按钮动画效果 */
    .menu_btn::before,
    .menu_btn::after {
        content: '';
        position: absolute;
        width: 30px;
        height: 3px;
        background-color: #4f46e5;
        transition: transform 0.3s ease;
    }
    .menu_btn::before {
        top: 12px;
        box-shadow: 0 8px 0 #6366f1;
    }
    .menu_btn::after {
        bottom: 16px;
    }
    .menu_btn.active::before {
        transform: translateY(8px) rotate(45deg);
        box-shadow: none;
    }
    .menu_btn.active::after {
        transform: translateY(-8px) rotate(-45deg);
    }
    /* 语言选择框样式 */
    .lang {
        max-width: 100px;
        min-width: 100px;
    }
"""

# JavaScript代码，用于菜单按钮动画
JS = """
    function () {
        const menu_btn = document.getElementById('menu');
        menu_btn.classList.toggle('active');
    }
"""

with gr.Blocks(theme="soft", css=CSS, fill_height=True) as demo:
    with gr.Row():
        visible = gr.State(value=True)
        menu_btn = gr.Button(
            value="", elem_classes="menu_btn", elem_id="menu", size="sm"
        )
        gr.HTML(TITLE)
    with gr.Row():
        with gr.Column(scale=1) as menubar:
            endpoint = gr.Dropdown(
                label="Endpoint",
                choices=["OpenAI", "Groq", "TogetherAI", "Ollama", "CUSTOM"],
                value="OpenAI",
            )
            choice = gr.Checkbox(
                label="Additional Endpoint",
                info="Additional endpoint for reflection",
            )
            model = gr.Textbox(
                label="Model",
                value="gpt-4o",
            )
            api_key = gr.Textbox(
                label="API_KEY",
                type="password",
            )
            base = gr.Textbox(label="BASE URL", visible=False)
            with gr.Column(visible=False) as AddEndpoint:
                endpoint2 = gr.Dropdown(
                    label="Additional Endpoint",
                    choices=[
                        "OpenAI",
                        "Groq",
                        "TogetherAI",
                        "Ollama",
                        "CUSTOM",
                    ],
                    value="OpenAI",
                )
                model2 = gr.Textbox(
                    label="Model",
                    value="gpt-4o",
                )
                api_key2 = gr.Textbox(
                    label="API_KEY",
                    type="password",
                )
                base2 = gr.Textbox(label="BASE URL", visible=False)
            with gr.Row():
                source_lang = gr.Textbox(
                    label="Source Lang",
                    value="English",
                    elem_classes="lang",
                )
                target_lang = gr.Textbox(
                    label="Target Lang",
                    value="Spanish",
                    elem_classes="lang",
                )
            switch_btn = gr.Button(value="🔄️")
            country = gr.Textbox(
                label="Country", value="Argentina", max_lines=1
            )
            with gr.Accordion("Advanced Options", open=False):
                max_tokens = gr.Slider(
                    label="Max tokens Per Chunk",
                    minimum=512,
                    maximum=2046,
                    value=1000,
                    step=8,
                )
                temperature = gr.Slider(
                    label="Temperature",
                    minimum=0,
                    maximum=1.0,
                    value=0.3,
                    step=0.1,
                )
                rpm = gr.Slider(
                    label="Request Per Minute",
                    minimum=1,
                    maximum=1000,
                    value=60,
                    step=1,
                )

        with gr.Column(scale=4):
            source_text = gr.Textbox(
                label="Source Text",
                value="If one advances confidently in the direction of his dreams, and endeavors to live the life which he has imagined, he will meet with a success unexpected in common hours.",
                lines=12,
            )
            with gr.Tab("Final"):
                output_final = gr.Textbox(
                    label="Final Translation", lines=12, show_copy_button=True
                )
            with gr.Tab("Initial"):
                output_init = gr.Textbox(
                    label="Init Translation", lines=12, show_copy_button=True
                )
            with gr.Tab("Reflection"):
                output_reflect = gr.Textbox(
                    label="Reflection", lines=12, show_copy_button=True
                )
            with gr.Tab("Diff"):
                output_diff = gr.HighlightedText(visible=False)
    with gr.Row():
        submit = gr.Button(value="Translate")
        upload = gr.UploadButton(label="Upload", file_types=["text"])
        export = gr.DownloadButton(visible=False)
        clear = gr.ClearButton(
            [source_text, output_init, output_reflect, output_final]
        )
        close = gr.Button(value="Stop", visible=False)

    switch_btn.click(
        fn=switch,
        inputs=[source_lang, source_text, target_lang, output_final],
        outputs=[source_lang, source_text, target_lang, output_final],
    )

    menu_btn.click(
        fn=update_menu, inputs=visible, outputs=[visible, menubar], js=JS
    )
    endpoint.change(fn=update_model, inputs=[endpoint], outputs=[model, base])

    choice.select(fn=enable_sec, inputs=[choice], outputs=[AddEndpoint])
    endpoint2.change(
        fn=update_model, inputs=[endpoint2], outputs=[model2, base2]
    )

    start_ta = submit.click(
        fn=huanik,
        inputs=[
            endpoint,
            base,
            model,
            api_key,
            choice,
            endpoint2,
            base2,
            model2,
            api_key2,
            source_lang,
            target_lang,
            source_text,
            country,
            max_tokens,
            temperature,
            rpm,
        ],
        outputs=[output_init, output_reflect, output_final, output_diff],
    )
    upload.upload(fn=read_doc, inputs=upload, outputs=source_text)
    output_diff.change(fn=export_txt, inputs=output_final, outputs=[export])

    submit.click(fn=close_btn_show, outputs=[clear, close])
    output_diff.change(
        fn=close_btn_hide, inputs=output_diff, outputs=[clear, close]
    )
    close.click(fn=None, cancels=start_ta)

if __name__ == "__main__":
    demo.queue(api_open=False).launch(show_api=False, share=False)
