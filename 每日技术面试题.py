import os
import requests
import google.generativeai as genai
from datetime import datetime
import re

def load_env_config():
    env_vars = {}
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                m = re.search(r'["\']?([^"\':]+?)["\']?\s*[:=]\s*["\']?(.+?)["\']?$', line.strip())
                if m:
                    env_vars[m.group(1).strip()] = m.group(2).strip().rstrip(',')
    return env_vars

config = load_env_config()
GEMINI_API_KEY = config.get("key", "sk-xxx")
FEISHU_WEBHOOK = config.get("Feishu_webhook_JZP", "https://open.feishu.cn/")
BASE_URL = config.get("url", "https://api.zetatechs.com").replace("https://", "").replace("http://", "")

genai.configure(
    api_key=GEMINI_API_KEY, 
    transport="rest",
    client_options={"api_endpoint": BASE_URL}
)
model = genai.GenerativeModel('gemini-3-flash-preview-free')

def generate_interview_questions():
    """依靠大模型的能力，生成 4 道高频高质量的技术面试题"""
    
    print("🧠 正在请 Gemini 出几道最新的 AI 全栈与后端服务端开发面试题...")
    prompt = f"""
    你是资深AI全栈工程师，擅长出硬核且贴近真实业务场景的技术面试题。
    请为用户每天出4道技术面试题，格式必须是精美的Markdown。

    【题目内容分配】
    总共 4 道题：

    1. 【🤖 大模型应用架构】（2道）
       - 考察并发处理、Prompt注入防御、向量检索、RAG架构等
       - 每道题包含：题目、考察点、参考答案、解析

    2. 【⚡ FastAPI后端开发】（2道）
       - 考察API设计、中间件、异步编程、数据库集成、性能优化等
       - 每道题包含：题目、考察点、参考答案、解析

    【Output Format】(Strictly output ONLY markdown, no other conversational words or codeblocks fences. Must be rigorous but readable, without garbled characters or emojis rendering badly).
    
    使用精美的卡片排版，emoji装饰，清晰层级。示例格式参考：
    
    ## 🤖 大模型应用架构
    ### 📌 题目1：[具体题目]
    - **考察点**：xxx
    - **参考答案**：xxx
    - **解析**：xxx
    
    （第二道题...以此类推）
    
    ---
    
    ## ⚡ FastAPI后端开发
    ### 📌 题目3：[具体题目]
    - **考察点**：xxx
    - **参考答案**：xxx
    - **解析**：xxx
    
    （第四道题...以此类推）
    
    【要求】
    - 题目要贴近真实的生产、运维工作场景
    - 答案要准确、专业，且代码/表述简明扼要
    - 难度适中，适合有基础的实战开发者（如 2~5 年经验）
    - 可以紧密结合当前的最新技术热点（如大语言模型的最新架构，异步高并发等）
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        # 清理可能的 markdown 标识符
        content = re.sub(r'^```[a-zA-Z]*\n', '', content)
        content = re.sub(r'\n```$', '', content)
        return content
    except Exception as e:
        print(f"Gemini API 调用失败: {e}")
        return ""

def send_interview_to_feishu(markdown_content):
    """将结果发送到飞书交互式卡片"""
    if not markdown_content or not FEISHU_WEBHOOK.startswith("http"):
        print("🔕 Webhook 错误或今日生成为空，取消发送。")
        return
        
    print("🚀 正在发送每日技术面试题飞书卡片...")
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "indigo", # 靛蓝色，极客且严谨
                "title": {
                    "content": "💻 每日技术面试题 | AI 全栈与 Python 后端",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": markdown_content
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"由 Gemini API & Python 随机抽取考点演绎 | 每天保持手感 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        }
                    ]
                }
            ]
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(FEISHU_WEBHOOK, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("✅ 飞书通知 (技术面试题) 发送成功！")
    else:
        print(f"❌ 飞书发送失败: {response.text}")

if __name__ == "__main__":
    final_card_content = generate_interview_questions()
    send_interview_to_feishu(final_card_content)
