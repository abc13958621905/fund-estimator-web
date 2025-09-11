# fund_estimator.py (最终版 v8 - 全球化时间逻辑)

import pandas as pd
import yfinance as yf
import datetime
import pytz
import warnings
import requests
import re
import sys
import os
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.simplefilter(action='ignore', category=FutureWarning)

HOLDINGS_FOLDER = 'fund_holdings'

def determine_calculation_mode():
    """
    重构为全球化时间逻辑：
    - 全球交易日的结束以美股收盘为准 (约北京时间次日凌晨5点)。
    - PREVIOUS_DAY模式仅在“全球静默期”(北京时间 05:00-09:30)及周末运行。
    """
    tz = pytz.timezone('Asia/Shanghai')
    now_beijing = datetime.datetime.now(tz)
    
    # 周末总是回顾模式
    if now_beijing.weekday() >= 5:
        return 'PREVIOUS_DAY'
    
    # 周一至周五的“全球静默期”(美股收盘后，A股开盘前)
    is_recap_window = (datetime.time(5, 0) <= now_beijing.time() < datetime.time(9, 30))
    if is_recap_window:
        return 'PREVIOUS_DAY'
        
    # 其他所有时间，都属于某个交易日的“当天”范畴
    return 'CURRENT_DAY'

def get_market_status(ticker):
    """根据股票代码判断市场状态，增加午间休市判断"""
    now_utc = datetime.datetime.now(pytz.utc)
    # 美股市场
    if ticker.isalpha() or '.' not in ticker:
        tz = pytz.timezone('US/Eastern')
        market_time = now_utc.astimezone(tz)
        if (datetime.time(9, 30) <= market_time.time() <= datetime.time(16, 0)) and market_time.weekday() < 5: return "open"
        return "closed"
    # A股、港股、北交所
    if ticker.endswith(('.SS', '.SZ', '.HK', '.BJ')):
        tz = pytz.timezone('Asia/Shanghai')
        market_time = now_utc.astimezone(tz)
        if market_time.weekday() >= 5: return "closed"
        
        time_now = market_time.time()
        is_morning = (datetime.time(9, 30) <= time_now <= datetime.time(11, 30))
        is_afternoon = (datetime.time(13, 0) <= time_now <= datetime.time(15, 0))
        is_lunch_break = (datetime.time(11, 30) < time_now < datetime.time(13, 0))

        if is_morning or is_afternoon: return "open"
        if is_lunch_break: return "lunch_break"
        if time_now > datetime.time(15, 0): return "closed_today"
        if time_now >= datetime.time(9, 30): return "active_day"
        return "closed"
    return "unknown"

def smart_ticker_converter(stock_code):
    stock_code = str(stock_code).strip().upper()
    if ' US' in stock_code: return stock_code.replace(' US', '').strip()
    if ' HK' in stock_code: return f"{stock_code.replace(' HK', '').strip().zfill(5)}.HK"
    if ' CH' in stock_code: stock_code = stock_code.replace(' CH', '').strip()
    if stock_code.isdigit() and len(stock_code) == 6:
        if stock_code.startswith(('8', '4', '9')):
            return f"{stock_code}.BJ"
        return f"{stock_code}.SS" if stock_code.startswith('6') else f"{stock_code}.SZ"
    if stock_code.isdigit() and len(stock_code) < 6: return f"{stock_code.zfill(5)}.HK"
    if stock_code.isalpha(): return stock_code
    return stock_code

