# API适配层 - 将原有估值逻辑包装为API友好的函数
import pandas as pd
import os
import sys
from datetime import datetime
import json
import requests
import re
from collections import defaultdict

# 导入原有模块
import pytz
from fund_estimator import (
    get_stock_price_changes,
    smart_ticker_converter,
    get_market_status,
    get_market_type_from_ticker,
    HOLDINGS_FOLDER
)

def get_historical_fund_data(fund_code, target_date):
    """
    从天天基金网获取基金历史净值数据
    返回指定日期的涨跌幅
    """
    try:
        # 格式化日期
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        date_str = target_date.strftime('%Y-%m-%d')
        
        # 天天基金网历史净值API
        url = f"http://api.fund.eastmoney.com/f10/lsjz"
        params = {
            'fundCode': fund_code,
            'pageIndex': 1,
            'pageSize': 20,
            'startDate': date_str,
            'endDate': date_str,
            '_': int(datetime.now().timestamp() * 1000)
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'http://fundf10.eastmoney.com/jjjz_{fund_code}.html'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 解析JSON响应
        data = response.json()
        if data.get('Data') and data['Data'].get('LSJZList'):
            fund_data = data['Data']['LSJZList'][0]
            
            # 提取涨跌幅
            change_rate = fund_data.get('JZZZL', '')
            if change_rate and change_rate != '--':
                return float(change_rate.rstrip('%'))
        
        # 如果天天基金失败，尝试其他数据源
        return get_fund_data_from_backup_source(fund_code, target_date)
        
    except Exception as e:
        print(f"获取基金 {fund_code} 历史数据失败: {e}")
        return None

def get_fund_data_from_backup_source(fund_code, target_date):
    """
    备用数据源：蛋卷基金
    """
    try:
        date_str = target_date.strftime('%Y-%m-%d')
        
        # 蛋卷基金API
        url = "https://danjuanapp.com/djapi/fund/nav/history"
        params = {
            'fund_code': fund_code,
            'start_date': date_str,
            'end_date': date_str,
            'page': 1,
            'size': 1
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=8)
        response.raise_for_status()
        
        data = response.json()
        if data.get('data') and data['data'].get('items'):
            item = data['data']['items'][0]
            change_rate = item.get('percentage')
            if change_rate is not None:
                return float(change_rate)
                
    except Exception as e:
        print(f"备用数据源获取失败: {e}")
    
    return None

def calculate_fund_estimate_api(csv_path, mode, target_date=None):
    """
    API友好的估值计算函数
    返回结构化的JSON数据而不是打印输出
    """
    fund_code = os.path.basename(csv_path).split('.')[0]
    
    # 回顾模式：直接获取真实历史数据
    if mode == 'review' and target_date:
        historical_change = get_historical_fund_data(fund_code, target_date)
        
        beijing_time = datetime.now(pytz.timezone('Asia/Shanghai'))
        
        result = {
            'fund_code': fund_code,
            'mode': 'review',
            'target_date': target_date,
            'historical_change': historical_change,
            'update_time': beijing_time.strftime('%Y-%m-%d %H:%M:%S 北京时间'),
            'data_source': '天天基金网/蛋卷基金',
            'note': '这是真实历史数据，非估算值'
        }
        
        if historical_change is None:
            result.update({
                'error': f'无法获取基金 {fund_code} 在 {target_date} 的历史数据',
                'suggestion': '请检查基金代码是否正确或选择其他交易日期'
            })
        
        return result
    
    # 实时模式：继续原有逻辑
    try:
        # 读取持仓数据
        holdings_df = pd.read_csv(csv_path, dtype={'证券代码': str})
        holdings_df.columns = holdings_df.columns.str.strip()
        
        required_cols = ['公司名称', '证券代码', '占基金资产净值比例(%)']
        if not all(col in holdings_df.columns for col in required_cols):
            raise ValueError(f"CSV文件缺少必要的列: {required_cols}")
        
        weight_col = '占基金资产净值比例(%)'
        holdings_df[weight_col] = pd.to_numeric(holdings_df[weight_col], errors='coerce')
        holdings_df.dropna(subset=[weight_col], inplace=True)
        
        # 构建股票代码映射
        ticker_map = {
            str(row['公司名称']).strip(): smart_ticker_converter(str(row['证券代码']).strip()) 
            for _, row in holdings_df.iterrows()
        }
        
        # 去重处理
        unique_name_map = {}
        processed_names = set()
        unique_rows_list = []
        for index, row in holdings_df.iterrows():
            name = str(row['公司名称']).strip()
            if name not in processed_names:
                unique_name_map[name] = ticker_map[name]
                processed_names.add(name)
                unique_rows_list.append(row)
        
        if len(unique_name_map) != len(holdings_df):
            holdings_df = pd.DataFrame(unique_rows_list)
        
        # 根据模式获取股价变化
        user_mode = None
        if mode == 'realtime':
            user_mode = 'REALTIME_MODE'
            calc_mode = 'CURRENT_DAY'
        elif mode == 'review':
            user_mode = 'REVIEW_MODE' 
            calc_mode = 'REVIEW_MODE'
        else:
            calc_mode = mode
        
        # 市场状态分析
        active_ticker_map = {}
        market_analysis = []
        
        if user_mode == 'REALTIME_MODE':
            query_statuses = ["open", "closed_today", "active_day", "lunch_break"]
            for name, ticker in unique_name_map.items():
                status = get_market_status(ticker)
                if status in query_statuses:
                    active_ticker_map[name] = ticker
                market_analysis.append({
                    'name': name,
                    'ticker': ticker,
                    'status': status,
                    'active': status in query_statuses
                })
            stock_changes = get_stock_price_changes(active_ticker_map, calc_mode, target_date)
        elif user_mode == 'REVIEW_MODE':
            stock_changes = get_stock_price_changes(unique_name_map, calc_mode, target_date)
        else:
            stock_changes = get_stock_price_changes(unique_name_map, calc_mode, target_date)
        
        # 计算估值
        total_change, total_weight = 0.0, 0.0
        calc_weight, failed_weight, inactive_weight = defaultdict(float), defaultdict(float), defaultdict(float)
        
        holdings_details = []
        
        for _, row in holdings_df.iterrows():
            name = str(row['公司名称']).strip()
            weight = row['占基金资产净值比例(%)'] / 100.0
            total_weight += weight
            ticker = unique_name_map.get(name, "")
            market = get_market_type_from_ticker(ticker)
            
            status = get_market_status(ticker)
            query_statuses = ["open", "closed_today", "active_day", "lunch_break"]
            is_active_for_today = ((user_mode == 'REALTIME_MODE') and status in query_statuses)
            
            change_pct = None
            if is_active_for_today or user_mode == 'REVIEW_MODE' or calc_mode == 'PREVIOUS_DAY':
                change_pct = stock_changes.get(name)
                if change_pct is not None and pd.notna(change_pct):
                    total_change += weight * change_pct
                    calc_weight[market] += weight
                else:
                    failed_weight[market] += weight
            else:
                inactive_weight[market] += weight
            
            # 记录持仓详情
            holdings_details.append({
                'name': name,
                'ticker': ticker,
                'weight': weight,
                'market': market,
                'change': change_pct,
                'status': status if user_mode == 'REALTIME_MODE' else 'review'
            })
        
        estimated_change = total_change / total_weight if total_weight > 0 else 0
        
        # 构建返回数据
        result = {
            'fund_code': os.path.basename(csv_path).split('.')[0],
            'mode': mode,
            'target_date': target_date,
            'estimated_change': estimated_change,
            'update_time': datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S 北京时间'),
            'statistics': {
                'total_weight': total_weight,
                'calc_weight': sum(calc_weight.values()),
                'failed_weight': sum(failed_weight.values()),
                'inactive_weight': sum(inactive_weight.values()),
                '成功计算占比': f"{(sum(calc_weight.values()) / total_weight * 100):.1f}%" if total_weight > 0 else "0.0%",
                '查询失败占比': f"{(sum(failed_weight.values()) / total_weight * 100):.1f}%" if total_weight > 0 else "0.0%",
                '未开盘市场占比': f"{(sum(inactive_weight.values()) / total_weight * 100):.1f}%" if total_weight > 0 else "0.0%",
                'markets_detail': {
                    'calc': dict(calc_weight),
                    'failed': dict(failed_weight),
                    'inactive': dict(inactive_weight)
                }
            },
            'holdings': holdings_details,
            'market_status_analysis': market_analysis if user_mode == 'REALTIME_MODE' else []
        }
        
        return result
        
    except Exception as e:
        raise e

def get_fund_summary_info(fund_code):
    """获取基金的简要信息"""
    try:
        csv_path = os.path.join(HOLDINGS_FOLDER, f"{fund_code}.csv")
        if not os.path.exists(csv_path):
            return None
        
        holdings_df = pd.read_csv(csv_path, dtype={'证券代码': str})
        holdings_count = len(holdings_df)
        
        # 计算权重分布
        if '占基金资产净值比例(%)' in holdings_df.columns:
            holdings_df['占基金资产净值比例(%)'] = pd.to_numeric(holdings_df['占基金资产净值比例(%)'], errors='coerce')
            total_weight = holdings_df['占基金资产净值比例(%)'].sum()
        else:
            total_weight = 0
        
        return {
            'holdings_count': holdings_count,
            'total_weight': total_weight / 100.0 if total_weight > 0 else 0,
            'last_updated': datetime.fromtimestamp(os.path.getmtime(csv_path)).strftime('%Y-%m-%d')
        }
        
    except Exception:
        return None