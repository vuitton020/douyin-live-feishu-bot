"""
TikTok Live Stream Analysis Bot - 修复飞书新版本事件格式
"""

import os
import json
import requests
import base64
import re
from flask import Flask, request, jsonify

FEISHU_APP_ID = os.environ.get('FEISHU_APP_ID', 'cli_a9f642df71f85cc2')
FEISHU_APP_SECRET = os.environ.get('FEISHU_APP_SECRET', 'qHOZbVFfLXn3z0h5eST4KdSgqpTsHJuy')

app = Flask(__name__)

print("TikTok直播分析机器人启动")
print(f"FEISHU_APP_ID: {FEISHU_APP_ID[:10]}...")
print(f"PORT: {os.environ.get('PORT', '10000')}")

@app.route('/')
def index():
    return 'TikTok直播分析机器人服务运行正常'

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/feishu/webhook', methods=['GET', 'POST'])
def feishu_webhook():
    print(f"\n收到请求: {request.method}")
    
    # GET - URL验证
    if request.method == 'GET':
        challenge = request.args.get('challenge', '')
        print(f"GET Challenge: {challenge}")
        return jsonify({"challenge": challenge})
    
    # POST - 事件回调
    try:
        event = request.get_json(silent=True) or {}
        print(f"Event type: {event.get('header', {}).get('event_type', 'unknown')}")
        
        event_type = event.get('header', {}).get('event_type', '')
        
        # URL验证事件
        if event_type == 'url_verification':
            challenge = event.get('challenge', '')
            print(f"URL Verification: {challenge}")
            return jsonify({"challenge": challenge})
        
        # 消息回调事件 (兼容新旧版本)
        if event_type in ['im.message.receive_v1', 'im:message']:
            message = event.get('event', {}).get('message', {})
            
            # 解析content
            content_str = message.get('content', '{}')
            print(f"Content raw: {content_str[:100]}...")
            
            try:
                # content可能是JSON字符串
                content = json.loads(content_str) if content_str.startswith('{') else {}
            except:
                content = {}
            
            # 获取文本内容
            text_content = content.get('text', '')
            if not text_content:
                # 尝试从原始content提取
                text_content = content_str
            
            print(f"Text content: {text_content}")
            
            if text_content:
                return handle_text_message(message, text_content, event)
            else:
                # 图片或其他类型
                return jsonify({"code": 0, "msg": "消息已收到"})
        
        return jsonify({"code": 0, "msg": "事件已处理"})
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"code": -1, "msg": str(e)})

def handle_text_message(message, text_content, event):
    print(f"处理文本消息: {text_content}")
    
    # 清理文本（移除@提及等）
    text_content = re.sub(r'@_user_\d+\s*', '', text_content)
    text_content = text_content.strip()
    
    data = parse_live_data(text_content)
    print(f"解析结果: {data}")
    
    if data:
        analysis = analyze_data(data)
        card = create_analysis_card(data, analysis)
        return send_card(card, event)
    else:
        return send_text("请发送格式: GMV=数值, 观众数=数值, 订单数=数值", event)

def parse_live_data(text):
    data = {}
    
    match = re.search(r'[Gg][Mm][Vv][=：:\s]*([\d.]+)', text)
    if match:
        data['gmv'] = float(match.group(1))
    
    match = re.search(r'观众[人数]?[=：:\s]*(\d+)', text)
    if match:
        data['viewers'] = int(match.group(1))
    
    match = re.search(r'订单[数量]?[=：:\s]*(\d+)', text)
    if match:
        data['orders'] = int(match.group(1))
    
    return data if 'gmv' in data and 'viewers' in data and 'orders' in data else None

def analyze_data(data):
    gmv, viewers, orders = data.get('gmv', 0), data.get('viewers', 0), data.get('orders', 0)
    rate = (orders / viewers * 100) if viewers > 0 else 0
    
    analysis = {'issues': [], 'insights': [], 'recommendations': []}
    
    if rate < 0.5:
        analysis['issues'].append({'title': '转化率严重偏低', 'description': f'当前 {rate:.2f}%', 'metric': f'转化率: {rate:.2f}%'})
    elif rate < 1.0:
        analysis['issues'].append({'title': '转化率有待提升', 'description': f'当前 {rate:.2f}%', 'metric': f'转化率: {rate:.2f}%'})
    
    if orders > 0:
        analysis['insights'].append({'title': '客单价', 'value': f'¥{gmv/orders:.2f}'})
    
    analysis['recommendations'] = [
        {'priority': 'urgent', 'title': '优化开场话术', 'description': '准备吸引人的开场和福利预告'},
        {'priority': 'medium', 'title': '提升互动频率', 'description': '每5-10分钟设置互动环节'},
        {'priority': 'longterm', 'title': '建立粉丝群', 'description': '培养忠实用户提升复购'},
    ]
    return analysis

