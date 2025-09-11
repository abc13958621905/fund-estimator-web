# 📈 基金估值Web应用

## 🚀 快速启动

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动应用
```bash
python app.py
```

### 3. 访问应用
- **电脑访问**: http://localhost:5000
- **手机访问**: http://你的IP地址:5000

## 📁 文件说明

```
项目目录/
├── app.py              # Flask Web应用主文件
├── fund_api.py         # API适配层
├── fund_estimator.py   # 原有估值逻辑
├── templates/
│   └── index.html      # 前端页面
├── fund_holdings/      # 基金持仓数据文件夹
├── requirements.txt    # 依赖包列表
└── README.md          # 说明文档
```

## 🎯 功能特性

### ✅ 已实现功能
- 📱 响应式设计，完美适配手机端
- 🔄 实时估值模式 - 根据市场状态智能计算
- 📅 回顾模式 - 查询历史特定日期估值
- 🎨 现代化UI设计，支持暗色主题适配
- ⚡ 智能缓存，提升查询速度
- 📊 市场状态实时监控

### 🌟 核心特色
1. **双模式估值**
   - 实时模式：自动判断市场状态
   - 回顾模式：精确查询历史数据

2. **移动端优化**
   - 触摸友好的交互设计
   - 卡片式布局，信息层次清晰
   - 一键返回，流畅的页面切换

3. **数据可视化**
   - 涨跌幅醒目显示（红涨绿跌）
   - 持仓权重分析
   - 计算成功率统计

## 🔧 部署到云服务器

### 方案一：简单部署
```bash
# 1. 上传代码到服务器
# 2. 安装依赖
pip install -r requirements.txt

# 3. 后台运行
nohup python app.py &
```

### 方案二：使用Gunicorn (推荐)
```bash
# 安装Gunicorn
pip install gunicorn

# 启动服务
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 方案三：Docker部署
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 📱 手机使用技巧

1. **添加到主屏幕**
   - iOS: Safari浏览器 → 分享 → 添加到主屏幕
   - Android: Chrome浏览器 → 菜单 → 添加到主屏幕

2. **离线使用**
   - 应用支持缓存，短时间内可离线查看已计算的结果

3. **分享功能**
   - 可直接分享链接给他人使用

## 🛠️ 技术栈

- **后端**: Flask + Python
- **前端**: HTML5 + Bootstrap + JavaScript
- **数据处理**: pandas + yfinance
- **API设计**: RESTful API
- **缓存**: 内存缓存机制

## 🔮 未来计划

- [ ] 数据可视化图表
- [ ] 基金收藏功能
- [ ] 推送提醒服务
- [ ] 批量对比功能
- [ ] 历史趋势分析
- [ ] PWA支持（离线使用）

## 🐛 常见问题

### Q: 手机无法访问？
A: 确保手机和电脑在同一WiFi网络下，使用电脑的内网IP地址

### Q: 估值数据不准确？
A: 检查基金持仓文件是否为最新，网络连接是否正常

### Q: 加载速度慢？
A: 首次访问需要获取股价数据，后续会有缓存加速

---

🎉 **现在就开始体验移动端的基金估值吧！**