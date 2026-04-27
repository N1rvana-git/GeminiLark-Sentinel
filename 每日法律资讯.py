import os
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
from datetime import datetime
import re
from urllib.parse import quote

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
FEISHU_WEBHOOK_DYX = config.get("Feishu_webhook_DYX", "https://open.feishu.cn/")
BASE_URL = config.get("url", "https://api.zetatechs.com").replace("https://", "").replace("http://", "")

genai.configure(
    api_key=GEMINI_API_KEY, 
    transport="rest",
    client_options={"api_endpoint": BASE_URL}
)
model = genai.GenerativeModel('gemini-3-flash-preview-free')

def search_news(query):
    """使用 Google News RSS 获取新闻"""
    url = f"https://news.google.com/rss/search?q={quote(query)}+when:2d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    search_results = []
    try:
        r = requests.get(url, timeout=15)
        r.encoding = 'utf-8' 
        root = ET.fromstring(r.text)
        items = root.findall(".//item")
        
        for item in items[:8]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            search_results.append(f"标题: {title}\n日期: {pub_date}\n链接: {link}")
            
        return "\n\n".join(search_results)
    except Exception as e:
        print(f"RSS获取失败 ({query}): {e}")
        return ""

def generate_legal_post(domestic_news, foreign_news, cases_news):
    """调用 Gemini API 生成文案"""
    print("🧠 正在请 Gemini 整合法律知识与新闻...")
    prompt = f"""
    你是一个资深的法学导师。需要为法学学生“平常鑫”整理一份每日资讯。
    
    【输入材料】
    【国内法律/时事新闻】：
    {domestic_news}
    
    【国内热点法律案件】：
    {cases_news}
    
    【国际/国外法律新闻】：
    {foreign_news}

    【任务要求】
    请生成一篇内容，严格包含以下部分：
    1. **打招呼语**：必须包含对“平常鑫”的称呼，加上一句激励人心的话语，语气要像一位关怀备至的导师或贴心的朋友。
    2. **法学知识点**：请结合法学原理、重要法条或者经典的法学理论（可以是民法、刑法、宪法、法理学等领域），写一个硬核且有价值的知识点，帮助法学生复习。必须真实客观。
    3. **国内热门案例**：从上方【国内热点法律案件】材料中挑出一个最新发生的真实国内纠纷或判决案例。简述案情经过，并从法律适用或争议焦点的角度给出简短专业的评析（必须真实，不可生造）。
    4. **国内法律动态**：从上方【国内法律/时事新闻】材料中挑出一个最重要的宏观新闻进行简练概括（如果材料中没有，请说明今日无国内重点法律动态）。
    5. **国外法律新闻**：从上方【国际/国外法律新闻】材料中挑出一个最有价值的国际/国外法律或时政新闻进行简要概括和略微评析。
    6. **法硕考研/法考每日一题**：请随机生成一道高质量的考研法硕（非法学/法学）或法考级别的真题/模拟题（可以是刑法、民法等学科的案例分析大题，也可以是包含易错点的客观选择题）。必须先写出完整的“案情/题干”，接着提出具体问题（如“甲的行为如何定性？”），最后附上详细、专业的标准答案及法理/法条深度解析（风格参考法硕名师的考研仿真案例）。

    输出格式必须为 Markdown（但不要包裹在```markdown 中）。
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r'^```[a-zA-Z]*\n', '', text)
        text = re.sub(r'\n```$', '', text)
        return text
    except Exception as e:
        print(f"Gemini API 调用失败: {e}")
        return ""

def send_to_feishu(markdown_content):
    """将结果发送到飞书"""
    if not markdown_content or not FEISHU_WEBHOOK_DYX.startswith("http"):
        print("🔕 没获取到内容或 Webhook 错误，取消发送。")
        return
        
    print("🚀 正在发送飞书法律资讯卡片...")
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "blue",
                "title": {
                    "content": "⚖️ 每日法律资讯与知识点",
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
                            "content": f"由 Gemini API 汇编 | 每日 14:00 推送 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        }
                    ]
                }
            ]
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(FEISHU_WEBHOOK_DYX, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("✅ 飞书通知发送成功！")
    else:
        print(f"❌ 飞书发送失败: {response.text}")

if __name__ == "__main__":
    domestic = search_news("国内 法律 OR 司法 OR 法治 OR 法院")
    foreign = search_news("国际法 OR 跨国诉讼 OR 国外法律 OR 美国最高法 OR 欧盟法")
    cases = search_news("国内 法院 (判决 OR 宣判 OR 庭审 OR 典型案例 OR 纠纷) -小说 -影视")
    final_content = generate_legal_post(domestic, foreign, cases)
    if final_content:
        send_to_feishu(final_content)