def create_analysis_card(data, analysis):
    issues = []
    for issue in analysis.get('issues', [])[:3]:
        emoji = '🔴' if '严重' in issue.get('title', '') else '🟠'
        issues.extend([
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': f"{emoji} {issue.get('title', '')}"}},
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': f"📊 {issue.get('metric', '')}"}}
        ])
    if not issues:
        issues = [{'tag': 'div', 'text': {'tag': 'plain_text', 'content': '✅ 数据表现良好'}}]
    
    insights = [{'tag': 'div', 'text': {'tag': 'plain_text', 'content': f"• {i.get('title', '')}: {i.get('value', '')}"}} for i in analysis.get('insights', [])[:2]]
    
    recs = []
    for rec in analysis.get('recommendations', [])[:3]:
        emoji = '🔴' if rec.get('priority') == 'urgent' else '🟡'
        recs.extend([
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': f"{emoji} **{rec.get('title', '')}**"}},
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': f"   {rec.get('description', '')}"}}
        ])
    
    return {
        'config': {'wide_screen_mode': True},
        'header': {'title': {'tag': 'plain_text', 'content': '📊 直播数据智能分析'}, 'template': 'blue'},
        'elements': [
            {'tag': 'column_set', 'flex_mode': 'stretch', 'columns': [
                {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'plain_text', 'content': '💰 GMV'}}]},
                {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'plain_text', 'content': '👥 观众'}}]},
                {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'plain_text', 'content': '📦 订单'}}]},
            ]},
            {'tag': 'column_set', 'flex_mode': 'stretch', 'columns': [
                {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'lark_md', 'content': f"**¥{data.get('gmv', 0):,.0f}**"}}]},
                {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'lark_md', 'content': f"**{data.get('viewers', 0):,}**"}}]},
                {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'lark_md', 'content': f"**{data.get('orders', 0):,}**"}}]},
            ]},
            {'tag': 'div', 'text': {'tag': 'separator'}},
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': '🔍 问题诊断'}},
            *issues,
            {'tag': 'div', 'text': {'tag': 'separator'}},
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': '💡 数据洞察'}},
            *insights,
            {'tag': 'div', 'text': {'tag': 'separator'}},
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': '🚀 优化建议'}},
*recs,
        ]
    }

def send_card(card, event):
    try:
        token_resp = requests.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
            json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET}, timeout=30)
        token_data = token_resp.json()
        if token_data.get('code') != 0:
            print(f"Token failed: {token_data.get('msg')}")
            return jsonify({'code': -1, 'msg': f'token失败: {token_data.get("msg")}'})
        
        token = token_data.get('tenant_access_token')
        receive_id = event.get('event', {}).get('sender', {}).get('sender_id', {}).get('open_id')
        if not receive_id:
            receive_id = event.get('event', {}).get('message', {}).get('sender', {}).get('open_id')
        
        if not receive_id:
            print("无法获取用户ID")
            return jsonify({'code': -1, 'msg': '无法获取用户ID'})
        
        print(f"发送消息给用户: {receive_id}")
        
        msg_resp = requests.post('https://open.feishu.cn/open-apis/im/v1/messages',
            params={'receive_id_type': 'open_id'},
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json; charset=utf-8'},
            json={'receive_id': receive_id, 'msg_type': 'interactive', 'content': json.dumps({'card': card})},
            timeout=30)
        
        print(f"发送结果: {msg_resp.status_code}")
        result = msg_resp.json()
        print(f"发送详情: {json.dumps(result, ensure_ascii=False)[:200]}")
        return jsonify(result)
    except Exception as e:
        print(f"发送失败: {e}")
        return jsonify({'code': -1, 'msg': str(e)})

def send_text(text, event):
    try:
        token_resp = requests.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
            json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET}, timeout=30)
        token = token_resp.json().get('tenant_access_token')
        receive_id = event.get('event', {}).get('sender', {}).get('sender_id', {}).get('open_id')
        
        msg_resp = requests.post('https://open.feishu.cn/open-apis/im/v1/messages',
            params={'receive_id_type': 'open_id'},
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'receive_id': receive_id, 'msg_type': 'text', 'content': json.dumps({'text': text})},
            timeout=30)
        return jsonify(msg_resp.json())
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
