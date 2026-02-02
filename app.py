"""
TikTok Live Stream Analysis Bot - Fixed Version
修复事件类型和@用户名的解析问题
"""

import os
import sys
import json
import requests
import base64
import logging
import re
from flask import Flask, request, jsonify

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# 配置
FEISHU_APP_ID = os.environ.get('FEISHU_APP_ID', 'cli_a9f642df71f85cc2')
FEISHU_APP_SECRET = os.environ.get('FEISHU_APP_SECRET', 'qHOZbVFfLXn3z0h5eST4KdSgqpTsHJuy')

app = Flask(__name__)

@app.route('/')
def index():
    """主页"""
    logger.info("Homepage accessed")
    return 'TikTok直播分析机器人服务运行正常'

@app.route('/health')
def health():
    """健康检查"""
    logger.info("Health check")
    return jsonify({"status": "ok"})

@app.route('/api/feishu/webhook', methods=['GET', 'POST'])
def feishu_webhook():
    """飞书事件回调"""
    logger.info(f"Received request: method={request.method}, args={dict(request.args)}")
    
    # ==================== GET 请求：URL 验证 ====================
    if request.method == 'GET':
        challenge = request.args.get('challenge', '')
        logger.info(f"URL verification request, challenge={challenge}")
        
        if challenge:
            response = jsonify({"challenge": challenge})
            logger.info(f"Returning challenge: {response.get_data(as_text=True)}")
            return response
        else:
            logger.warning("GET request without challenge")
            return jsonify({"code": 0, "msg": "success"})
    
    # ==================== POST 请求：事件回调 ====================
    if request.method == 'POST':
        try:
            event_data = request.get_json()
            logger.info(f"Received event: {json.dumps(event_data, ensure_ascii=False)[:500]}")
            
            if event_data is None:
                logger.error("No JSON data in POST")
                return jsonify({"code": -1, "msg": "No data"})
            
            # URL 验证事件
            if event_data.get('type') == 'url_verification':
                challenge = event_data.get('challenge', '')
                logger.info(f"URL verification, challenge={challenge}")
                return jsonify({"challenge": challenge})
            
            # 获取事件类型
            event_type = event_data.get('header', {}).get('event_type', '')
            logger.info(f"Event type: {event_type}")
            
            # 消息接收事件 (im.message.receive_v1)
            if event_type == 'im.message.receive_v1':
                event = event_data.get('event', {})
                message = event.get('message', {})
                msg_type = message.get('msg_type')
                content = message.get('content')
                
                logger.info(f"Message: type={msg_type}, content={content}")
                
                # 处理文本消息
                if msg_type == 'text':
                    try:
                        # 解码base64内容
                        text_content = base64.b64decode(content).decode('utf-8')
                        logger.info(f"Raw text: {text_content}")
                        
                        # 去掉 @用户名 标记
                        text_content = re.sub(r'@_user_\d+\s*', '', text_content).strip()
                        logger.info(f"Cleaned text: {text_content}")
                        
                        # 解析数据
                        data = parse_live_data(text_content)
                        if data:
                            logger.info(f"Parsed data: {data}")
                            analysis = analyze_data(data)
                            card = create_analysis_card(data, analysis)
                            return send_card(card, event)
                        else:
                            logger.warning(f"Cannot parse data from: {text_content}")
                            return send_text("请发送格式: GMV=1000, 观众数=5000, 订单数=50", event)
                    except Exception as e:
                        logger.error(f"Error processing text: {e}")
                        return send_text(f"处理错误: {str(e)}", event)
                
                # 处理图片消息
                if msg_type == 'image':
                    logger.info("Image message received")
                    data = {'gmv': 1000, 'viewers': 5000, 'orders': 50}
                    analysis = analyze_data(data)
                    card = create_analysis_card(data, analysis)
                    return send_card(card, event)
            
            # 机器人被添加/移除事件
            if event_type in ['im.chat.member.bot.added_v1', 'im.chat.member.bot.deleted_v1']:
                logger.info(f"Bot {event_type.split('.')[-1]}")
                return jsonify({"code": 0, "msg": "success"})
            
            # 其他事件
            logger.info(f"Other event: {event_type}")
            return jsonify({"code": 0, "msg": "success"})
        
        except Exception as e:
            logger.error(f"Error processing POST: {e}")
            return jsonify({"code": -1, "msg": str(e)})
    
    logger.warning(f"Unsupported method: {request.method}")
    return jsonify({"code": -1, "msg": "Method not allowed"})

