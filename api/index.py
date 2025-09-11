
  from flask import Flask, request, jsonify, render_template_string
  import pandas as pd
  import yfinance as yf
  import datetime
  import pytz
  import os
  import json
  from io import StringIO

  app = Flask(__name__)

  # 模拟基金数据（用于演示）
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

  @app.route('/')
  def index():
      return render_template_string('''
  <!DOCTYPE html>
  <html lang="zh-CN">
  <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>基金估值工具</title>
      <style>
          body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }        
          .fund-card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; }        
          .input-group { margin: 15px 0; }
          input, button { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }        
          button { background: #007bff; color: white; cursor: pointer; }
          button:hover { background: #0056b3; }
          .result { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; }
      </style>
  </head>
  <body>
      <h1>🔍 基金估值工具</h1>
      <p>输入基金代码查询实时估值</p>

      <div class="input-group">
          <input type="text" id="fundCode" placeholder="输入6位基金代码，如：007455">
          <button onclick="searchFund()">查询估值</button>
      </div>

      <div id="result"></div>

      <div class="fund-card">
          <h3>📊 支持的基金代码：</h3>
          <ul>
              <li><strong>007455</strong> - 华夏中证5G通信主题ETF联接A</li>
              <li><strong>012922</strong> - 汇添富中证生物科技指数A</li>
          </ul>
      </div>

      <script>
      function searchFund() {
          const code = document.getElementById('fundCode').value.trim();
          const resultDiv = document.getElementById('result');

          if (!code) {
              alert('请输入基金代码');
              return;
          }

          resultDiv.innerHTML = '<div class="result">🔄 正在查询中...</div>';

          fetch(`/api/estimate?code=${code}`)
              .then(response => response.json())
              .then(data => {
                  if (data.error) {
                      resultDiv.innerHTML = `<div class="result">❌ ${data.error}</div>`;
                  } else {
                      resultDiv.innerHTML = `
                          <div class="result">
                              <h3>📈 ${data.fund_name}</h3>
                              <p><strong>基金代码：</strong> ${data.fund_code}</p>
                              <p><strong>查询时间：</strong> ${data.query_time}</p>
                              <p><strong>模式：</strong> ${data.mode}</p>
                              <p><strong>状态：</strong> ✅ 查询成功</p>
                              <p><strong>说明：</strong>
  这是演示版本，实际估值计算需要完整的持仓数据。</p>
                          </div>
                      `;
                  }
              })
              .catch(error => {
                  resultDiv.innerHTML = `<div class="result">❌ 网络错误：${error}</div>`;
              });
      }

      // 回车搜索
      document.getElementById('fundCode').addEventListener('keypress', function(e) {
          if (e.key === 'Enter') {
              searchFund();
          }
      });
      </script>
  </body>
  </html>
      ''')

  @app.route('/api/estimate')
  def estimate():
      fund_code = request.args.get('code', '').strip()

      if not fund_code:
          return jsonify({"error": "请提供基金代码"})

      if fund_code not in SAMPLE_FUND_DATA:
          return jsonify({"error": f"基金代码 {fund_code} 不存在，请尝试：007455 或 012922"})

      fund_info = SAMPLE_FUND_DATA[fund_code]

      # 获取当前时间
      now = datetime.datetime.now(pytz.timezone('Asia/Shanghai'))

      return jsonify({
          "fund_code": fund_code,
          "fund_name": fund_info["name"],
          "query_time": now.strftime("%Y-%m-%d %H:%M:%S"),
          "mode": "演示模式",
          "holdings_count": len(fund_info["holdings"]),
          "top_holdings": fund_info["holdings"][:3],
          "status": "success",
          "note": "这是Vercel部署的演示版本"
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
          "time": datetime.datetime.now().isoformat()
      })

  # Vercel需要的处理器
  def handler(request):
      return app

  if __name__ == "__main__":
      app.run(debug=True)
