#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音直播数据飞书机器人 - 修复版
支持飞书机器人接收直播数据并自动生成分析报告
"""

import os
import json
import re
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from concurrent.futures import ThreadPoolExecutor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 飞书应用配置
FEISHU_APP_ID = os.environ.get('FEISHU_APP_ID', 'cli_a9f642df71f85cc2')
FEISHU_APP_SECRET = os.environ.get('FEISHU_APP_SECRET', 'qHOZbVFfLXn3z0h5eST4KdSgqpTsHJuy')

# 缓存access_token
access_token_cache = {'token': None, 'expire_time': None}
token_executor = ThreadPoolExecutor(max_workers=1)

def get_tenant_access_token():
    """获取飞书应用访问令牌"""
    global access_token_cache
    
    # 检查缓存是否有效
    if (access_token_cache['token'] and 
        access_token_cache['expire_time'] and 
        datetime.now() < access_token_cache['expire_time']):
        return access_token_cache['token']
    
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET
        }
        
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        if data.get('code') == 0:
            access_token_cache['token'] = data.get('tenant_access_token')
            # 提前5分钟刷新
            access_token_cache['expire_time'] = datetime.now() + timedelta(minutes=115)
            return access_token_cache['token']
        else:
            logger.error(f"获取access_token失败: {data}")
            return None
    except Exception as e:
        logger.error(f"获取access_token异常: {e}")
        return None

def send_feishu_message(receive_id, msg_type, content):
    """发送飞书消息"""
    try:
        token = get_tenant_access_token()
        if not token:
            return False, "获取访问令牌失败"
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        params = {"receive_id_type": "open_id"}
        
        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": json.dumps(content)
        }
        
        response = requests.post(url, headers=headers, params=params, json=payload)
        data = response.json()
        
        if data.get('code') == 0:
            return True, "发送成功"
        else:
            logger.error(f"发送消息失败: {data}")
            return False, str(data)
    except Exception as e:
        logger.error(f"发送消息异常: {e}")
        return False, str(e)

def parse_live_stream_data(text):
    """解析直播数据"""
    data = {}
    
    # 提取GMV
    gmv_match = re.search(r'[Gg][Mm][Vv][=：:\s]*([\d.]+)', text)
    if gmv_match:
        data['gmv'] = float(gmv_match.group(1))
    
    # 提取观众数
    viewer_match = re.search(r'观众[数]?[=：:\s]*([\d,]+)', text)
    if not viewer_match:
        viewer_match = re.search(r'[Vv]iewers?[=：:\s]*([\d,]+)', text)
    if not viewer_match:
        viewer_match = re.search(r'观看[人]?[=：:\s]*([\d,]+)', text)
    if viewer_match:
        data['viewers'] = int(viewer_match.group(1).replace(',', ''))
    
    # 提取订单数
    order_match = re.search(r'订单[数]?[=：:\s]*([\d,]+)', text)
    if not order_match:
        order_match = re.search(r'[Oo]rders?[=：:\s]*([\d,]+)', text)
    if order_match:
        data['orders'] = int(order_match.group(1).replace(',', ''))
    
    return data

def analyze_live_stream(data):
    """分析直播数据"""
    if not data:
        return None
    
    gmv = data.get('gmv', 0)
    viewers = data.get('viewers', 1)
    orders = data.get('orders', 0)
    
    # 基础指标
    gpv = gmv / viewers if viewers > 0 else 0  # 每观众贡献
    conversion = orders / viewers if viewers > 0 else 0  # 转化率
    aov = gmv / orders if orders > 0 else 0  # 平均客单价
    gpm = (gmv / 1000) * 100 if viewers > 0 else 0  # 千次曝光GMV
    
    # 质量评分 (0-100)
    score = 0
    score += min(gpv * 50, 25)  # 每观众贡献 (最多25分)
    score += min(conversion * 500, 25)  # 转化率 (最多25分)
    score += min(aov / 10, 25)  # 客单价 (最多25分)
    score += min(gpm / 5, 25)  # 千次曝光GMV (最多25分)
    score = min(score, 100)
    
    # 评级
    if score >= 80:
        rating = "S"
    elif score >= 60:
        rating = "A"
    elif score >= 40:
        rating = "B"
    else:
        rating = "C"
    
    return {
        'gmv': gmv,
        'viewers': viewers,
        'orders': orders,
        'gpv': round(gpv, 2),
        'conversion_rate': f"{conversion*100:.2f}%",
        'aov': round(aov, 2),
        'score': int(score),
        'rating': rating
    }

def generate_analysis_card(data):
    """生成飞书交互卡片"""
    analysis = analyze_live_stream(data)
    
    if not analysis:
        return {
            "config": {"wide_screen_mode": True},
            "elements": [
                {"tag": "div", "text": {"tag": "plain_text", "content": "❌ 无法解析直播数据"}}
            ]
        }
    
    # 根据评分选择颜色和评语
    score = analysis['score']
    if score >= 80:
        color = "green"
        comment = "🌟 优秀表现！数据非常亮眼"
    elif score >= 60:
        color = "blue"
        comment = "👍 良好表现，还有提升空间"
    elif score >= 40:
        color = "yellow"
        comment = "💪 一般表现，需要优化策略"
    else:
        color = "red"
        comment = "⚠️ 表现不佳，建议调整策略"
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "📊 抖音直播数据分析报告"},
            "template": color
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": f"📈 {comment}"
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "fields": [
                    {"is_short": True, "text": {"tag": "plain_text", "content": f"💰 GMV\n**RM {analysis['gmv']:.2f}**"}},
                    {"is_short": True, "text": {"tag": "plain_text", "content": f"👥 观众数\n**{analysis['viewers']:,}**"}},
                    {"is_short": True, "text": {"tag": "plain_text", "content": f"📦 订单数\n**{analysis['orders']:,}**"}},
                    {"is_short": True, "text": {"tag": "plain_text", "content": f"🎯 转化率\n**{analysis['conversion_rate']}**"}},
                    {"is_short": True, "text": {"tag": "plain_text", "content": f"💳 客单价\n**RM {analysis['aov']:.2f}**"}},
                    {"is_short": True, "text": {"tag": "plain_text", "content": f"👀 每观众贡献\n**RM {analysis['gpv']:.2f}**"}}
                ]
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": f"🏆 综合评分: **{analysis['rating']}** ({score}分)"
                }
            }
        ]
    }
    
    return card

@app.route('/')
def index():
    """健康检查"""
    return jsonify({
        "status": "running",
        "service": "抖音直播飞书机器人",
        "version": "2.0"
    })

@app.route('/api/feishu/webhook', methods=['GET', 'POST'])
def feishu_webhook():
    """飞书事件回调"""
    try:
        # 验证请求
        if request.method == 'GET':
            challenge = request.args.get('challenge', '')
            return jsonify({"challenge": challenge})
        
        event = request.json
        logger.info(f"Received event: {json.dumps(event, ensure_ascii=False)}")
        
        # 检查事件类型
        event_type = event.get('header', {}).get('event_type', '')
        
        if event_type in ['im.message.receive_v1', 'im:message']:
            message = event.get('event', {}).get('message', {})
            
            # 获取消息内容
            content_str = message.get('content', '{}')
            
            # 解析content JSON字符串
            try:
                if content_str.startswith('{'):
                    content = json.loads(content_str)
                else:
                    content = {}
            except:
                content = {}
            
            # 提取文本内容
            text_content = content.get('text', '')
            if not text_content:
                text_content = content_str
            
            # 移除@mentions
            text_content = re.sub(r'@_user_\d+\s*', '', text_content).strip()
            
            logger.info(f"Message text: {text_content}")
            
            if not text_content:
                return jsonify({"success": True})
            
            # 解析数据
            data = parse_live_stream_data(text_content)
            logger.info(f"Parsed data: {data}")
            
            # 生成分析卡片
            card = generate_analysis_card(data)
            
            # 发送回复
            receive_id = message.get('sender', {}).get('sender_id', {}).get('open_id', '')
            
            if receive_id:
                send_feishu_message(
                    receive_id=receive_id,
                    msg_type="interactive",
                    content=card
                )
            
            return jsonify({"success": True})
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"处理飞书事件异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """直接分析接口"""
    try:
        data = request.json
        text = data.get('text', '')
        
        parsed = parse_live_stream_data(text)
        analysis = analyze_live_stream(parsed)
        
        return jsonify({
            "success": True,
            "original": data,
            "parsed": parsed,
            "analysis": analysis
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