def parse_live_data(text):
    """解析直播数据"""
    data = {}
    
    # 匹配 GMV
    match = re.search(r'[Gg][Mm][Vv][=：:\s]*([\d.]+)', text)
    if match:
        data['gmv'] = float(match.group(1))
    
    # 匹配观众数
    match = re.search(r'观众[人数]?[=：:\s]*(\d+)', text)
    if match:
        data['viewers'] = int(match.group(1))
    
    # 匹配订单数
    match = re.search(r'订单[数量]?[=：:\s]*(\d+)', text)
    if match:
        data['orders'] = int(match.group(1))
    
    logger.info(f"Parsed data: {data}")
    
    if 'gmv' in data and 'viewers' in data and 'orders' in data:
        return data
    return None

def analyze_data(data):
    """分析直播数据"""
    gmv = data.get('gmv', 0)
    viewers = data.get('viewers', 0)
    orders = data.get('orders', 0)
    
    analysis = {'issues': [], 'insights': [], 'recommendations': []}
    
    # 转化率
    conversion_rate = (orders / viewers * 100) if viewers > 0 else 0
    
    if conversion_rate < 0.5:
        analysis['issues'].append({
            'title': '转化率严重偏低',
            'description': f'当前 {conversion_rate:.2f}%，需立即优化',
            'metric': f'转化率: {conversion_rate:.2f}%'
        })
    elif conversion_rate < 1.0:
        analysis['issues'].append({
            'title': '转化率有待提升',
            'description': f'当前 {conversion_rate:.2f}%，接近行业基准',
            'metric': f'转化率: {conversion_rate:.2f}%'
        })
    
    # 客单价
    if orders > 0:
        avg_order = gmv / orders
        analysis['insights'].append({
            'title': '客单价',
            'value': f'¥{avg_order:.2f}'
        })
    
    # 建议
    analysis['recommendations'] = [
        {'priority': 'urgent', 'title': '优化开场话术', 'description': '准备吸引人的开场和福利预告'},
        {'priority': 'medium', 'title': '提升互动频率', 'description': '每5-10分钟设置互动环节'},
        {'priority': 'longterm', 'title': '建立粉丝群', 'description': '培养忠实用户提升复购'},
    ]
    
    return analysis

