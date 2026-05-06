from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# 从环境变量读取配置（部署时在Render后台填）
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
HERMES_API_URL = os.environ.get("HERMES_API_URL", "http://localhost:8000/api/chat")

def get_feishu_token():
    """获取飞书API访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    resp = requests.post(url, json=data)
    return resp.json()["tenant_access_token"]

@app.route("/webhook", methods=["POST"])
def feishu_webhook():
    """接收飞书消息，转发给Hermes Agent，再把回复发回飞书"""
    data = request.json
    # 处理飞书消息回调
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    
    event = data.get("event", {})
    message = event.get("message", {})
    text = message.get("content", "").strip()
    open_id = event.get("sender", {}).get("sender_id", {}).get("open_id")
    
    if not text or not open_id:
        return "ok"
    
    # 调用Hermes Agent获取回复
    hermes_resp = requests.post(HERMES_API_URL, json={"prompt": text})
    reply_text = hermes_resp.json().get("response", "抱歉，我现在无法回答你")
    
    # 回复飞书用户
    token = get_feishu_token()
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {"Authorization": f"Bearer {token}"}
    msg_data = {
        "receive_id": open_id,
        "msg_type": "text",
        "content": f'{{"text": "{reply_text}"}}'
    }
    requests.post(url, headers=headers, json=msg_data)
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "Hermes-Feishu Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
