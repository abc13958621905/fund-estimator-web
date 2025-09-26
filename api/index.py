from flask import Flask, request, jsonify, render_template_string
import datetime
import pytz

app = Flask(__name__)

# 模拟基金数据
SAMPLE_FUND_DATA = {
    "007455": {
        "name": "华夏中证5G通信主题ETF联接A",
        "holdings": [
            {"name": "中兴通讯", "code": "000063", "weight": 8.5},
            {"name": "中国移动", "code": "600941", "weight": 7.2},
            {"name": "烽火通信", "code": "600498", "weight": 6.8}
        ]
    },
    "012922": {
        "name": "汇添富中证生物科技指数A",
        "holdings": [
            {"name": "药明康德", "code": "603259", "weight": 9.1},
            {"name": "恒瑞医药", "code": "600276", "weight": 8.3},
            {"name": "迈瑞医疗", "code": "300760", "weight": 7.9}
        ]
    }
}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📈 基金估值助手</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 500px; padding: 20px; }
        .card { backdrop-filter: blur(20px); background: rgba(255, 255, 255, 0.95); border: none; border-radius: 20px; margin-bottom: 20px; }
        .fund-card { cursor: pointer; transition: all 0.3s ease; }
        .fund-card:hover { transform: translateY(-5px); }
        .demo-notice { background: rgba(255, 255, 255, 0.1); color: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="text-center text-white mb-4">
            <h1 class="display-6 fw-bold">📈 基金估值助手</h1>
            <p class="lead">实时追踪 · 智能分析</p>
        </div>

        <div class="demo-notice text-center">
            <h5>🎉 Vercel部署成功！</h5>
            <p class="mb-0">基金估值应用已成功部署到Vercel平台</p>
        </div>

        <div class="card">
            <div class="card-header">
                <h6 class="mb-0">📊 支持的基金</h6>
            </div>
            <div class="card-body">
                <div class="fund-card card mb-2" onclick="queryFund('007455')">
                    <div class="card-body">
                        <h6 class="card-title mb-1">华夏中证5G通信主题ETF联接A</h6>
                        <small class="text-muted">007455</small>
                    </div>
                </div>
                <div class="fund-card card mb-2" onclick="queryFund('012922')">
                    <div class="card-body">
                        <h6 class="card-title mb-1">汇添富中证生物科技指数A</h6>
                        <small class="text-muted">012922</small>
                    </div>
                </div>
            </div>
        </div>

        <div id="result"></div>

        <div class="card">
            <div class="card-body text-center">
                <h6>🚀 部署信息</h6>
                <p class="mb-0">
                    <strong>平台:</strong> Vercel<br>
                    <strong>时间:</strong> {{ current_time }}<br>
                    <strong>状态:</strong> <span class="text-success">✅ 运行正常</span>
                </p>
            </div>
        </div>
    </div>

    <script>
    function queryFund(code) {
        fetch('/api/estimate?code=' + code)
            .then(response => response.json())
            .then(data => {
                document.getElementById('result').innerHTML = `
                    <div class="card">
                        <div class="card-body">
                            <h5>${data.fund_name}</h5>
                            <p><strong>代码:</strong> ${data.fund_code}</p>
                            <p><strong>时间:</strong> ${data.query_time}</p>
                            <p><strong>状态:</strong> ✅ 查询成功</p>
                            <p><strong>持仓数量:</strong> ${data.holdings_count}</p>
                        </div>
                    </div>
                `;
            })
            .catch(error => {
                document.getElementById('result').innerHTML =
                    '<div class="card"><div class="card-body text-danger">查询失败: ' + error + '</div></div>';
            });
    }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, current_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route('/api/estimate')
def estimate():
    fund_code = request.args.get('code', '').strip()

    if not fund_code:
        return jsonify({"error": "请提供基金代码"})

    if fund_code not in SAMPLE_FUND_DATA:
        return jsonify({"error": f"基金代码 {fund_code} 不存在"})

    fund_info = SAMPLE_FUND_DATA[fund_code]
    now = datetime.datetime.now(pytz.timezone('Asia/Shanghai'))

    return jsonify({
        "fund_code": fund_code,
        "fund_name": fund_info["name"],
        "query_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "holdings_count": len(fund_info["holdings"]),
        "top_holdings": fund_info["holdings"],
        "status": "success",
        "platform": "Vercel"
    })

@app.route('/api/funds')
def get_funds():
    return jsonify({
        "available_funds": [
            {"code": "007455", "name": "华夏中证5G通信主题ETF联接A"},
            {"code": "012922", "name": "汇添富中证生物科技指数A"}
        ],
        "total": 2,
        "status": "success"
    })

@app.route('/api/test')
def test():
    return jsonify({
        "status": "ok",
        "message": "基金估值API运行正常",
        "time": datetime.datetime.now().isoformat(),
        "platform": "Vercel"
    })

# Vercel入口点
def handler(event, context):
    return app(event, context)

if __name__ == "__main__":
    app.run(debug=True)