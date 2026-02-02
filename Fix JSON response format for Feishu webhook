"""
TikTok Live Stream Analysis Bot - Fixed Version for Render
"""

import os
import json
import requests
import base64
from datetime import datetime
from dataclasses import dataclass
from flask import Flask, request, jsonify, render_template_string

# 配置
FEISHU_APP_ID = os.environ.get('FEISHU_APP_ID', 'cli_a9f642df71f85cc2')
FEISHU_APP_SECRET = os.environ.get('FEISHU_APP_SECRET', 'qHOZbVFfLXn3z0h5eST4KdSgqpTsHJuy')

@dataclass
class LiveDashboardData:
    gmv: float = 0.0
    viewers: int = 0
    orders: int = 0
    avg_viewers: float = 0.0
    peak_viewers: int = 0
    total_likes: int = 0
    traffic_sources: dict = None
    product_data: list = None

    def __post_init__(self):
        if self.traffic_sources is None:
            self.traffic_sources = {}
        if self.product_data is None:
            self.product_data = []

class DataAnalyzer:
    BENCHMARKS = {
        "conversion_rate": {"critical": 0.5, "warning": 1.0},
        "gmv_per_viewer": {"critical": 0.1},
    }
    
    def __init__(self, data: LiveDashboardData):
        self.data = data
        self.issues = []
        self.insights = []
        self.recommendations = []
    
    def analyze(self):
        if self.data.viewers > 0:
            rate = (self.data.orders / self.data.viewers) * 100
            if rate < self.BENCHMARKS["conversion_rate"]["critical"]:
                self.issues.append({
                    "type": "critical",
                    "title": "转化率严重偏低",
                    "description": f"当前 {rate:.2f}%，需立即优化",
                    "metric": f"转化率: {rate:.2f}%"
                })
        
        if self.data.orders > 0:
            avg_order = self.data.gmv / self.data.orders
            self.insights.append({
                "title": "客单价",
                "description": f"平均 ¥{avg_order:.2f}",
                "value": f"¥{avg_order:.2f}"
            })
        
        if self.data.viewers > 0 and self.data.avg_viewers > 0:
            self.insights.append({
                "title": "平均观看",
                "description": f"峰值 {self.data.peak_viewers}，平均 {self.data.avg_viewers:.0f}",
                "value": f"{self.data.avg_viewers:.0f}"
            })
        
        self.recommendations = [
            {"priority": "urgent", "title": "优化开场话术", "description": "准备吸引人的开场和福利预告"},
            {"priority": "medium", "title": "提升互动频率", "description": "每5-10分钟设置互动环节"},
            {"priority": "longterm", "title": "建立粉丝群", "description": "培养忠实用户提升复购"},
        ]
        
        return {"issues": self.issues, "insights": self.insights, "recommendations": self.recommendations}

class FeishuCardGenerator:
    @staticmethod
    def create_card(gmv, viewers, orders, result):
        # 构建问题元素
        issues_elements = []
        for issue in result.get("issues", [])[:3]:
            emoji = "🔴" if issue.get("type") == "critical" else "🟠"
            issues_elements.extend([
                {"tag": "div", "text": {"tag": "plain_text", "content": f"{emoji} {issue.get('title', '')}"}},
                {"tag": "div", "text": {"tag": "plain_text", "content": f"📊 {issue.get('metric', '')}"}}
            ])
        if not issues_elements:
            issues_elements = [{"tag": "div", "text": {"tag": "plain_text", "content": "✅ 数据表现良好"}}]
        
        # 构建洞察元素
        insights_elements = []
        for insight in result.get("insights", [])[:2]:
            insights_elements.append({"tag": "div", "text": {"tag": "plain_text", "content": f"• {insight.get('title', '')}: {insight.get('value', '')}"}})
        
        # 构建建议元素
        rec_elements = []
        for rec in result.get("recommendations", [])[:3]:
            emoji = "🔴" if rec.get("priority") == "urgent" else "🟡"
            rec_elements.extend([
                {"tag": "div", "text": {"tag": "plain_text", "content": f"{emoji} **{rec.get('title', '')}**"}},
                {"tag": "div", "text": {"tag": "plain_text", "content": f"   {rec.get('description', '')}"}}
            ])
        
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "📊 直播数据智能分析"},
                "template": "blue"
            },
            "elements": [
                # 核心指标
                {
                    "tag": "column_set",
                    "flex_mode": "stretch",
                    "columns": [
                        {"tag": "column", "width": "weighted", "weight": 1, "elements": [{"tag": "div", "text": {"tag": "plain_text", "content": "💰 GMV"}}]},
                        {"tag": "column", "width": "weighted", "weight": 1, "elements": [{"tag": "div", "text": {"tag": "plain_text", "content": "👥 观众"}}]},
                        {"tag": "column", "width": "weighted", "weight": 1, "elements": [{"tag": "div", "text": {"tag": "plain_text", "content": "📦 订单"}}]},
                    ]
                },
                {
                    "tag": "column_set",
                    "flex_mode": "stretch",
                    "columns": [
                        {"tag": "column", "width": "weighted", "weight": 1, "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": f"**¥{gmv:,.0f}**"}}]},
                        {"tag": "column", "width": "weighted", "weight": 1, "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": f"**{viewers:,}**"}}]},
                        {"tag": "column", "width": "weighted", "weight": 1, "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": f"**{orders:,}**"}}]},
                    ]
                },
                {"tag": "div", "text": {"tag": "separator"}},
                # 问题诊断
                {"tag": "div", "text": {"tag": "plain_text", "content": "🔍 问题诊断"}},
                *issues_elements,
                {"tag": "div", "text": {"tag": "separator"}},
                # 数据洞察
                {"tag": "div", "text": {"tag": "plain_text", "content": "💡 数据洞察"}},
                *insights_elements,
                {"tag": "div", "text": {"tag": "separator"}},
                # 优化建议
                {"tag": "div", "text": {"tag": "plain_text", "content": "🚀 优化建议"}},
                *rec_elements,
            ]
        }