def get_price_changes_from_sina(tickers_list):
    if not tickers_list: return {}, []
    print(f"\n--- 启动二级引擎(Sina)：查询 {len(tickers_list)} 只股票 ---")
    sina_tickers_map = {
        f"sh{t.replace('.SS', '')}" if t.endswith('.SS') else
        f"sz{t.replace('.SZ', '')}" if t.endswith('.SZ') else
        f"hk{t.replace('.HK', '')}" if t.endswith('.HK') else
        f"bj{t.replace('.BJ', '')}" if t.endswith('.BJ') else
        f"gb_{t.lower()}": t for t in tickers_list
    }
    url = f"https://hq.sinajs.cn/list={','.join(sina_tickers_map.keys())}"
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn/'}
    try:
        r = requests.get(url, headers=headers, timeout=15); r.encoding = 'gbk'
        r.raise_for_status()
        changes, found_tickers = {}, set()
        for res in r.text.split(';'):
            if len(res) < 20 or '=""' in res: continue
            match = re.search(r'var hq_str_([^=]+)="([^"]+)"', res)
            if not match: continue
            sina_ticker, data_str = match.groups()
            original_ticker = sina_tickers_map.get(sina_ticker)
            if not original_ticker: continue
            data = data_str.split(',')
            try:
                change = None
                if sina_ticker.startswith('gb_') and len(data) > 26:
                    latest, prev_close = float(data[1]), float(data[26])
                    if prev_close == 0 and len(data) > 7: prev_close = float(data[7])
                    if prev_close != 0: change = (latest - prev_close) / prev_close
                elif sina_ticker.startswith('hk') and len(data) > 8:
                    latest, prev_close = float(data[6]), float(data[3])
                    if prev_close != 0: change = (latest - prev_close) / prev_close
                elif sina_ticker.startswith(('sh', 'sz', 'bj')) and len(data) > 3:
                    latest, prev_close = float(data[3]), float(data[2])
                    if prev_close != 0: change = (latest - prev_close) / prev_close
                if change is not None:
                    changes[original_ticker] = change; found_tickers.add(original_ticker)
            except (ValueError, IndexError): continue
        still_failed = [t for t in tickers_list if t not in found_tickers]
        print(f"--- 二级引擎(Sina)完成：成功 {len(found_tickers)}，失败 {len(still_failed)} ---")
        return changes, still_failed
    except Exception as e:
        print(f"二级引擎(Sina)出错: {e}"); return {}, tickers_list

def get_price_changes_from_tencent(tickers_list):
    if not tickers_list: return {}, []
    print(f"\n--- 启动三级引擎(Tencent)：查询 {len(tickers_list)} 只股票 ---")
    tencent_tickers_map = {
        f"sh{t.replace('.SS', '')}" if t.endswith('.SS') else
        f"sz{t.replace('.SZ', '')}" if t.endswith('.SZ') else
        f"hk{t.replace('.HK', '')}" if t.endswith('.HK') else
        f"bj{t.replace('.BJ', '')}" if t.endswith('.BJ') else
        f"us{t.upper()}": t for t in tickers_list
    }
    url = f"http://qt.gtimg.cn/q={','.join(tencent_tickers_map.keys())}"
    try:
        r = requests.get(url, timeout=15); r.raise_for_status()
        changes, found_tickers = {}, set()
        for res in r.text.split(';'):
            if len(res) < 20 or '~""~' in res: continue
            match = re.search(r'v_([^=]+)="([^"]+)"', res)
            if not match: continue
            tencent_ticker, data_str = match.groups()
            original_ticker = tencent_tickers_map.get(tencent_ticker)
            if not original_ticker: continue
            data = data_str.split('~')
            try:
                change = None
                if len(data) > 4 and data[3] and data[4]:
                    latest, prev_close = float(data[3]), float(data[4])
                    if prev_close != 0: change = (latest - prev_close) / prev_close
                if change is not None:
                    changes[original_ticker] = change; found_tickers.add(original_ticker)
            except (ValueError, IndexError): continue
        still_failed = [t for t in tickers_list if t not in found_tickers]
        print(f"--- 三级引擎(Tencent)完成：成功 {len(found_tickers)}，失败 {len(still_failed)} ---")
        return changes, still_failed
    except Exception as e:
        print(f"三级引擎(Tencent)出错: {e}"); return {}, tickers_list

