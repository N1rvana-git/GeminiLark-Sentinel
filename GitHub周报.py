import os
import requests
import google.generativeai as genai
from datetime import datetime
import re
from bs4 import BeautifulSoup

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
BASE_URL = config.get("url", "https://api.zetatechs.com").replace("https://", "").replace("http://", "")

genai.configure(
    api_key=GEMINI_API_KEY, 
    transport="rest",
    client_options={"api_endpoint": BASE_URL}
)
model = genai.GenerativeModel('gemini-3-flash-preview-free')

def scrape_github_trending(language):
    """抓取 GitHub Trending 指定语言的一周数据"""
    url = f"https://github.com/trending/{language}?since=weekly"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return ""
            
        soup = BeautifulSoup(r.text, 'html.parser')
        repos = []
        for article in soup.find_all('article', class_='Box-row'):
            name_tag = article.find('h2', class_='h3 lh-condensed')
            if not name_tag: continue
            
            repo_name = name_tag.text.strip().replace(' ', '').replace('\n', '')
            desc_tag = article.find('p', class_='col-9 color-fg-muted my-1 pr-4')
            desc = desc_tag.text.strip() if desc_tag else "No description"
            
            # 星星提取
            star_tag = article.find('span', class_='d-inline-block float-sm-right')
            stars = star_tag.text.strip() if star_tag else ""
            
            repos.append(f"Repo: {repo_name}\nDesc: {desc}\nWeekly Stars: {stars}")
            
        return "\n---\n".join(repos)
    except Exception as e:
        print(f"抓取 {language} Trending 失败: {e}")
        return ""

def process_github_trending():
    """统筹抓取 Python 和 Rust 的项目，并过滤带有 Agent/RAG 及其相关 AI 能力的信息发给模型"""
    print("🌍 正在从 GitHub Trending 收集过去一周的 Python 和 Rust 项目...")
    python_data = scrape_github_trending("python")
    rust_data = scrape_github_trending("rust")
    
    all_data = f"### Python Repos:\n{python_data}\n\n### Rust Repos:\n{rust_data}"
    
    if not python_data and not rust_data:
        return "无法获取 Trending 信息"
        
    print("🧠 正在请 Gemini 以资深 AI 全栈工程师的身份筛选与点评...")
    prompt = f"""
    你是资深AI全栈工程师。
    以下是我抓取到的 GitHub 上过去一周(weekly)的 Trending 仓库列表（包括 Python 和 Rust）：
    
    {all_data}
    
    【执行任务】：
    1. 请从上述列表中，筛选出核心与 'Agent' 或 'RAG' 强相关的 AI 项目。
    2. 根据它们获取的新增 Star 数（Weekly Stars），挑选出排名前三的项目。如果不足三个相关，则输出查找到的。
    3. 针对每个项目，用你资深的架构眼光，简明扼要地说明：
       - **解决什么问题**
       - **架构特色**
       - **技术亮点**
    4. 整理为精美、专业的飞书 Markdown 卡片格式排版输出。
    
    【Output Format】(Strictly output ONLY markdown, no other conversational words. Include emojis and clear typography).
    如果上面提供的数据里【没有任何】符合 Agent/RAG 相关的项目，请直接且仅输出：今日无相关项目
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        content = re.sub(r'^```[a-zA-Z]*\n', '', content)
        content = re.sub(r'\n```$', '', content)
        return content
    except Exception as e:
        print(f"Gemini API 调用失败: {e}")
        return ""

def send_trending_to_feishu(markdown_content):
    """将结果发送到飞书"""
    if not markdown_content or "今日无相关项目" in markdown_content or not FEISHU_WEBHOOK_JZP.startswith("http"):
        print("🔕 没找到相关高亮项目或 Webhook 错误，取消发送。")
        return
        
    print("🚀 正在发送 GitHub Trending 周报飞书卡片...")
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "wathet", # 浅蓝水蓝色，很极客
                "title": {
                    "content": "🏆 GitHub Trending | AI 全栈工程师周报 (每周一)",
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
                            "content": f"由 Gemini API & GitHub 强力驱动 | 聚焦 Agent & RAG 生态 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        }
                    ]
                }
            ]
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(FEISHU_WEBHOOK_JZP, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("✅ 飞书通知 (GitHub 周报) 发送成功！")
    else:
        print(f"❌ 飞书发送失败: {response.text}")


if __name__ == "__main__":
    final_card_content = process_github_trending()
    send_trending_to_feishu(final_card_content)