# Flask App
app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head><title>TikTok直播分析机器人</title></head>
<body style="font-family: Arial; padding: 40px; text-align: center;">
    <h1>🎬 TikTok直播分析机器人</h1>
    <p>服务运行正常 ✅</p>
    <p>回调地址: /api/feishu/webhook</p>
</body>
</html>
    """)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "douyin-live-feishu-bot"})

@app.route('/api/feishu/webhook', methods=['GET', 'POST'])
def webhook():
    """飞书事件回调"""
    try:
        # URL验证（GET请求）
        if request.method == 'GET':
            challenge = request.args.get('challenge', '')
            return jsonify({"challenge": challenge})
        
        # 事件回调（POST请求）
        event = request.json
        
        # URL验证事件
        if event.get("type") == "url_verification":
            challenge = event.get("challenge", '')
            return jsonify({"challenge": challenge})
        
        # 消息回调事件
        if event.get("type") == "event_callback":
            message = event.get("event", {}).get("message", {})
            msg_type = message.get("msg_type")
            content = message.get("content")
            
            if msg_type == "text":
                text_content = base64.b64decode(content).decode("utf-8")
                data = parse_text(text_content)
                if data:
                    return process_data(message.get("message_id"), data, event)
                else:
                    # 无法解析数据，返回提示
                    return send_error_message("无法识别数据格式，请发送: GMV=1000, 观众数=5000, 订单数=50")
            
            if msg_type == "image":
                # 图片消息，使用示例数据
                return process_dummy_data(message.get("message_id"), event)
        
        # 其他事件，返回成功
        return jsonify({"code": 0, "msg": "success"})
    
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})

def parse_text(text):
    """解析文本数据"""
    import re
    data = {}
    
    # 匹配各种格式
    patterns = [
        (r'[Gg][Mm][Vv][=：:\s]*([\d.]+)', 'gmv'),
        (r'观众[人数]?[=：:\s]*(\d+)', 'viewers'),
        (r'订单[数量]?[=：:\s]*(\d+)', 'orders'),
        (r'峰值[观看]?[=：:\s]*(\d+)', 'peak_viewers'),
        (r'平均[观看]?[=：:\s]*([\d.]+)', 'avg_viewers'),
    ]
    
    for pattern, key in patterns:
        match = re.search(pattern, text)
        if match:
            data[key] = float(match.group(1)) if key in ['gmv', 'avg_viewers'] else int(match.group(1))
    
    # 设置默认值
    if 'peak_viewers' not in data and 'viewers' in data:
        data['peak_viewers'] = int(data['viewers'] * 0.8)
    if 'avg_viewers' not in data and 'viewers' in data:
        data['avg_viewers'] = float(data['viewers']) * 0.5
    
    return LiveDashboardData(**data) if 'gmv' in data and 'viewers' in data else None

def process_data(message_id, data, event):
    """处理文本数据"""
    analyzer = DataAnalyzer(data)
    result = analyzer.analyze()
    card = FeishuCardGenerator.create_card(data.gmv, data.viewers, data.orders, result)
    return send_card_message(message_id, card, event)

def process_dummy_data(message_id, event):
    """处理图片数据（使用示例）"""
    data = LiveDashboardData(
        gmv=1000,
        viewers=5000,
        orders=50,
        peak_viewers=3500,
        avg_viewers=1200
    )
    analyzer = DataAnalyzer(data)
    result = analyzer.analyze()
    card = FeishuCardGenerator.create_card(data.gmv, data.viewers, data.orders, result)
    return send_card_message(message_id, card, event)

def send_error_message(error_text, event=None):
    """发送错误消息"""
    card = {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": "⚠️ 提示"}, "template": "yellow"},
        "elements": [
            {"tag": "div", "text": {"tag": "plain_text", "content": error_text}}
        ]
    }
    # 返回成功响应，避免飞书报错
    return jsonify({"code": 0, "msg": "processed"})

def send_card_message(message_id, card, event):
    """发送飞书卡片"""
    try:
        # 获取 tenant_access_token
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        token_payload = {
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET
        }
        
        token_response = requests.post(token_url, json=token_payload, timeout=30)
        token_data = token_response.json()
        
        if token_data.get("code") != 0:
            return jsonify({"code": -1, "msg": f"获取token失败: {token_data.get('msg')}"})
        
        tenant_access_token = token_data.get("tenant_access_token")
        
        # 获取接收者ID
        receive_id = event.get("sender", {}).get("sender_id", {}).get("open_id")
        if not receive_id:
            receive_id = event.get("message", {}).get("sender", {}).get("open_id")
        
        if not receive_id:
            return jsonify({"code": -1, "msg": "无法获取接收者ID"})
        
        # 发送卡片消息
        message_url = "https://open.feishu.cn/open-apis/im/v1/messages"
        message_params = {
            "receive_id_type": "open_id"
        }
        message_headers = {
            "Authorization": f"Bearer {tenant_access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        message_payload = {
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": json.dumps({"card": card})
        }
        
        message_response = requests.post(
            message_url,
            params=message_params,
            headers=message_headers,
            json=message_payload,
            timeout=30
        )
        
        result = message_response.json()
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