def get_stock_price_changes(ticker_map, mode, target_date=None):
    tickers_to_fetch = list(set(ticker_map.values()))
    if not tickers_to_fetch: return {}
    
    if mode == 'REVIEW_MODE' and target_date:
        # 回顾模式：获取指定日期前后几天的数据
        target_dt = datetime.datetime.strptime(target_date, '%Y-%m-%d')
        end_date = target_dt + datetime.timedelta(days=1)
        start_date = target_dt - datetime.timedelta(days=10)  # 多获取几天数据确保有足够的交易日
        print(f"\n--- 启动主引擎(Yahoo)：查询 {len(tickers_to_fetch)} 只股票在 {target_date} 的数据 ---")
        data = yf.download(tickers_to_fetch, start=start_date.strftime('%Y-%m-%d'), 
                          end=end_date.strftime('%Y-%m-%d'), progress=True, group_by='ticker', timeout=10)
    else:
        period = "3d" if mode == 'PREVIOUS_DAY' else "2d"
        print(f"\n--- 启动主引擎(Yahoo)：查询 {len(tickers_to_fetch)} 只股票 ---")
        data = yf.download(tickers_to_fetch, period=period, progress=True, group_by='ticker', timeout=10)
    
    changes, failed_yahoo = {}, []
    for ticker in tickers_to_fetch:
        try:
            stock_data = data.get(ticker)
            if stock_data is not None and not stock_data.empty and 'Close' in stock_data.columns and not stock_data['Close'].isnull().all():
                valid_closes = stock_data['Close'].dropna()
                if len(valid_closes) < 2: failed_yahoo.append(ticker); continue
                
                if mode == 'REVIEW_MODE' and target_date:
                    # 找到目标日期或最接近的交易日
                    target_dt = datetime.datetime.strptime(target_date, '%Y-%m-%d').date()
                    available_dates = [d.date() for d in valid_closes.index]
                    
                    # 找到目标日期当天或之前最近的交易日
                    target_trade_date = None
                    prev_trade_date = None
                    
                    for date in sorted(available_dates):
                        if date <= target_dt:
                            if target_trade_date is None or date > target_trade_date:
                                prev_trade_date = target_trade_date
                                target_trade_date = date
                    
                    if target_trade_date and prev_trade_date:
                        target_price = valid_closes[valid_closes.index.date == target_trade_date].iloc[-1]
                        prev_price = valid_closes[valid_closes.index.date == prev_trade_date].iloc[-1]
                        if pd.notna(prev_price) and pd.notna(target_price) and prev_price != 0:
                            changes[ticker] = (target_price - prev_price) / prev_price
                        else: failed_yahoo.append(ticker)
                    else: failed_yahoo.append(ticker)
                else:
                    prev_close, latest_price = valid_closes.iloc[-2], valid_closes.iloc[-1]
                    if pd.notna(prev_close) and pd.notna(latest_price) and prev_close != 0:
                        changes[ticker] = (latest_price - prev_close) / prev_close
                    else: failed_yahoo.append(ticker)
            else: failed_yahoo.append(ticker)
        except (KeyError, IndexError): failed_yahoo.append(ticker)
    print(f"--- 主引擎(Yahoo)完成：成功 {len(changes)}，失败 {len(failed_yahoo)} ---")
    
    if failed_yahoo and mode != 'REVIEW_MODE':  # 回顾模式下不使用备用数据源
        sina_changes, failed_sina = get_price_changes_from_sina(failed_yahoo)
        changes.update(sina_changes)
        if failed_sina:
            tencent_changes, failed_tencent = get_price_changes_from_tencent(failed_sina)
            changes.update(tencent_changes)
            if failed_tencent:
                print("\n--- 警告：以下股票在所有数据源均查询失败，可能已停牌或退市，按涨跌幅 0% 计算 ---")
                for ticker in failed_tencent:
                    name = next((k for k, v in ticker_map.items() if v == ticker), "N/A")
                    print(f"  [i] {name[:15]:<16s} ({ticker})")
                    changes[ticker] = 0.0
    elif failed_yahoo and mode == 'REVIEW_MODE':
        print("\n--- 警告：以下股票在回顾模式下查询失败，按涨跌幅 0% 计算 ---")
        for ticker in failed_yahoo:
            name = next((k for k, v in ticker_map.items() if v == ticker), "N/A")
            print(f"  [i] {name[:15]:<16s} ({ticker})")
            changes[ticker] = 0.0
    
    ticker_to_name = {v: k for k, v in ticker_map.items()}
    return {ticker_to_name.get(k): v for k, v in changes.items() if ticker_to_name.get(k)}

