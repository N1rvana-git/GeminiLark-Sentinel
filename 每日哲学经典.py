import os
import requests
import google.generativeai as genai
from datetime import datetime
import re
import random

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
FEISHU_WEBHOOK_JZP = config.get("Feishu_webhook_JZP", "https://open.feishu.cn/")
FEISHU_WEBHOOK_DYX = config.get("Feishu_webhook_DYX", "https://open.feishu.cn/")
BASE_URL = config.get("url", "https://api.zetatechs.com").replace("https://", "").replace("http://", "")

genai.configure(
    api_key=GEMINI_API_KEY, 
    transport="rest",
    client_options={"api_endpoint": BASE_URL}
)
model = genai.GenerativeModel('gpt-5.4-free')

def generate_philosophy_card():
    """纯依靠大模型的能力，选择哲学段落进行精写导读"""
    
    print("🧠 正在请 Gemini 随机挑选一位全球著名的哲学家及著作进行导读生成...")
    prompt = f"""
    你是一个极其深邃且富有洞察力的哲学导师。
    今天的任务是为读者带来一篇每日哲学经典导读。
    
    首先，请你发挥自己庞大的知识库，从全球哲学历史的长河中（可以是东方哲学、西方哲学、古代、近代或现代）**完全随机挑选一位著名的哲学家和TA的一本代表作**。每天都要尝试发掘不同的大师或不同的流派。
    然后，请挑选这本著作中最有穿透力、最震撼的经典语录，以此作为切入点，写一篇约 500 字的导读。

    【Output Format】(Strictly output ONLY markdown, no other conversational words or codeblocks fences. Content must be rigorous but readable, without garbled characters or emojis rendering badly).
    
    【📚 著作出处】
    [写出你本次随机抽取的哲学家及著作信息，比如：王阳明《传习录》 或 尼采《查拉图斯特拉如是说》]

    【📜 经典语录】
    [写出那句话的原话或核心论述，约50字。如果是外语请给出最优雅的中文翻译]
    
    【👤 作者简介】
    [30字以内的一句话简单概括该哲学家及其核心流派]
    
    【💭 深度导读】
    [分为以下几段自然展开，无需标明小标题，保持连贯，加粗核心词即可，总字数大约 500 字：
    - 这句话的语境与背景
    - 核心含义的详细解读
    - 对当代快节奏、充满焦虑与异化的现代生活的深刻启示与实践意义
    - 留给读者的一到两个直击灵魂的延伸思考问题]
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

def send_philosophy_to_feishu(markdown_content):
    """将结果发送到飞书交互式卡片"""
    if not markdown_content:
        print("🔕 Webhook 错误或今日生成为空，取消发送。")
        return
        
    print("🚀 正在发送哲学导读飞书卡片...")
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "carmine", # 红色/胭脂红 比较有复古学术氛围
                "title": {
                    "content": "🦉 每日哲学导读 | 叩问灵魂的 500 字",
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
                            "content": f"由 Gemini API & Python 随机抽取经典著作演绎 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        }
                    ]
                }
            ]
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    
    webhooks = [FEISHU_WEBHOOK_JZP, FEISHU_WEBHOOK_DYX]
    for webhook in webhooks:
        if not webhook.startswith("http"):
            continue
        response = requests.post(webhook, json=payload, headers=headers)
        if response.status_code == 200:
            print(f"✅ 飞书通知发送成功！({webhook[-10:]})")
        else:
            print(f"❌ 飞书发送失败 ({webhook[-10:]}): {response.text}")

if __name__ == "__main__":
    final_card_content = generate_philosophy_card()
    send_philosophy_to_feishu(final_card_content)
