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

# 根据代理服务器特性，往往需要走 HTTP(REST) 协议而不是原生的 gRPC
genai.configure(
    api_key=GEMINI_API_KEY, 
    transport="rest",
    client_options={"api_endpoint": BASE_URL}
)
# 回退到兼容性最广的 flash 模型，你也可以换回预览版
model = genai.GenerativeModel('gpt-5.4-free')

def search_latest_news():
    """使用免费且稳定的 Google News RSS 获取新闻"""
    print("🔍 正在通过 Google News RSS 搜索最新 AI 资讯...")
    query = "AI大模型 OR 人工智能 OR Agent框架 OR 大模型API"
    url = f"https://news.google.com/rss/search?q={quote(query)}+when:1d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    
    search_results = []
    try:
        r = requests.get(url, timeout=15)
        # 强制指定编码防止乱码
        r.encoding = 'utf-8' 
        root = ET.fromstring(r.text)
        items = root.findall(".//item")
        
        # 只取前 15 条传给 Gemini 总结，以免 Token 过多
        for item in items[:15]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            search_results.append(f"标题: {title}\n日期: {pub_date}\n链接: {link}")
            
        if not search_results:
            return ""
        return "\n\n".join(search_results)
    except Exception as e:
        print(f"RSS获取失败: {e}")
        return ""

def summarize_with_gemini(news_text):
    """调用 Gemini API 进行过滤和格式化"""
    if not news_text:
        return "暂无新闻"
        
    print("🧠 正在请 Gemini 筛选并整理排版...")
    prompt = f"""
    你是一个资深的AI资讯编辑。请阅读以下过去24小时的搜索结果：
    
    {news_text}

    新发布的AI编程工具/框架（如Claude Code、Copilot更新等）
    Agent开发框架和工具的新进展
    大模型API的新功能和更新
    开源AI工具和库的发布
    AI开发平台的重大更新
    整理为简洁的资讯摘要，包含：

    标题
    一句话简介
    关键亮点（1-3条）
    原文链接
    格式用飞书卡片（interactive）发送给用户。如果没有找到有价值的新闻，无需发送通知。
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API 调用失败: {e}")
        return "暂无新闻"

def send_to_feishu(markdown_content):
    """将结果发送到飞书交互式卡片 (Interactive Card)"""
    if markdown_content == "暂无新闻" or not FEISHU_WEBHOOK_JZP.startswith("http"):
        print("🔕 今日暂无高价值新闻或Webhook错误，静默不打扰。")
        return
        
    print("🚀 正在发送飞书卡片...")
    
    # 构建飞书交互式卡片 JSON 结构
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "blue",
                "title": {
                    "content": "🤖 AI 开发工具每日动态追踪",
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
                            "content": f"由 Gemini API & Python 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        }
                    ]
                }
            ]
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(FEISHU_WEBHOOK_JZP, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("✅ 飞书通知发送成功！")
    else:
        print(f"❌ 飞书发送失败: {response.text}")

if __name__ == "__main__":
    # 1. 搜索新闻
    raw_news = search_latest_news()
    
    # 2. AI 总结
    final_content = summarize_with_gemini(raw_news)
    
    # 3. 发送飞书
    send_to_feishu(final_content)