# 基金估值Web应用后端API
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import sys
import json
from datetime import datetime, timedelta
import threading
import time

# 导入原有的基金估值逻辑
from fund_estimator import (
    get_fund_name, 
    determine_calculation_mode,
    HOLDINGS_FOLDER
)

# 导入API适配层
from fund_api import calculate_fund_estimate_api, get_fund_summary_info

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局变量存储缓存数据
fund_cache = {}
cache_timestamp = {}
CACHE_DURATION = 300  # 5分钟缓存

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/funds', methods=['GET'])
def get_funds():
    """获取所有可用的基金列表"""
    try:
        if not os.path.isdir(HOLDINGS_FOLDER):
            return jsonify({'error': f'找不到持仓文件夹 {HOLDINGS_FOLDER}'}), 404
        
        available_files = [f for f in os.listdir(HOLDINGS_FOLDER) if f.endswith('.csv') and len(f) == 10]
        if not available_files:
            return jsonify({'error': f'{HOLDINGS_FOLDER} 文件夹是空的'}), 404
        
        funds = []
        for file in sorted(available_files):
            fund_code = file.split('.')[0]
            fund_name = get_fund_name(fund_code)
            summary = get_fund_summary_info(fund_code)
            
            funds.append({
                'code': fund_code,
                'name': fund_name,
                'file': file,
                'summary': summary
            })
        
        return jsonify({'funds': funds})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/estimate', methods=['POST'])
def estimate_fund():
    """基金估值计算"""
    try:
        data = request.get_json()
        fund_code = data.get('fund_code')
        mode = data.get('mode', 'realtime')  # realtime 或 review
        target_date = data.get('target_date')
        
        if not fund_code:
            return jsonify({'error': '基金代码不能为空'}), 400
        
        # 检查缓存
        cache_key = f"{fund_code}_{mode}_{target_date}"
        current_time = time.time()
        
        if (cache_key in fund_cache and 
            cache_key in cache_timestamp and 
            current_time - cache_timestamp[cache_key] < CACHE_DURATION):
            return jsonify(fund_cache[cache_key])
        
        # 构建CSV文件路径
        csv_file_path = os.path.join(HOLDINGS_FOLDER, f"{fund_code}.csv")
        if not os.path.exists(csv_file_path):
            return jsonify({'error': f'找不到基金 {fund_code} 的持仓文件'}), 404
        
        # 调用估值计算
        result = calculate_fund_estimate_api(csv_file_path, mode, target_date)
        
        # 缓存结果
        fund_cache[cache_key] = result
        cache_timestamp[cache_key] = current_time
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-status', methods=['GET'])
def get_market_status():
    """获取当前市场状态"""
    try:
        mode = determine_calculation_mode()
        current_time = datetime.now()
        
        return jsonify({
            'mode': mode,
            'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'is_trading_time': mode == 'CURRENT_DAY'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate-date', methods=['POST'])
def validate_date():
    """验证用户输入的日期"""
    try:
        data = request.get_json()
        date_str = data.get('date')
        
        if not date_str:
            return jsonify({'valid': False, 'error': '日期不能为空'}), 400
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            today = datetime.now()
            
            if target_date.date() > today.date():
                return jsonify({'valid': False, 'error': '不能查询未来的日期'})
            
            if (today - target_date).days > 365:
                return jsonify({'valid': False, 'error': '查询日期过于久远（超过1年）'})
            
            return jsonify({'valid': True, 'date': date_str})
            
        except ValueError:
            return jsonify({'valid': False, 'error': '日期格式不正确，请使用 YYYY-MM-DD 格式'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 基金估值Web应用启动中...")
    print(f"📱 访问地址: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)