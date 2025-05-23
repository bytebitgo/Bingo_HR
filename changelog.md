# Changelog

## [0.3.0] - 2025-03-09
### 新增
- 支持已上传简历的批量管理：全选、批量删除
- 前端支持多选、全选、批量操作
- 后端支持批量删除接口

## [0.2.0] - 2025-03-08
### 新增
- 支持批量上传简历（仅限pdf、word、excel、图片、markdown）
- 简历文件管理：列表、下载、删除
- 前后端均校验文件类型
- 新增uploads目录用于存储简历

## [0.1.0] - 2025-03-07
### 新增
- 项目初始化：
  - 添加Flask主程序(app.py)
  - 工具函数(utils.py)
  - 前端页面(templates/index.html)
  - 依赖文件(requirements.txt)

## [0.4.0] - 2025-03-10
### 修复
- 修正AI分析worker线程只在主进程中启动，避免多进程/多线程重复或未启动问题，提升系统稳定性。

## [0.4.1] - 2024-06-09
### Changed
- Flask服务监听端口由5000改为5001。

## [0.4.2] - 2024-06-09
### 新增
- 支持在mysql.env中配置Azure MySQL连接参数，系统启动时优先连接MySQL，失败时自动回退到sqlite。

## [0.4.4] - 2025-03-13
### 优化
- 新增PDF简历内容自动解析，AI分析前自动提取PDF文本并传递给Azure OpenAI。
- requirements.txt新增PyPDF2依赖，未安装时AI分析会在前端提示需安装依赖。

## [0.4.5] - 2025-03-14
### 改进
- 改进AI分析队列导出功能，现在包含所有状态的任务（包括已完成任务）
- 在导出CSV中添加分析时间列
- 优化导出文件的命名和内容组织

## [0.4.6] - 2025-03-15
### 新增
- 添加招聘需求管理功能：可以创建、编辑、查看和删除招聘需求
- 招聘需求包含职位名称、职位要求和职位描述三个主要字段
- 重构模板系统，添加base.html基础模板，所有页面统一继承
- 优化导航栏，添加更多功能入口

## [0.4.7] - 2025-03-16
### 改进
- 重新设计导航栏，使用Bootstrap Navbar组件
- 添加下拉菜单，将功能分组为招聘管理和系统管理
- 添加Bootstrap Icons图标，优化视觉体验
- 改进响应式设计，支持移动端显示

## [0.4.8] - 2025-03-17
### 修复
- 修复招聘需求功能数据库表缺失的问题
- 添加数据库迁移脚本，自动创建所需的数据库表
### 变更
- 全局将"简历管理"统一更名为"Candidate system"
- 全局将"Bingo-AI-HR"统一更名为"Candidate Screening and Matching System"

## [0.4.9] - 2025-03-18
### 修复
- 修复删除简历时的数据库约束错误
- 完善删除逻辑，确保同时删除关联的分析记录

## [0.4.10] - 2025-03-19
- 新增 .gitignore 文件，忽略常见 Python、Flask 项目及本地开发、部署相关的文件和目录。

## [0.4.11] - 2025-03-20
- 新增 GitHub Actions 自动化部署工作流（.github/workflows/azure-vm-deploy.yml），支持推送main分支后自动部署到Azure VM。

## [0.4.12] - 2025-03-21
### 新增
- 后台系统设置支持切换数据库类型（SQLite/ Azure Database for MySQL），可配置MySQL连接参数，切换后需重启服务生效。
- requirements.txt 新增 pymysql 依赖。

## [0.4.13] - 2024-06-10
### 新增
- 系统设置页面支持启用Azure Key Vault，支持从Key Vault中选择OpenAI Key。
- 后端支持优先从Key Vault获取OpenAI Key，兼容本地配置。
- requirements.txt 新增 azure-identity、azure-keyvault-secrets 依赖。
- 系统设置页面"Key Vault 名称+列出机密"按钮始终显示，支持实时列出机密。
- OpenAI Key机密名称、Azure Blob连接字符串、Azure Blob容器名均支持下拉选择Key Vault机密。
- 系统设置页面整体美化为现代化卡片风格，菜单与首页风格统一，分组清晰，主按钮带图标。
- Deployment Name 默认值由 gpt-4.5-preview 改为 gpt-40。
### 优化
- 默认API Key提示为"如果启用Azure Key Vault则无需设置"，并在readme中同步说明。
- 代码结构优化，所有设置项分组、留白、交互体验提升。

## [0.4.14] - 2024-06-10
### 优化
- 系统设置默认API Key提示为"如果启用Azure Key Vault则无需设置"。

## [0.4.15] - 2024-06-11
### 变更
- Flask服务监听端口由5001改为5000，相关文档和说明同步更新。

## [0.4.16] - 2025-03-18
### 修复
- 修复CI/CD脚本中多单词服务名未加引号导致的shell报错（如 Screening: command not found） 