def create_analysis_card(data, analysis):
    """创建分析卡片"""
    # 构建问题元素
    issues_elements = []
    for issue in analysis.get('issues', [])[:3]:
        emoji = '🔴' if '严重' in issue.get('title', '') else '🟠'
        issues_elements.extend([
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': f"{emoji} {issue.get('title', '')}"}},
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': f"📊 {issue.get('metric', '')}"}}
        ])
    
    if not issues_elements:
        issues_elements = [{'tag': 'div', 'text': {'tag': 'plain_text', 'content': '✅ 数据表现良好'}}]
    
    # 构建洞察元素
    insights_elements = []
    for insight in analysis.get('insights', [])[:2]:
        insights_elements.append({
            'tag': 'div', 
            'text': {'tag': 'plain_text', 'content': f"• {insight.get('title', '')}: {insight.get('value', '')}"}
        })
    
    # 构建建议元素
    rec_elements = []
    for rec in analysis.get('recommendations', [])[:3]:
        emoji = '🔴' if rec.get('priority') == 'urgent' else '🟡'
        rec_elements.extend([
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': f"{emoji} **{rec.get('title', '')}**"}},
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': f"   {rec.get('description', '')}"}}
        ])
    
    card = {
        'config': {'wide_screen_mode': True},
        'header': {
            'title': {'tag': 'plain_text', 'content': '📊 直播数据智能分析'},
            'template': 'blue'
        },
        'elements': [
            # 核心指标
            {
                'tag': 'column_set',
                'flex_mode': 'stretch',
                'columns': [
                    {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'plain_text', 'content': '💰 GMV'}}]},
                    {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'plain_text', 'content': '👥 观众'}}]},
                    {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'plain_text', 'content': '📦 订单'}}]},
                ]
            },
            {
                'tag': 'column_set',
                'flex_mode': 'stretch',
                'columns': [
                    {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'lark_md', 'content': f"**¥{data.get('gmv', 0):,.0f}**"}}]},
                    {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'lark_md', 'content': f"**{data.get('viewers', 0):,}**"}}]},
                    {'tag': 'column', 'width': 'weighted', 'weight': 1, 'elements': [{'tag': 'div', 'text': {'tag': 'lark_md', 'content': f"**{data.get('orders', 0):,}**"}}]},
                ]
            },
            {'tag': 'div', 'text': {'tag': 'separator'}},
            # 问题诊断
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': '🔍 问题诊断'}},
            *issues_elements,
            {'tag': 'div', 'text': {'tag': 'separator'}},
            # 数据洞察
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': '💡 数据洞察'}},
            *insights_elements,
            {'tag': 'div', 'text': {'tag': 'separator'}},
            # 优化建议
            {'tag': 'div', 'text': {'tag': 'plain_text', 'content': '🚀 优化建议'}},
            *rec_elements,
        ]
    }
    
    return card

def send_card(card, event):
    """发送卡片消息"""
    try:
        logger.info("Sending card message...")
        
        # 获取 token
        token_url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
        token_data = {'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET}
        
        token_response = requests.post(token_url, json=token_data, timeout=30)
        token_result = token_response.json()
        
        if token_result.get('code') != 0:
            logger.error(f"Token failed: {token_result}")
            return jsonify({'code': -1, 'msg': f'token失败: {token_result.get("msg")}'})
        
        token = token_result.get('tenant_access_token')
        logger.info("Token obtained")
        
        # 获取用户 ID
        receive_id = event.get('sender', {}).get('sender_id', {}).get('open_id')
        if not receive_id:
            receive_id = event.get('message', {}).get('sender', {}).get('open_id')
        
        if not receive_id:
            logger.error("Cannot get receive_id")
            return jsonify({'code': -1, 'msg': '无法获取用户ID'})
        
        logger.info(f"Sending to user: {receive_id}")
        
        # 发送消息
        msg_url = 'https://open.feishu.cn/open-apis/im/v1/messages'
        msg_params = {'receive_id_type': 'open_id'}
        msg_headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        msg_payload = {
            'receive_id': receive_id,
            'msg_type': 'interactive',
            'content': json.dumps({'card': card})
        }
        
        msg_response = requests.post(msg_url, params=msg_params, headers=msg_headers, json=msg_payload, timeout=30)
        result = msg_response.json()
        
        logger.info(f"Send result: {result}")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error sending card: {e}")
        return jsonify({'code': -1, 'msg': str(e)})

def send_text(text, event):
    """发送文本消息"""
    try:
        token_url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
        token_data = {'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET}
        
        token_response = requests.post(token_url, json=token_data, timeout=30)
        token_result = token_response.json()
        
        if token_result.get('code') != 0:
            return jsonify({'code': -1, 'msg': 'token失败'})
        
        token = token_result.get('tenant_access_token')
        receive_id = event.get('sender', {}).get('sender_id', {}).get('open_id')
        
        msg_url = 'https://open.feishu.cn/open-apis/im/v1/messages'
        msg_params = {'receive_id_type': 'open_id'}
        msg_headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        msg_payload = {
            'receive_id': receive_id,
            'msg_type': 'text',
            'content': json.dumps({'text': text})
        }
        
        msg_response = requests.post(msg_url, params=msg_params, headers=msg_headers, json=msg_payload, timeout=30)
        return jsonify(msg_response.json())
    
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port)
