import os
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
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
FEISHU_WEBHOOK_JZP = config.get("Feishu_webhook_JZP", "https://open.feishu.cn/")
BASE_URL = config.get("url", "https://api.zetatechs.com").replace("https://", "").replace("http://", "")

genai.configure(
    api_key=GEMINI_API_KEY, 
    transport="rest",
    client_options={"api_endpoint": BASE_URL}
)
model = genai.GenerativeModel('gpt-5.4-free')

def fetch_latest_arxiv_papers():
    """从 arXiv 官方 API 获取最新包含 LLM 推理优化的论文"""
    print("🌍 正在通过 arXiv API 获取过去一周内的最新论文...")
    
    # 缩小检索词粒度同时加大抓取面，防止过长 query
    query = 'all:%22LLM%22+AND+all:%22inference%22'
    url = f'http://export.arxiv.org/api/query?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results=20'
    
    papers_data = []
    try:
        r = requests.get(url, timeout=15)
        root = ET.fromstring(r.text)
        
        # arXiv xml 命名空间兼容写法
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            title_node = entry.find('{http://www.w3.org/2005/Atom}title')
            summary_node = entry.find('{http://www.w3.org/2005/Atom}summary')
            published_node = entry.find('{http://www.w3.org/2005/Atom}published')
            link_node = entry.find('{http://www.w3.org/2005/Atom}id')
            
            if title_node is None or summary_node is None or published_node is None or link_node is None:
                continue
                
            title = title_node.text.replace('\n', ' ')
            summary = summary_node.text.replace('\n', ' ')
            published = published_node.text
            link = link_node.text
            
            # 提取作者
            authors = [a.find('{http://www.w3.org/2005/Atom}name').text for a in entry.findall('{http://www.w3.org/2005/Atom}author') if a.find('{http://www.w3.org/2005/Atom}name') is not None]
            author_str = ", ".join(authors)
            
            papers_data.append(f"Title: {title}\nAuthors: {author_str}\nPublished: {published}\nLink: {link}\nAbstract: {summary}\n")
            
        print(f"✅ 成功获取了 {len(papers_data)} 篇 arXiv 摘要！")
        if not papers_data:
            return ""
        return "\n---\n".join(papers_data)
    except Exception as e:
        print(f"arXiv 获取失败: {e}")
        return ""

def generate_paper_report(papers_text):
    """交由大模型精选顶级论文，并转换为精美阅读卡片"""
    if not papers_text:
        return "暂无相关论文"
        
    print("🧠 正在请 Gemini 以资深 AI 研究员的身份筛选并深度解读论文...")
    prompt = f"""
    你是全球顶尖的 AI 研究员（来自 OpenAI/Google 级别的团队）。
    请阅读以下从 arXiv 抓取的最新大语言模型 (LLM) 推理优化相关论文摘要：
    
    {papers_text}
    
    【执行任务】
    1. 请从中筛选出最多 3 篇最高质量、最具影响力的论文（优先选择解决核心痛点、有知名作者团队背书，或在推理效率、推理架构、KV Cache、投机解码等方向有重大突破的文章）。
    2. 为每篇被选中的论文撰写一份专业的速览导读。
    
    【Output Format】(Strictly output ONLY markdown, no other conversational words. Include emojis and clear typography).
    
    用极具技术深度的语言整理为精美的 Markdown 报告，每篇论文必须包含以下固定层次：
    
    ## 📄 [论文英文原标题]
    - 📌 **中文译名**：xxx
    - 👥 **作者团队**：xxx (如果看出团队背景请备注，如著名的大学或实验室)
    - 💡 **核心创新点**：xxx
    - 🔧 **方法概述**：xxx (用了什么算法/机制，如提出了新的 KV Cache 管理等)
    - 📊 **关键实验结果**：xxx (如推理速度提升 xx 倍，吞吐量提升 xx%)
    - 🔗 **论文地址**：[Link]
    
    (如有第 2、3 篇，请用 `---` 隔开并以此类推)
    
    要求：报告要极其专业、有技术深度，严禁错版乱码。如果上述列表中没有任何值得推荐的推理篇论文，请仅输出“今日暂无值得关注的推理优化论文”。
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

def send_papers_to_feishu(markdown_content):
    """发送到飞书"""
    if not markdown_content or "今日暂无" in markdown_content or not FEISHU_WEBHOOK_JZP.startswith("http"):
        print("🔕 没有高质量论文或 Webhook 错误，跳过发送。")
        return
        
    print("🚀 正在发送 LLM 推理优化论文飞书卡片...")
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "turquoise", # 蓝绿色，科研感十足
                "title": {
                    "content": "🔬 LLM 推理优化论文速递 | 每周二",
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
                            "content": f"由 Gemini API & arXiv 自动挖掘 | 聚焦推理、KV Cache、投机解码 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        }
                    ]
                }
            ]
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(FEISHU_WEBHOOK_JZP, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("✅ 飞书通知 (论文速递) 发送成功！")
    else:
        print(f"❌ 飞书发送失败: {response.text}")

if __name__ == "__main__":
    raw_papers = fetch_latest_arxiv_papers()
    final_card_content = generate_paper_report(raw_papers)
    send_papers_to_feishu(final_card_content)