def get_market_type_from_ticker(ticker):
    if ticker.endswith(('.SS', '.SZ', '.BJ')): return 'A股'
    if ticker.endswith('.HK'): return '港股'
    if ticker.isalpha() or '.' not in ticker: return '美股'
    return '其他'

def estimate_fund_change_from_csv(csv_path, user_mode=None, target_date=None):
    if user_mode is None:
        mode = determine_calculation_mode()
        print(f"--- 当前估算模式: {mode} ---")
    else:
        if user_mode == 'REVIEW_MODE' and target_date:
            mode = 'PREVIOUS_DAY'  # 回顾模式使用历史数据逻辑
            print(f"--- 回顾模式: 查询 {target_date} 的估值 ---")
        elif user_mode == 'REALTIME_MODE':
            mode = 'CURRENT_DAY'  # 实时模式强制使用当日逻辑
            print(f"--- 实时估值模式 ---")
        else:
            mode = user_mode
            print(f"--- 估算模式: {mode} ---")
    try:
        holdings_df = pd.read_csv(csv_path, dtype={'证券代码': str})
        holdings_df.columns = holdings_df.columns.str.strip()
        required_cols = ['公司名称', '证券代码', '占基金资产净值比例(%)']
        if not all(col in holdings_df.columns for col in required_cols):
            print(f"错误: CSV文件 '{os.path.basename(csv_path)}' 缺少必要的列: {required_cols}")
            return
        weight_col = '占基金资产净值比例(%)'
        holdings_df[weight_col] = pd.to_numeric(holdings_df[weight_col], errors='coerce')
        original_rows = len(holdings_df)
        holdings_df.dropna(subset=[weight_col], inplace=True)
        if len(holdings_df) < original_rows:
            print(f"--- 警告：移除了 {original_rows - len(holdings_df)} 行持仓占比数据无效的记录 ---")
    except FileNotFoundError:
        print(f"错误：在 '{HOLDINGS_FOLDER}' 文件夹下找不到 '{os.path.basename(csv_path)}' 文件。"); return
    except pd.errors.ParserError as e:
        print(f"\n错误：CSV文件 '{os.path.basename(csv_path)}' 格式错误，无法解析。")
        match = re.search(r'line (\d+)', str(e))
        if match: print(f"请重点检查文件第 {match.group(1)} 行的格式，可能存在多余的逗号。")
        return
    except Exception as e:
        print(f"读取或处理CSV时发生未知错误: {e}"); return

    ticker_map = {
        str(row['公司名称']).strip(): smart_ticker_converter(str(row['证券代码']).strip()) 
        for _, row in holdings_df.iterrows()
    }
    
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
        print("\n--- 警告：CSV文件中存在重复的公司名称，将只使用第一条记录进行计算 ---")
        holdings_df = pd.DataFrame(unique_rows_list)

    active_ticker_map = {}
    if user_mode == 'REALTIME_MODE' or (user_mode is None and mode == 'CURRENT_DAY'):
        print("\n--- 市场状态分析 ---")
        query_statuses = ["open", "closed_today", "active_day", "lunch_break"]
        for name, ticker in unique_name_map.items():
            status = get_market_status(ticker)
            if status in query_statuses:
                active_ticker_map[name] = ticker
            print(f"{name[:15]:<16s} ({ticker:<10s}): 市场状态 {status:<12s}" + ("(加入查询)" if status in query_statuses else "(按0%计算)"))
        stock_changes = get_stock_price_changes(active_ticker_map, mode if user_mode is None else 'CURRENT_DAY', target_date)
    elif user_mode == 'REVIEW_MODE':
        print(f"\n--- 回顾模式：查询 {target_date} 所有市场数据 ---")
        stock_changes = get_stock_price_changes(unique_name_map, 'REVIEW_MODE', target_date)
    else:
        print("\n--- 所有市场均按上一个交易日收盘价计算 ---")
        stock_changes = get_stock_price_changes(unique_name_map, mode, target_date)

    total_change, total_weight = 0.0, 0.0
    calc_weight, failed_weight, inactive_weight = defaultdict(float), defaultdict(float), defaultdict(float)
    
    for _, row in holdings_df.iterrows():
        name = str(row['公司名称']).strip()
        weight = row['占基金资产净值比例(%)'] / 100.0
        total_weight += weight
        ticker = unique_name_map.get(name, "")
        market = get_market_type_from_ticker(ticker)

        status = get_market_status(ticker)
        query_statuses = ["open", "closed_today", "active_day", "lunch_break"]
        is_active_for_today = ((user_mode == 'REALTIME_MODE' or (user_mode is None and mode == 'CURRENT_DAY')) and status in query_statuses)
        
        if is_active_for_today or user_mode == 'REVIEW_MODE' or (user_mode is None and mode == 'PREVIOUS_DAY'):
            change_pct = stock_changes.get(name)
            if change_pct is not None and pd.notna(change_pct):
                total_change += weight * change_pct
                calc_weight[market] += weight
            else:
                failed_weight[market] += weight
        else:
            inactive_weight[market] += weight
            
    estimated_change = total_change / total_weight if total_weight > 0 else 0
    update_time = datetime.datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
    
    print("\n" + "="*50); print(" " * 19 + "估算结果"); print("="*50)
    print(f"更新时间: {update_time} (北京时间)")
    print(f"估算模式: {'今日实时估算' if mode == 'CURRENT_DAY' else '上一交易日回顾'}")
    print("-" * 50)
    print(f"基金总股票持仓占比: {total_weight:.2%}")

    def format_market_details(weight_dict):
        if not weight_dict: return "0.00%"
        parts = [f"{market}: {weight:.2%}" for market, weight in sorted(weight_dict.items()) if weight > 0]
        return ", ".join(parts) if parts else "0.00%"

    active_total = sum(calc_weight.values()) + sum(failed_weight.values())
    calc_total = sum(calc_weight.values())
    failed_total = sum(failed_weight.values())
    inactive_total = sum(inactive_weight.values())

    active_markets_str = format_market_details({k: calc_weight.get(k, 0) + failed_weight.get(k, 0) for k in set(calc_weight) | set(failed_weight)})
    if mode == 'CURRENT_DAY':
        print(f"  - 活跃市场持仓: {active_total:.2%} ({active_markets_str})")
    else:
        print(f"  - 全球市场持仓: {active_total:.2%} ({active_markets_str})")
        
    print(f"    - 成功计算占比: {calc_total:.2%} ({format_market_details(calc_weight)})")
    print(f"    - 查询失败占比: {failed_total:.2%} ({format_market_details(failed_weight)})")
    if inactive_total > 0:
        print(f"  - 未开盘市场持仓: {inactive_total:.2%} ({format_market_details(inactive_weight)})")

    print("-" * 50)
    print(f"估算涨跌幅: {estimated_change:+.4%}"); print("="*50)

