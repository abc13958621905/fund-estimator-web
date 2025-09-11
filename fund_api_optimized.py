# 优化版API适配层 - 处理API限制和错误
import pandas as pd
import os
import sys
from datetime import datetime
import json
import time
import random
from collections import defaultdict

# 导入原有模块
from fund_estimator import (
    get_stock_price_changes,
    smart_ticker_converter,
    get_market_status,
    get_market_type_from_ticker,
    HOLDINGS_FOLDER
)

# 全局缓存
_cache = {}
_cache_timestamp = {}
CACHE_DURATION = 300  # 5分钟缓存

def get_stock_price_changes_optimized(ticker_map, mode, target_date=None):
    """
    优化的股价获取函数，处理API限制
    """
    if not ticker_map:
        return {}
    
    cache_key = f"{mode}_{target_date}_{len(ticker_map)}"
    current_time = time.time()
    
    # 检查缓存
    if (cache_key in _cache and 
        cache_key in _cache_timestamp and 
        current_time - _cache_timestamp[cache_key] < CACHE_DURATION):
        print("使用缓存数据...")
        return _cache[cache_key]
    
    print(f"开始获取 {len(ticker_map)} 只股票数据...")
    
    # 分批处理，避免API限制
    batch_size = 15  # 每批15只股票
    all_changes = {}
    
    ticker_items = list(ticker_map.items())
    total_batches = (len(ticker_items) + batch_size - 1) // batch_size
    
    for i in range(0, len(ticker_items), batch_size):
        batch_num = i // batch_size + 1
        batch = dict(ticker_items[i:i+batch_size])
        
        print(f"处理批次 {batch_num}/{total_batches} ({len(batch)} 只股票)...")
        
        try:
            # 添加延时，避免频率限制
            if batch_num > 1:
                delay = random.uniform(2, 4)
                print(f"等待 {delay:.1f} 秒...")
                time.sleep(delay)
            
            batch_changes = get_stock_price_changes(batch, mode, target_date)
            all_changes.update(batch_changes)
            
        except Exception as e:
            print(f"批次 {batch_num} 查询失败: {e}")
            # 对失败的股票设置0涨跌幅
            for name in batch.keys():
                all_changes[name] = 0.0
            continue
    
    # 缓存结果
    _cache[cache_key] = all_changes
    _cache_timestamp[cache_key] = current_time
    
    print(f"股票数据获取完成，成功 {len(all_changes)} 只")
    return all_changes

def calculate_fund_estimate_api_optimized(csv_path, mode, target_date=None):
    """
    优化版API友好的估值计算函数
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
        
        print(f"读取持仓数据：{len(holdings_df)} 只股票")
        
        # 构建股票代码映射
        ticker_map = {}
        for _, row in holdings_df.iterrows():
            name = str(row['公司名称']).strip()
            code = str(row['证券代码']).strip()
            ticker = smart_ticker_converter(code)
            ticker_map[name] = ticker
        
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
            print(f"去重后持仓：{len(unique_name_map)} 只股票")
        
        # 根据模式获取股价变化
        if mode == 'realtime':
            calc_mode = 'CURRENT_DAY'
            user_mode = 'REALTIME_MODE'
        elif mode == 'review':
            calc_mode = 'REVIEW_MODE'
            user_mode = 'REVIEW_MODE'
        else:
            calc_mode = mode
            user_mode = None
        
        # 市场状态分析
        active_ticker_map = {}
        market_analysis = []
        
        if user_mode == 'REALTIME_MODE':
            query_statuses = ["open", "closed_today", "active_day", "lunch_break"]
            for name, ticker in unique_name_map.items():
                try:
                    status = get_market_status(ticker)
                    if status in query_statuses:
                        active_ticker_map[name] = ticker
                    market_analysis.append({
                        'name': name,
                        'ticker': ticker,
                        'status': status,
                        'active': status in query_statuses
                    })
                except Exception as e:
                    print(f"获取 {name} 市场状态失败: {e}")
                    market_analysis.append({
                        'name': name,
                        'ticker': ticker,
                        'status': 'unknown',
                        'active': False
                    })
            
            stock_changes = get_stock_price_changes_optimized(active_ticker_map, calc_mode, target_date)
        else:
            stock_changes = get_stock_price_changes_optimized(unique_name_map, calc_mode, target_date)
        
        # 计算估值
        total_change, total_weight = 0.0, 0.0
        calc_weight, failed_weight, inactive_weight = defaultdict(float), defaultdict(float), defaultdict(float)
        
        holdings_details = []
        success_count = 0
        
        for _, row in holdings_df.iterrows():
            name = str(row['公司名称']).strip()
            weight = row['占基金资产净值比例(%)'] / 100.0
            total_weight += weight
            ticker = unique_name_map.get(name, "")
            market = get_market_type_from_ticker(ticker)
            
            try:
                status = get_market_status(ticker)
            except:
                status = 'unknown'
            
            query_statuses = ["open", "closed_today", "active_day", "lunch_break"]
            is_active_for_today = ((user_mode == 'REALTIME_MODE') and status in query_statuses)
            
            change_pct = None
            if is_active_for_today or user_mode == 'REVIEW_MODE' or calc_mode == 'PREVIOUS_DAY':
                change_pct = stock_changes.get(name)
                if change_pct is not None and pd.notna(change_pct):
                    total_change += weight * change_pct
                    calc_weight[market] += weight
                    success_count += 1
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
        success_rate = success_count / len(holdings_df) if len(holdings_df) > 0 else 0
        
        print(f"估值计算完成：{success_count}/{len(holdings_df)} 只股票成功")
        
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
                'success_rate': success_rate,
                'success_count': success_count,
                'total_count': len(holdings_df),
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
        print(f"估值计算错误: {e}")
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