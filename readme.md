# Bingo HR - Bingo-AI-HR

## 项目简介
本项目基于Flask开发，实现简历的批量上传、管理（下载、删除、批量删除、全选）和类型校验，后续可扩展智能评分。

## 功能特性
- 支持批量上传简历（仅限pdf、word、excel、图片、markdown），word(docx)和pdf简历内容自动解析后用于AI分析
- 简历文件管理：列表、下载、单个删除、批量删除、全选
- 前后端均校验文件类型，禁止其它类型上传
- 招聘需求管理：可以创建、编辑、查看和删除招聘需求，包含职位名称、要求和描述
- AI辅助分析简历，自动提取内容并进行匹配度评分

## 安装与运行
1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 启动服务：
   ```bash
   python app.py
   ```
3. 访问页面：
   - 在浏览器中打开 http://127.0.0.1:5000

## 目录结构
```
resume_matcher/
├── app.py
├── requirements.txt
├── templates/
│   └── index.html
├── uploads/
├── utils.py
├── changelog.md
└── readme.md
```

## 注意事项
- 请勿上传敏感信息，API密钥等请勿公开。
- 仅供学习与内部评估使用。
- AI分析worker线程已自动修正为只在主进程中启动，避免多进程/多线程重复或未启动问题。
- 日志输出已修正，确保AI分析worker日志能实时显示在终端。
- 依赖PyPDF2库用于PDF简历内容解析，未安装时AI分析会提示需安装依赖。

## 数据库切换（SQLite/Azure MySQL）

系统支持本地SQLite和Azure Database for MySQL两种数据库。

- 默认使用本地SQLite。
- 管理员可在"系统设置"页面切换数据库类型（sqlite/mysql），并配置MySQL连接参数（用户名、密码、主机、数据库名、端口）。
- 切换数据库类型后，需重启服务后生效。
- MySQL连接需安装pymysql依赖（已自动包含在requirements.txt中）。

## 版本历史（当前版本：0.4.13）
详见 [changelog.md](./changelog.md)

## 自动化部署（GitHub Actions -> Azure VM）
本项目已集成GitHub Actions自动化部署工作流（.github/workflows/azure-vm-deploy.yml），推送到main分支后会自动：
1. 安装依赖并检查代码。
2. 通过SCP将全部代码上传到Azure VM（连接信息通过GitHub Secrets配置，采用SSH密钥方式）。
3. 远程SSH到VM，自动重启Flask服务。

> 你需要在GitHub仓库的Settings-Secrets中配置如下变量：
> - AZURE_VM_HOST
> - AZURE_VM_USER
> - AZURE_VM_KEY（SSH私钥内容，建议使用专用部署密钥）
> - AZURE_VM_PORT（如为22可省略）
> - RESET_DB（可选，首次部署时设为true可自动重建数据库，后续建议设为false或删除）

如需自定义部署路径或命令，请修改azure-vm-deploy.yml中的相关字段。

## .gitignore说明
本项目已添加 `.gitignore` 文件，自动忽略常见的Python缓存、虚拟环境、日志、数据库、编辑器配置等本地和部署相关文件，确保代码仓库整洁，仅跟踪必要的源代码和配置文件。

## 如何触发自动化部署
只需将代码推送（push）到 main 分支，GitHub Actions 会自动执行自动化部署流程，无需手动干预。

例如：
```bash
git add .
git commit -m "更新说明"
git push origin main
```
推送后可在GitHub仓库的Actions页面查看部署进度和日志。 

## 版本说明

当前版本：0.4.13

## 启动说明

默认启动命令：

```
python app.py
```

Flask服务默认监听端口为5001（原为5000）。

## MySQL优先配置

你可以在项目根目录下新建`mysql.env`文件，内容如下：

```
MYSQL_USER=xxx
MYSQL_PASSWORD=xxx
MYSQL_HOST=xxx.mysql.database.azure.com
MYSQL_DB=xxx
MYSQL_PORT=3306
```

系统启动时会优先尝试连接MySQL，若失败则自动回退到本地sqlite。

## Azure Key Vault 支持

系统支持通过Azure Key Vault集中管理OpenAI Key。
- 管理员可在"系统设置"页面启用Azure Key Vault，并填写Key Vault名称及机密名称。
- 启用后，系统将优先从Key Vault获取OpenAI Key，未启用时使用本地配置。
- 需确保服务器具备访问Key Vault的权限（如已配置Azure身份认证环境）。
- 如果启用Azure Key Vault，则API Key字段可留空。

fixme