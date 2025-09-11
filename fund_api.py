# API适配层 - 将原有估值逻辑包装为API友好的函数
import pandas as pd
import os
import sys
from datetime import datetime
import json
from collections import defaultdict

# 导入原有模块
from fund_estimator import (
    get_stock_price_changes,
    smart_ticker_converter,
    get_market_status,
    get_market_type_from_ticker,
    HOLDINGS_FOLDER
)

def calculate_fund_estimate_api(csv_path, mode, target_date=None):
    """
    API友好的估值计算函数
    返回结构化的JSON数据而不是打印输出
    """
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
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'market_analysis': {
                'total_weight': total_weight,
                'calc_weight': sum(calc_weight.values()),
                'failed_weight': sum(failed_weight.values()),
                'inactive_weight': sum(inactive_weight.values()),
                'success_rate': sum(calc_weight.values()) / total_weight if total_weight > 0 else 0,
                'markets': {
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