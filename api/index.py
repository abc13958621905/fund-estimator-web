from flask import Flask, request, jsonify, render_template_string
  import os
  import sys

  # 简单的基金估值应用
  app = Flask(__name__)

  @app.route('/')
  def index():
      return '''
      <!DOCTYPE html>
      <html>
      <head>
          <title>基金估值工具</title>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
      </head>
      <body>
          <h1>基金估值工具</h1>
          <p>应用正在启动中，请稍候...</p>
          <p>如果您看到此页面，说明部署基本成功。</p>
      </body>
      </html>
      '''

  @app.route('/api/test')
  def test():
      return jsonify({"status": "ok", "message": "API working"})

  # Vercel入口点
  if __name__ == "__main__":
      app.run()