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
                # 简单解析 .env 格式
                m = re.search(r'["\']?([^"\':]+?)["\']?\s*[:=]\s*["\']?(.+?)["\']?$', line.strip())
                if m:
                    env_vars[m.group(1).strip()] = m.group(2).strip().rstrip(',')
    return env_vars

config = load_env_config()
GEMINI_API_KEY = config.get("key", "sk-xxx")
FEISHU_WEBHOOK_JZP = config.get("Feishu_webhook_JZP", "https://open.feishu.cn/")
BASE_URL = config.get("url", "https://api.zetatechs.com").replace("https://", "").replace("http://", "")

# 初始化 Gemini API 客户端 (走 HTTP REST 适配代理)
genai.configure(
    api_key=GEMINI_API_KEY, 
    transport="rest",
    client_options={"api_endpoint": BASE_URL}
)
# 仍然使用兼容你额度的免费版或 flash 预览版模型
model = genai.GenerativeModel('gemini-3-flash-preview-free')

def search_foreign_tech_news():
    """搜寻国外知名媒体科技内容 (The Verge, TechCrunch, Wired 等)"""
    print("🌍 正在通过 Google News RSS 搜寻外媒最新科技资讯...")
    
    # 构建外媒搜索词：必须带媒体源，限制为过去 24 小时
    media_sites = "site:techcrunch.com OR site:wired.com OR site:theverge.com OR site:arstechnica.com"
    keywords = "AI OR LLM OR framework OR open source OR GPT"
    query = f"({keywords}) AND ({media_sites})"
    
    # 注意这里改用 us 节点，全英数据源
    url = f"https://news.google.com/rss/search?q={quote(query)}+when:1d&hl=en-US&gl=US&ceid=US:en"
    
    search_results = []
    try:
        r = requests.get(url, timeout=15)
        r.encoding = 'utf-8' 
        root = ET.fromstring(r.text)
        items = root.findall(".//item")
        
        # 只取前 15 条提供给大模型参考
        for item in items[:15]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            # 摘要里通常有短短的引子，由于 RSS 里的结构，我们合并进发给大模型的参考
            desc = item.findtext("description", "")
            desc_text = re.sub(r'<[^>]+>', '', desc) # 去除HTML标签
            
            search_results.append(f"Title: {title}\nDate: {pub_date}\nLink: {link}\nSnippet: {desc_text}")
            
        if not search_results:
            return ""
        return "\n\n".join(search_results)
    except Exception as e:
        print(f"外媒RSS获取失败: {e}")
        return ""

def generate_english_reading_card(news_text):
    """调用 Gemini API 生成精美的英文科技新闻卡片"""
    if not news_text:
        return "暂无新闻", ""
        
    print("🧠 正在请 Gemini 精读外媒文章并提炼生词解析...")
    prompt = f"""
    You are an expert tech news editor and a very patient English teacher.
    Please read the following English search results from the past 24 hours:
    
    {news_text}
    
    【Task】
    Select the **most important** and technically deep news item (preferably related to AI, LLM, programming frameworks, or open-source tools). Do not choose ads.
    Generate a bilingual "Daily English Reading" snippet for Chinese tech professionals.
    
    【Output Format】(Strictly output ONLY markdown, no other conversational words, and include emojis. Never output any garbled text formatting like markdown codeblock fences at the start/end).
    
    【📰 新闻标题】[An engaging English title with emoji]
    
    【📝 原文节选】
    [Write a fluent, original-like English paragraph about 100 words summarizing or quoting the selected news item. Make sure the vocabulary is professional.]
    
    【📚 生词标注】
    [Extract 3 to 5 key professional or advanced vocabulary words from the English text above, using lists. Format:
    - **word** /[phonetic symbol]/: Chinese meaning
    Example: - **framework** /ˈfreɪmwɜːk/: 框架]
    
    【🇨🇳 中文翻译】
    [Provide a natural and flawless Chinese translation of the 100-word paragraph]
    
    🔗 **原文链接**：[The link of the selected news item]
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        # 清除大模型可能生成的额外 markdown wrap 标识 (如 ```markdown ...)
        content = re.sub(r'^```[a-zA-Z]*\n', '', content)
        content = re.sub(r'\n```$', '', content)
        return content
    except Exception as e:
        print(f"Gemini API 调用失败: {e}")
        return ""

def send_tech_news_to_feishu(markdown_content):
    """将结果发送到飞书"""
    if not markdown_content or "暂无新闻" in markdown_content or not FEISHU_WEBHOOK_JZP.startswith("http"):
        print("🔕 今日暂无外媒新闻或Webhook没准备好，不打扰。")
        return
        
    print("🚀 正在发送英文精读飞书卡片...")
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "purple",
                "title": {
                    "content": "✨ 每日科技外媒资讯 | 碎片阅读分享",
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
                            "content": f"由 Gemini API & Python 生成 | 外媒科技精读 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        }
                    ]
                }
            ]
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(FEISHU_WEBHOOK_JZP, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("✅ 飞书通知 (英文精读) 发送成功！")
    else:
        print(f"❌ 飞书发送失败: {response.text}")

if __name__ == "__main__":
    # 1. 拿近 24 小时的全英 Tech / AI 外媒文章
    raw_eng_news = search_foreign_tech_news()
    
    # 2. 扔给大模型写 “原生节选、提取生词、配上翻译”
    final_card_content = generate_english_reading_card(raw_eng_news)
    
    # 3. 发飞书
    send_tech_news_to_feishu(final_card_content)
