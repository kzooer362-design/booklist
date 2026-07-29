# 书单投票 - 中国版 (booklist-n)

适配腾讯云 SCF Serverless 部署的版本。

## 目录结构

```
booklist-n/
├── static/              ← 前端静态文件（托管到 CloudBase）
│   ├── index.html       ← 你需要从 booklist-C 复制
│   ├── app.js           ← 你需要从 booklist-C 复制
│   └── style.css        ← 你需要从 booklist-C 复制
├── scf/                 ← SCF 云函数代码
│   ├── index.py         ← Flask SCF 入口
│   ├── requirements.txt ← Python 依赖
│   └── serverless.json  ← SCF 配置
├── cloudbaserc.json     ← CloudBase 部署配置
└── .gitignore
```

## 部署到腾讯云 CloudBase

### 1. 前置条件

- 已注册腾讯云账号并完成实名认证
- 已开通云开发 CloudBase（https://console.cloud.tencent.com/tcb）
- 已安装 Node.js 和 CloudBase CLI：
  ```bash
  npm install -g @cloudbase/cli
  tcb login
  ```

### 2. 复制前端文件

从 `booklist-C` 复制前端文件到 `static/`：

```powershell
Copy-Item D:\booklist-C\index.html D:\booklist-n\static\
Copy-Item D:\booklist-C\app.js D:\booklist-n\static\
Copy-Item D:\booklist-C\style.css D:\booklist-n\static\
```

### 3. 初始化并部署

```powershell
cd D:\booklist-n

# 初始化 CloudBase 项目
tcb init

# 设置环境 ID（在 CloudBase 控制台查看）
tcb env:init -e 你的环境ID

# 部署全部资源
tcb deploy
```

### 4. 获取访问地址

部署完成后，CloudBase 会提供：
- 前端静态网站地址：`https://xxx.booklist-cn.service.tcloudbase.com`
- 后端 API 地址：通过 SCF API 网关暴露

### 5. 配置前端指向 SCF API

部署后需要修改 `static/app.js` 中的 API 地址，将 `backendApiUrl` 改为 SCF API 网关地址。

## 本地开发

```powershell
cd D:\booklist-n\scf
pip install -r requirements.txt
python index.py
```

访问 http://localhost:5000

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/search?q=书名 | 图书搜索 |
| GET | /api/cover?url=图片地址 | 封面代理 |
| GET | /api/health | 健康检查 |
