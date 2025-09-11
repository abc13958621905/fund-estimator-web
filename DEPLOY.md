# 🌐 免费云服务器部署教程

## 🎯 选择平台：Render (推荐)

### 📋 准备工作
确保你的项目文件夹包含：
- ✅ app.py (主应用文件)
- ✅ fund_api.py (API适配层) 
- ✅ fund_estimator.py (估值逻辑)
- ✅ requirements.txt (依赖列表)
- ✅ Procfile (启动配置)
- ✅ templates/index.html (前端页面)
- ✅ fund_holdings/ (基金数据文件夹)

## 🚀 Render部署步骤

### 第1步：注册Render账号
1. 访问 https://render.com
2. 点击 "Get Started for Free"
3. 选择 "GitHub" 登录（推荐）

### 第2步：上传代码到GitHub
1. 在GitHub创建新仓库：
   - 仓库名：`fund-estimator-web`
   - 设为Public（免费版需要）

2. 上传代码：
```bash
# 在你的项目文件夹执行
git init
git add .
git commit -m "基金估值Web应用"
git branch -M main
git remote add origin https://github.com/你的用户名/fund-estimator-web.git
git push -u origin main
```

### 第3步：在Render创建Web Service
1. 登录Render后点击 "New +"
2. 选择 "Web Service"
3. 连接你的GitHub仓库
4. 配置如下：

**基本设置：**
- Name: `fund-estimator`
- Environment: `Python 3`
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

**高级设置：**
- Auto-Deploy: `Yes`

5. 点击 "Create Web Service"

### 第4步：等待部署完成
- 部署时间：约3-5分钟
- 成功后会获得免费域名：`https://fund-estimator.onrender.com`

## 🔧 其他平台部署

### Railway 部署
1. 访问 https://railway.app
2. GitHub登录
3. "New Project" → "Deploy from GitHub repo"
4. 选择你的仓库，自动部署

### Fly.io 部署
1. 安装flyctl：https://fly.io/docs/hands-on/install-flyctl/
2. 登录：`flyctl auth login`
3. 在项目目录执行：`flyctl launch`
4. 按提示完成部署

## 📱 部署后使用

### 访问应用
- 🌐 **网址**: https://你的应用名.onrender.com
- 📱 **手机**: 直接用浏览器访问上述网址
- 🔗 **分享**: 可以把链接发给朋友使用

### 添加到手机桌面
**iPhone:**
1. Safari打开网站
2. 点击分享按钮
3. 选择"添加到主屏幕"
4. 像App一样使用

**Android:**
1. Chrome打开网站
2. 菜单 → "添加到主屏幕"
3. 确认添加

## 🛠️ 常见问题解决

### Q: 部署失败怎么办？
**A: 检查以下几点：**
- requirements.txt文件是否正确
- 是否包含所有必要文件
- GitHub仓库是否设为Public

### Q: 网站访问慢？
**A: 免费版限制：**
- Render免费版会"休眠"，首次访问需要30秒唤醒
- 15分钟无访问会自动休眠
- 可以用定时器每10分钟访问一次保持活跃

### Q: 如何更新代码？
**A: 自动部署：**
1. 修改本地代码
2. git add . && git commit -m "更新"
3. git push
4. Render会自动重新部署

## 🎯 保持应用活跃的技巧

### 方法1：定时访问
设置手机提醒，每天访问几次

### 方法2：监控服务 (推荐)
使用 UptimeRobot 免费监控：
1. 注册 https://uptimerobot.com
2. 添加你的网站URL
3. 设置5分钟检查一次
4. 应用永远不会休眠

### 方法3：升级付费版
Render付费版每月$7，永不休眠

## 🎉 部署成功！

恭喜！你现在有了一个：
- 📱 完全免费的基金估值Web应用
- 🌐 可以全球访问的专属域名
- ⚡ 自动更新部署的现代化服务
- 🔒 HTTPS安全连接

**现在就可以随时随地用手机查看基金估值了！** 🎯

---

💡 **小贴士**: 把域名保存到收藏夹，或添加到手机桌面，使用更方便！