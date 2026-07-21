import os, re
import google.generativeai as genai
import urllib.request
import json

def load_env_config():
    env_vars = {}
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            m = re.search(r'["\']?([^"\':]+?)["\']?\s*[:=]\s*["\']?(.+?)["\']?$', line.strip())
            if m:
                env_vars[m.group(1).strip()] = m.group(2).strip().rstrip(',')
    return env_vars

config = load_env_config()
BASE_URL = config.get('url', 'https://api.zetatechs.com')
KEY = config.get('key', '')

print(f"Testing OpenAI SDK directly via urllib to {BASE_URL}/v1/chat/completions")
req = urllib.request.Request(f"{BASE_URL}/v1/chat/completions", method="POST")
req.add_header("Authorization", f"Bearer {KEY}")
req.add_header("Content-Type", "application/json")
data = json.dumps({"model": "gpt-5.4-free", "messages": [{"role": "user", "content": "你好"}]}).encode('utf-8')

try:
    with urllib.request.urlopen(req, data=data) as response:
        res = json.loads(response.read().decode())
        print("Success! OpenAI API format works:", res['choices'][0]['message']['content'])
except Exception as e:
    print("OpenAI format failed:", e)

print("---")
print("Testing Gemini SDK with gpt-5.4-free")
try:
    genai.configure(api_key=KEY, transport="rest", client_options={"api_endpoint": BASE_URL.replace("https://", "").replace("http://", "")})
    model = genai.GenerativeModel('gpt-5.4-free')
    print('Testing Google SDK:', model.generate_content('你好').text)
except Exception as e:
    print('Google SDK failed:', e)