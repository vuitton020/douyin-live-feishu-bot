# -*- coding: utf-8 -*-
"""
Glitch版本 - 飞书机器人Web服务
Feishu Bot Web Service for Glitch

作者: Matrix Agent
"""

import os
import sys
import json
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 尝试导入Flask，如果不存在则安装
try:
    from flask import Flask, request, jsonify
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "flask", "-q"])
    from flask import Flask, request, jsonify

# 创建Flask应用
app = Flask(__name__)


def get_env_or_secret(key: str, default: str = None) -> str:
    """获取环境变量"""
    value = os.environ.get(key)
    if value:
        return value
    return default


def handle_feishu_event(event: dict) -> dict:
    """
    处理飞书事件
    
    Args:
        event: 飞书事件数据
        
    Returns:
        dict: 处理结果
    """
    try:
        event_type = event.get("type")
        
        if event_type == "url_verification":
            return {"challenge": event.get("challenge", "")}
        
        elif event_type == "event_callback":
            return process_event(event.get("event", {}))
        
        return {"success": True}
        
    except Exception as e:
        logger.exception(f"Error handling event: {e}")
        return {"error": str(e)}


def process_event(event_data: dict) -> dict:
    """处理事件"""
    try:
        event_type = event_data.get("type")
        
        if event_type == "message":
            return handle_message(event_data)
        
        return {"success": True}
        
    except Exception as e:
        logger.exception(f"Error processing event: {e}")
        return {"error": str(e)}


def handle_message(event_data: dict) -> dict:
    """处理消息"""
    try:
        message_type = event_data.get("message_type")
        content = event_data.get("content", {})
        
        logger.info(f"Received message type: {message_type}")
        
        # 获取配置
        app_id = get_env_or_secret("FEISHU_APP_ID")
        app_secret = get_env_or_secret("FEISHU_APP_SECRET")
        
        if not app_id or not app_secret:
            return {"error": "Missing FEISHU_APP_ID or FEISHU_APP_SECRET"}
        
        # 处理图片消息
        if message_type == "image":
            return handle_image_message(event_data, content, app_id, app_secret)
        
        # 处理文本消息
        elif message_type == "text":
            return handle_text_message(event_data, content, app_id, app_secret)
        
        return {"success": True, "message": "Message type not supported"}
        
    except Exception as e:
        logger.exception(f"Error handling message: {e}")
        return {"error": str(e)}


def handle_image_message(event_data: dict, content: dict, app_id: str, app_secret: str) -> dict:
    """处理图片消息"""
    try:
        image_key = content.get("image_key", "")
        
        if not image_key:
            return {"success": False, "message": "No image key found"}
        
        logger.info(f"Processing image: {image_key}")
        
        # 导入分析模块
        from modules.image_analysis import ImageAnalyzer, LiveDashboardData
        from modules.data_analysis import DataAnalyzer
        from modules.feishu_card import create_dashboard_card, build_card_message
        
        # 初始化分析器
        image_analyzer = ImageAnalyzer()
        data_analyzer = DataAnalyzer()
        
        # 获取图片URL
        image_url = get_image_url(image_key, app_id, app_secret)
        
        if not image_url:
            return {"success": False, "message": "Failed to get image URL"}
        
        # 分析图片
        dashboard_data = image_analyzer.analyze(image_url)
        
        # 分析数据
        report = data_analyzer.analyze(dashboard_data)
        
        # 生成卡片
        card = create_dashboard_card(report)
        card_message = build_card_message(card)
        
        # 发送卡片消息
        receive_id = event_data.get("sender", {}).get("sender_id", {}).get("open_id")
        
        if receive_id:
            try:
                send_message(receive_id, card_message, app_id, app_secret)
            except Exception as e:
                logger.warning(f"Failed to send message: {e}")
        
        return {"success": True}
        
    except Exception as e:
        logger.exception(f"Error processing image: {e}")
        return {"error": str(e)}


