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
FEISHU_WEBHOOK_DYX = config.get("Feishu_webhook_DYX", "https://open.feishu.cn/")
BASE_URL = config.get("url", "https://api.zetatechs.com").replace("https://", "").replace("http://", "")

genai.configure(
    api_key=GEMINI_API_KEY, 
    transport="rest",
    client_options={"api_endpoint": BASE_URL}
)
model = genai.GenerativeModel('gpt-5.4-free')

def generate_poetry_content():
    """生成三段克制、有留白感的文字：古典诗词 + 散文短句 + 原创短句"""
    print("🧠 正在生成今日文字...")
    prompt = """
你是一位敏感、克制的文字观察者。请为我生成3段文字，每段都追求"淡而有余味"。

【三段内容要求】

第一段：古典诗词
- 挑选一首绝句或小令，不求家喻户晓，但求意境深远
- 偏好：时间感、宿命感、物哀、释然类的主题

第二段：现代散文短句
- 从名家作品中摘取一句或一小段（不超过两句话）
- 偏好：平淡日常里见深意的句子，不要华丽辞藻
- 参考气质：周作人、汪曾祺、是枝裕和电影台词感

第三段：原创短句文案（核心重点）
- 风格严格参考以下示例的调性：
  "是否有一刹那 我们在命运之外"
  "日与月 夏与冬 更迭难休"
  "倘若时间只是人为的停顿"
  "昨天太重 明天太远 就到这 好吗"
  "命运在新陈代谢 很深的东西变得很浅"
  "细腻的心 感受到更多是幸福还是悲伤"
  "在失去的所有人里 我最怀恋我自己"
  "谢谢远去的一切"
  "生命本就层峦叠嶂"
  "别在最疲惫的时候审视自己的人生 你只是今天有点累"

- 创作要求：
  1. 极短！一句话为主，最多不超过两句
  2. 用词朴素，拒绝华丽辞藻和文艺腔堆砌
  3. 情绪克制，不说透，留大量空白给读者自己填
  4. 可以有宿命感、时间感、疏离感、轻微的释然或遗憾
  5. 像一个人坐在窗边发呆时冒出来的念头，不像写作文
  6. 绝对禁止"风都显得多余""人间烟火"这类烂大街表达
  7. 也可以是纯意象/纯名词组合，甚至2-4个emoji组成的情绪表达

【每段注解要求】
- 每段配一句极短的注解，一两句话点到为止
- 不要写"这句短得像一声轻叹，却留下很长的回响"这种空话
- 直接说：好在哪里，或者它触碰到了什么

【输出格式】（纯markdown，不要代码块）

### 一、[诗词标题] — [作者]
> [内容]

注：[一句话赏析]

---

### 二、[篇目] — [作者]
> [内容]

注：[一句话赏析]

---

### 三、[两个字的短标题]
> [原创文案内容]

注：[一句话赏析]
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
    if not markdown_content:
        print("🔕 没获取到内容，取消发送。")
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
                    "content": "今日三句",
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
                            "content": f"每日 14:00 · {datetime.now().strftime('%Y-%m-%d')}"
                        }
                    ]
                }
            ]
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    
    webhooks = [FEISHU_WEBHOOK, FEISHU_WEBHOOK_DYX]
    for webhook in webhooks:
        if not webhook.startswith("http"):
            continue
        response = requests.post(webhook, json=payload, headers=headers)
        if response.status_code == 200:
            print(f"✅ 飞书通知 (每日诗意) 发送成功！({webhook[-10:]})")
        else:
            print(f"❌ 飞书发送失败 ({webhook[-10:]}): {response.text}")


if __name__ == "__main__":
    final_card_content = generate_poetry_content()
    send_poetry_to_feishu(final_card_content)