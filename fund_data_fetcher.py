import json
import datetime
import re
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError

def fetch_fund_info_from_eastmoney(fund_code):
    """从天天基金网获取基金信息"""
    try:
        # 天天基金API
        url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"

        # 设置请求头
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')

        # 解析JSONP格式数据
        # 格式: jsonpgz({"fundcode":"007455","name":"华夏中证5G通信主题ETF联接A",...})
        jsonp_match = re.search(r'jsonpgz\((.*)\)', content)
        if jsonp_match:
            json_str = jsonp_match.group(1)
            data = json.loads(json_str)

            return {
                "code": data.get("fundcode"),
                "name": data.get("name"),
                "current_nav": data.get("dwjz"),  # 单位净值
                "estimated_nav": data.get("gsz"),  # 估算净值
                "estimated_change": data.get("gszzl"),  # 估算涨跌幅
                "nav_date": data.get("jzrq"),  # 净值日期
                "update_time": data.get("gztime"),  # 更新时间
                "status": "success"
            }
    except Exception as e:
        return {"error": f"天天基金查询失败: {str(e)}"}

def fetch_fund_info_from_sina(fund_code):
    """从新浪财经获取基金信息"""
    try:
        # 新浪财经基金API
        url = f"http://hq.sinajs.cn/list=fu_{fund_code}"

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('gbk')

        # 解析新浪财经数据格式
        # 格式: var hq_str_fu_007455="华夏中证5G通信主题ETF联接A,1.2345,1.2500,0.0155,1.25,2023-09-26";
        match = re.search(f'var hq_str_fu_{fund_code}="([^"]+)"', content)
        if match:
            data_str = match.group(1)
            parts = data_str.split(',')

            if len(parts) >= 5:
                return {
                    "code": fund_code,
                    "name": parts[0],
                    "current_nav": parts[1],
                    "estimated_nav": parts[2],
                    "estimated_change": parts[3],
                    "nav_date": parts[4],
                    "status": "success"
                }
    except Exception as e:
        return {"error": f"新浪财经查询失败: {str(e)}"}

def fetch_fund_info_multi_source(fund_code):
    """多数据源获取基金信息"""

    # 优先使用天天基金
    result = fetch_fund_info_from_eastmoney(fund_code)
    if "error" not in result and result.get("name"):
        result["source"] = "天天基金"
        return result

    # 备用新浪财经
    result = fetch_fund_info_from_sina(fund_code)
    if "error" not in result and result.get("name"):
        result["source"] = "新浪财经"
        return result

    return {"error": f"所有数据源都无法获取基金 {fund_code} 的信息"}

def validate_and_update_fund_database():
    """验证并更新基金数据库"""

    # 测试基金代码列表
    test_fund_codes = [
        "007455", "012922", "016531",  # 原有的基金
        "000001", "110022", "519066",  # 常见基金
        "161725", "502056", "001632",  # 更多基金
        "320003", "040025", "270042"   # 扩展基金
    ]

    fund_database = {}
    successful_queries = 0
    failed_queries = []

    print("正在从财经网站获取基金信息...")

    for fund_code in test_fund_codes:
        print(f"查询基金: {fund_code}")
        result = fetch_fund_info_multi_source(fund_code)

        if "error" not in result:
            fund_database[fund_code] = {
                "name": result["name"],
                "current_nav": result.get("current_nav"),
                "source": result.get("source"),
                "last_updated": datetime.datetime.now().isoformat()
            }
            successful_queries += 1
            print(f"  ✓ {result['name']} (来源: {result.get('source')})")
        else:
            failed_queries.append(fund_code)
            print(f"  ✗ {result['error']}")

    print(f"\n查询完成: 成功 {successful_queries}/{len(test_fund_codes)}")
    if failed_queries:
        print(f"失败的基金代码: {failed_queries}")

    return fund_database

# 测试函数
if __name__ == "__main__":
    # 测试单个基金查询
    print("测试单个基金查询:")
    result = fetch_fund_info_multi_source("007455")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n" + "="*50)

    # 批量验证基金数据库
    database = validate_and_update_fund_database()

    print(f"\n最终基金数据库:")
    print(json.dumps(database, ensure_ascii=False, indent=2))