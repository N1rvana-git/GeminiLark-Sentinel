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
FEISHU_WEBHOOK = config.get("Feishu_webhook", "https://open.feishu.cn/")
BASE_URL = config.get("url", "https://api.zetatechs.com").replace("https://", "").replace("http://", "")

genai.configure(
    api_key=GEMINI_API_KEY, 
    transport="rest",
    client_options={"api_endpoint": BASE_URL}
)
model = genai.GenerativeModel('gemini-3-flash-preview-free')

def generate_poetry_content():
    """让大模型生成富有诗意的三句文案或诗词"""
    print("🧠 正在请 Gemini 以文学大师的身份挑选绝美诗词...")
    prompt = """
    你是一位学识渊博、深谙古典诗词与现代美学的文学大师。
    请为我精心挑选和创作 3 段极具诗意、意境深远的文字。必须严格按照以下结构分类提供：
    
    【执行要求】：
    1. **第一段必须是古典诗词**（绝美、深情、旷达或哀婉的古诗词绝句）。
    2. **第二段必须是一段优美的现代散文节选**（名家名篇中回味无穷的散文长句，写景或抒情皆可）。
    3. **第三段必须是你全新创作的一句极具意境的超短散句**。
       - **长度要求**：必须极简！可以是几个字，或者简短的一两句。绝不要长短句拼凑的长文！
       - **内容要求**：**绝对、绝对不能使用或拼凑我在下面给出的任何词汇和例子**！那些例子仅仅是提供给你体会一种“细腻、物哀、孤独、宿命感、通透、释怀”的氛围（Vibe）。你需要用全新的词汇、意象和比喻来进行原创。
       - **氛围参考**（供你理解意境，严禁抄袭词语）：细腻的心感受到更多的是幸福还是悲伤 / 但命运总是让两个人在不同时段顿悟 / 我该如何跟不想失去的人说再见 / 奇迹般和一位觉得我可爱的人维持永久的感情仅此而已 / 扎根成长自然流淌 / 执念开始消失的时候平静的生活贯穿每分每秒 / 而我心里的雨季也不会再来了 / 祝你先于春天 / 物哀 / 兰因絮果 / 吞咽了太多意义，生命只需要呼吸 / 缘分竟默许你离去 / 大部分人都只是我生命的玻璃窗上缓缓划过的雨水 / 等等...
       
    4. 每段文字后面，请附上一段两三句的简短且唯美的赏析，说明其动人之处。
    
    【Output Format】(Strictly markdown only. Do not wrap in ```markdown ... ```)
    
    ### 📜 第一句：[标题 - 作者 (古典诗词)]
    > “ [具体的诗词内容] ”
    
    **💡 赏析**：[唯美解读]
    
    ---
    
    ### 🍃 第二句：[标题 - 作者 (现代散文)]
    > “ [具体的散文内容] ”
    
    **💡 赏析**：[唯美解读]
    
    ---
    
    ### 💧 第三句：[意境短录 - 原创]
    > “ [具体的原创金句内容] ”
    
    **💡 赏析**：[唯美解读]
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        # 清理多余的 markdown 代码块标记
        content = re.sub(r'^```[a-zA-Z]*\n', '', content)
        content = re.sub(r'\n```$', '', content)
        return content
    except Exception as e:
        print(f"Gemini API 调用失败: {e}")
        return ""

def send_poetry_to_feishu(markdown_content):
    """将结果发送到飞书"""
    if not markdown_content or not FEISHU_WEBHOOK.startswith("http"):
        print("🔕 没获取到内容或 Webhook 错误，取消发送。")
        return
        
    print("🚀 正在发送每日诗意共赏飞书卡片...")
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "carmine", # 胭脂红色，充满文学与浪漫气息
                "title": {
                    "content": "🌸 每日诗意共赏 | 纵有千种风情",
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
                            "content": f"由 Gemini API 洗涤心灵 | 每日 14:00 推送 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        }
                    ]
                }
            ]
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(FEISHU_WEBHOOK, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("✅ 飞书通知 (每日诗意) 发送成功！")
    else:
        print(f"❌ 飞书发送失败: {response.text}")


if __name__ == "__main__":
    final_card_content = generate_poetry_content()
    send_poetry_to_feishu(final_card_content)