from http.server import BaseHTTPRequestHandler
import json
import datetime
from urllib.parse import urlparse, parse_qs

# 模拟基金数据
SAMPLE_FUND_DATA = {
    "007455": {
        "name": "华夏中证5G通信主题ETF联接A",
        "holdings": [
            {"name": "中兴通讯", "code": "000063", "weight": 8.5},
            {"name": "中国移动", "code": "600941", "weight": 7.2}
        ]
    },
    "012922": {
        "name": "汇添富中证生物科技指数A",
        "holdings": [
            {"name": "药明康德", "code": "603259", "weight": 9.1},
            {"name": "恒瑞医药", "code": "600276", "weight": 8.3}
        ]
    }
}

HTML_CONTENT = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📈 基金估值助手</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .container { max-width: 500px; padding: 20px; }
        .card {
            backdrop-filter: blur(20px);
            background: rgba(255, 255, 255, 0.95);
            border: none;
            border-radius: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .fund-card { cursor: pointer; transition: all 0.3s ease; }
        .fund-card:hover { transform: translateY(-5px); box-shadow: 0 12px 40px rgba(0,0,0,0.15); }
        .success-notice {
            background: rgba(40, 167, 69, 0.2);
            color: white;
            border: 2px solid rgba(40, 167, 69, 0.5);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="text-center text-white mb-4">
            <h1 class="display-6 fw-bold">📈 基金估值助手</h1>
            <p class="lead">实时追踪 · 智能分析</p>
        </div>

        <div class="success-notice text-center">
            <h5>🎉 Vercel部署成功！</h5>
            <p class="mb-1">基金估值应用已成功部署</p>
            <small>使用原生Python HTTP处理器</small>
        </div>

        <div class="card">
            <div class="card-header">
                <h6 class="mb-0">📊 支持的基金</h6>
            </div>
            <div class="card-body p-0">
                <div class="fund-card" onclick="queryFund('007455')">
                    <div class="card-body">
                        <h6 class="card-title mb-1">华夏中证5G通信主题ETF联接A</h6>
                        <small class="text-muted">007455</small>
                        <span class="badge bg-success float-end">可用</span>
                    </div>
                </div>
                <div class="fund-card" onclick="queryFund('012922')">
                    <div class="card-body">
                        <h6 class="card-title mb-1">汇添富中证生物科技指数A</h6>
                        <small class="text-muted">012922</small>
                        <span class="badge bg-success float-end">可用</span>
                    </div>
                </div>
            </div>
        </div>

        <div id="result"></div>

        <div class="card">
            <div class="card-body text-center">
                <h6>🚀 技术信息</h6>
                <div class="row">
                    <div class="col-4">
                        <div class="h6 text-primary">Vercel</div>
                        <small class="text-muted">部署平台</small>
                    </div>
                    <div class="col-4">
                        <div class="h6 text-success">Python</div>
                        <small class="text-muted">后端语言</small>
                    </div>
                    <div class="col-4">
                        <div class="h6 text-info">REST</div>
                        <small class="text-muted">API接口</small>
                    </div>
                </div>
                <div class="mt-3">
                    <small class="text-muted">部署时间: """ + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</small>
                </div>
            </div>
        </div>
    </div>

    <script>
        function queryFund(code) {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = '<div class="card"><div class="card-body text-center"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">查询中...</p></div></div>';

            fetch('/api/estimate?code=' + code)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    resultDiv.innerHTML = `
                        <div class="card">
                            <div class="card-body">
                                <h5 class="text-primary">${data.fund_name}</h5>
                                <div class="row mt-3">
                                    <div class="col-6">
                                        <strong>基金代码:</strong><br>
                                        <span class="text-muted">${data.fund_code}</span>
                                    </div>
                                    <div class="col-6">
                                        <strong>持仓数量:</strong><br>
                                        <span class="text-muted">${data.holdings_count}</span>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <strong>查询时间:</strong><br>
                                    <span class="text-muted">${data.query_time}</span>
                                </div>
                                <div class="mt-3">
                                    <span class="badge bg-success">✅ 查询成功</span>
                                </div>
                                <button class="btn btn-outline-secondary btn-sm mt-3" onclick="document.getElementById('result').innerHTML=''">
                                    返回列表
                                </button>
                            </div>
                        </div>
                    `;
                })
                .catch(error => {
                    resultDiv.innerHTML = `
                        <div class="card">
                            <div class="card-body text-danger">
                                <h6>❌ 查询失败</h6>
                                <p>${error.message}</p>
                                <button class="btn btn-outline-secondary btn-sm" onclick="document.getElementById('result').innerHTML=''">
                                    返回列表
                                </button>
                            </div>
                        </div>
                    `;
                });
        }

        // 页面加载动画
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('.card').forEach((card, index) => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                setTimeout(() => {
                    card.style.transition = 'all 0.5s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, index * 150);
            });
        });
    </script>
</body>
</html>"""

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # 设置响应头
        self.send_response(200)

        try:
            if path == '/':
                # 首页
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(HTML_CONTENT.encode('utf-8'))

            elif path == '/api/estimate':
                # 基金估值API
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                fund_code = query_params.get('code', [''])[0].strip()

                if not fund_code:
                    response = {"error": "请提供基金代码"}
                elif fund_code not in SAMPLE_FUND_DATA:
                    response = {"error": f"基金代码 {fund_code} 不存在"}
                else:
                    fund_info = SAMPLE_FUND_DATA[fund_code]
                    response = {
                        "fund_code": fund_code,
                        "fund_name": fund_info["name"],
                        "query_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "holdings_count": len(fund_info["holdings"]),
                        "top_holdings": fund_info["holdings"],
                        "status": "success",
                        "platform": "Vercel + Python"
                    }

                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

            elif path == '/api/funds':
                # 基金列表API
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                response = {
                    "available_funds": [
                        {"code": "007455", "name": "华夏中证5G通信主题ETF联接A"},
                        {"code": "012922", "name": "汇添富中证生物科技指数A"}
                    ],
                    "total": 2,
                    "status": "success"
                }

                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

            elif path == '/api/test':
                # 测试API
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                response = {
                    "status": "ok",
                    "message": "基金估值API运行正常",
                    "time": datetime.datetime.now().isoformat(),
                    "platform": "Vercel Serverless"
                }

                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

            else:
                # 404错误
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"error": "页面不存在"}
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            # 服务器错误
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": f"服务器错误: {str(e)}"}
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))