def get_valid_date():
    """获取用户输入的有效日期"""
    while True:
        date_input = input("请输入要查询的日期 (格式: YYYY-MM-DD，如 2024-01-15): ").strip()
        if not date_input:
            print("日期不能为空，请重新输入。")
            continue
        
        try:
            # 验证日期格式
            target_date = datetime.datetime.strptime(date_input, '%Y-%m-%d')
            today = datetime.datetime.now()
            
            # 检查日期不能是未来
            if target_date.date() > today.date():
                print("不能查询未来的日期，请输入今天或过去的日期。")
                continue
                
            # 检查日期不能太久远（超过1年）
            if (today - target_date).days > 365:
                print("查询日期过于久远（超过1年），可能无法获取到数据，请选择近期日期。")
                continue
                
            return date_input
            
        except ValueError:
            print("日期格式不正确，请使用 YYYY-MM-DD 格式（如：2024-01-15）。")
            continue

def get_fund_name(fund_code):
    try:
        r = requests.get(f"http://fundgz.1234567.com.cn/js/{fund_code}.js", headers={'Referer': 'http://fund.eastmoney.com/'}, timeout=5)
        name = json.loads(re.search(r'jsonpgz\((.*)\)', r.text).group(1)).get('name')
        if name: return name
    except Exception: pass
    try:
        r = requests.get(f"https://hq.sinajs.cn/list=f_{fund_code}", headers={'Referer': 'http://finance.sina.com.cn/'}, timeout=5)
        r.encoding = 'gbk'
        match = re.search(r'="([^"]+)"', r.text)
        if match and match.group(1).split(',')[0]: return match.group(1).split(',')[0]
    except Exception: pass
    return "获取名称失败"