def handle_text_message(event_data: dict, content: dict, app_id: str, app_secret: str) -> dict:
    """处理文本消息"""
    try:
        text = content.get("text", "").strip()
        
        # 欢迎消息
        welcome_keywords = ["你好", "hello", "hi", "帮助", "使用说明"]
        if any(kw in text.lower() for kw in welcome_keywords):
            from modules.feishu_card import FeishuCard, build_card_message
            
            card = FeishuCard()
            card.set_header("🎉 欢迎使用抖音直播数据分析师", "智能数据分析助手")
            card.add_div("📋 **使用说明**")
            card.add_div("1. 发送抖音直播大屏截图")
            card.add_div("2. 我会自动分析数据并生成报告")
            card.add_div("3. 提供专业的运营优化建议")
            card.add_div("")
            card.add_div("💡 **温馨提示**:")
            card.add_div("• 截图越清晰，数据分析越准确")
            card.add_div("• 建议在直播结束后进行分析")
            
            card_message = build_card_message(card)
            
# 发送卡片
            receive_id = event_data.get("sender", {}).get("sender_id", {}).get("open_id")
            
            if receive_id:
                try:
                    send_message(receive_id, card_message, app_id, app_secret)
                except Exception as e:
                    logger.warning(f"Failed to send message: {e}")
            
            return {"success": True}
        
        return {"success": True, "message": "Text received"}
        
    except Exception as e:
        logger.exception(f"Error handling text: {e}")
        return {"error": str(e)}


def get_image_url(image_key: str, app_id: str, app_secret: str) -> str:
    """获取图片URL"""
    try:
        import requests
        
        # 获取access token
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": app_id, "app_secret": app_secret}
        
        response = requests.post(token_url, json=payload, timeout=10)
        result = response.json()
        
        if result.get("code") != 0:
            return ""
        
        token = result.get("tenant_access_token")
        
        # 获取图片URL
        headers = {"Authorization": f"Bearer {token}"}
        img_url = f"https://open.feishu.cn/open-apis/im/v1/images/{image_key}"
        
        response = requests.get(img_url, headers=headers, timeout=10)
        result = response.json()
        
        if result.get("code") == 0:
            return result.get("data", {}).get("image_url")
        
        return ""
        
    except Exception as e:
        logger.error(f"Error getting image URL: {e}")
        return ""


def send_message(receive_id: str, card_message: dict, app_id: str, app_secret: str) -> bool:
    """发送卡片消息"""
    try:
        import requests
        
        # 获取access token
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": app_id, "app_secret": app_secret}
        
        response = requests.post(token_url, json=payload, timeout=10)
        result = response.json()
        
        if result.get("code") != 0:
            return False
        
        token = result.get("tenant_access_token")
        
        # 发送消息
        msg_url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "receive_id": receive_id,
            "msg_type": "interactive",
            "card": card_message["card"]
        }
        
        response = requests.post(msg_url, headers=headers, json=payload, timeout=10)
        
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False


# ============ API路由 ============\n\n@app.route("/", methods=["GET", "POST"])
def index():
    """首页"""
    return """
    <h1>🚀 抖音直播大屏分析飞书机器人</h1>
    <p>状态: 运行中 ✅</p>
    <p>时间: """ + json.dumps({"status": "running", "message": "Bot is active"}) + """</p>
    """


@app.route("/api", methods=["GET", "POST"])
def api():
    """API入口"""
    try:
        # 处理GET请求（URL验证）
        if request.method == "GET":
            challenge = request.args.get("challenge", "")
            return jsonify({"challenge": challenge})
        
        # 处理POST请求
        if request.is_json:
            body = request.get_json()
            
            # URL验证
            if "challenge" in body:
                return jsonify({"challenge": body["challenge"]})
            
            # 处理事件回调
            if body.get("type") == "event_callback":
                result = process_event(body.get("event", {}))
                return jsonify(result)
            
            return jsonify({"success": True})
        
        return jsonify({"error": "Invalid request"}), 400
        
    except Exception as e:
        logger.exception(f"Error in api: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "healthy", "service": "douyin-live-bot"})


# ============ 启动应用 ============

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting bot on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)

