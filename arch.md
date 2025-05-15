# Candidate Screening and Matching System 系统架构图

```mermaid
graph TD
    subgraph 用户浏览器
        A1[Web前端]
        A2[静态资源]
    end

    subgraph Flask后端
        B1[app.py 主入口路由]
        B2[templates Jinja2模板]
        B3[utils.py 工具函数]
        B4[Flask-Login 用户认证]
        B5[Flask-SQLAlchemy ORM]
        B6[AI分析队列 多线程]
        B7[Key Vault集成]
        B8[Azure Blob集成]
        B9[OpenAI分析打分]
    end

    subgraph 数据存储
        C1[SQLite resume_matcher.db]
        C2[Azure MySQL 可选]
        C3[Azure Blob 简历文件]
        C4[Azure Key Vault API密钥]
    end

    subgraph OpenAI云服务
        E1[OpenAI GPT API]
    end

    subgraph CI/CD
        D1[GitHub Actions]
        D2[.github workflows azure-vm-deploy.yml]
        D3[Azure VM Linux主机]
    end

    %% 用户与前端
    A1 -- "HTTP请求" --> B1
    A2 -.-> A1

    %% 前端模板
    B1 -- "渲染" --> B2

    %% 认证与ORM
    B1 -- "用户认证" --> B4
    B1 -- "数据库操作" --> B5

    %% 工具与AI
    B1 -- "调用" --> B3
    B1 -- "AI分析任务" --> B6

    %% Key Vault Blob
    B1 -- "API密钥获取" --> B7
    B1 -- "简历上传" --> B8

    %% 数据库
    B5 -- "ORM" --> C1
    B5 -- "ORM可选" --> C2

    %% Key Vault Blob
    B7 -- "读取密钥" --> C4
    B8 -- "上传下载" --> C3

    %% AI分析
    B6 -- "调用OpenAI分析简历打分" --> B9
    B9 -- "API请求分析与评分" --> E1

    %% CI CD
    D1 -- "推送触发" --> D2
    D2 -- "SSH部署" --> D3
    D3 -- "运行Flask服务" --> B1
    D2 -- "chown数据库文件" --> C1

    %% 其它
    D3 -- "持久化resume_matcher.db" --> C1

    %% 说明
    classDef cloud fill:#e0f7fa,stroke:#0097a7,stroke-width:2px;
    class C2,C3,C4,E1 cloud;
```

---

**说明：**
- 用户通过浏览器访问 Flask 后端，前端页面由 Jinja2 模板渲染，静态资源由 static 提供。
- Flask 后端负责路由、业务逻辑、用户认证、数据库操作、AI分析队列、多线程、与 Azure Key Vault 及 Blob 的集成。
- AI分析队列会调用OpenAI GPT API进行简历内容分析和自动评分，分析结果回写数据库。
- 数据存储支持本地 SQLite 和 Azure MySQL，简历文件可上传至 Azure Blob，API Key 等敏感信息集中存储于 Azure Key Vault。
- CI CD 采用 GitHub Actions 自动部署，推送到 main 分支后自动构建、上传、重启服务，并确保 resume_matcher.db 文件属主为 bingo。
- 主要依赖见 requirements.txt，包括 Flask、SQLAlchemy、Login、openai、PyPDF2、python-docx、azure 相关库等。 