if __name__ == '__main__':
    while True:
        print("\n" + "="*60); print(" " * 20 + "基金涨跌幅估值工具"); print("="*60)
        
        # 模式选择菜单
        print("\n--- 请选择估值模式 ---")
        print("[1] 实时估值模式 - 根据当前市场状态进行实时估算")
        print("[2] 回顾模式 - 查询指定日期的历史估值")
        print("[q] 退出程序")
        print("-" * 60)
        
        mode_choice = input("请选择模式 (1/2/q): ").strip().lower()
        if mode_choice == 'q':
            print("感谢使用！")
            break
        
        if mode_choice not in ['1', '2']:
            print("无效的模式选择，请输入 1、2 或 q。")
            continue
        
        # 获取目标日期（回顾模式需要）
        target_date = None
        if mode_choice == '2':
            print("\n--- 回顾模式：请输入要查询的日期 ---")
            target_date = get_valid_date()
        
        if not os.path.isdir(HOLDINGS_FOLDER): 
            print(f"\n错误: 找不到持仓文件夹 '{HOLDINGS_FOLDER}'。")
            break
            
        available_files = [f for f in os.listdir(HOLDINGS_FOLDER) if re.match(r'^\d{6}\.csv$', f)]
        if not available_files: 
            print(f"\n错误: '{HOLDINGS_FOLDER}' 文件夹是空的。")
            break
        
        print("\n正在获取基金名称，请稍候...")
        fund_list = [{'code': f.split('.')[0], 'name': None} for f in sorted(available_files)]
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_fund = {executor.submit(get_fund_name, fund['code']): fund for fund in fund_list}
            for future in as_completed(future_to_fund):
                fund = future_to_fund[future]
                try: fund['name'] = future.result()
                except Exception: fund['name'] = "获取名称异常"
        
        print("\n--- 请选择您要估值的基金 ---")
        for i, fund in enumerate(fund_list): 
            print(f"[{i+1}] {fund['code']} - {fund['name']}")
        print("-" * 60)
        
        choice = input("请输入您想查询的基金序号 (输入 b 返回模式选择): ")
        if choice.lower() == 'b': 
            continue
        
        try:
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(fund_list):
                selected_fund = fund_list[choice_index]
                csv_file_path = os.path.join(HOLDINGS_FOLDER, f"{selected_fund['code']}.csv")
                print(f"\n您选择了: {selected_fund['code']} - {selected_fund['name']}")
                
                # 根据模式调用相应的函数
                user_mode = 'REALTIME_MODE' if mode_choice == '1' else 'REVIEW_MODE'
                estimate_fund_change_from_csv(csv_file_path, user_mode, target_date)
            else:
                print("\n无效的序号，请重新输入。")
        except ValueError:
            print("\n输入无效，请输入数字序号。")
        except Exception as e:
            print(f"\n处理基金时发生未知错误: {e}")
        
        print("\n" + "*"*60)
        input("按 Enter 键继续...")