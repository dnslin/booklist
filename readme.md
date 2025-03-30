# 小说榜单抓取和API服务系统

## 项目概述

小说榜单抓取和API服务系统是一个用于自动获取、整合和提供中文网络小说平台榜单数据的工具。该系统支持从多个主流小说网站（如刺猬猫、起点中文网、番茄小说）爬取最新的榜单数据，保存到本地数据库，并通过RESTful API提供数据访问服务。

## 功能特点

- **多平台数据采集**：支持从刺猬猫、起点中文网、番茄小说等多个小说平台获取榜单数据
- **多种榜单类型**：支持各平台的多种榜单类型，如周点击榜、月票榜、新书榜、热门榜等
- **自动化数据更新**：通过运行主程序可自动更新所有平台最新榜单数据
- **统一数据存储**：所有数据统一存储在SQLite数据库，便于管理和查询
- **RESTful API服务**：提供完整的RESTful API，支持灵活查询各平台榜单数据
- **可扩展架构**：采用适配器模式设计，易于扩展支持新的小说平台

## 系统架构

系统主要由以下几个部分组成：

1. **数据采集模块**：负责从各小说平台获取榜单数据
   - `ciwei.py`: 刺猬猫网站数据爬取
   - `qidian.py`: 起点中文网数据爬取
   - `fanqie.py`: 番茄小说数据爬取

2. **数据处理与存储模块**：负责数据处理和数据库操作
   - `booklist_db.py`: 数据库管理类，处理数据库连接、表结构创建和数据存储等

3. **API服务模块**：提供RESTful API接口
   - `api.py`: FastAPI应用，提供各种数据查询接口

## 文件结构

```
.
├── api.py                 # API服务实现
├── booklist_db.py         # 数据库管理类
├── booklist.db            # SQLite数据库文件
├── ciwei.py               # 刺猬猫数据爬取模块
├── cookie.json            # 网站Cookie配置
├── fanqie.py              # 番茄小说数据爬取模块
├── qidian.py              # 起点中文网数据爬取模块
├── .gitignore             # Git忽略文件配置
└── readme.md              # 项目说明文档
```

## 安装与配置

### 依赖安装

```bash
pip install requests lxml bs4 fastapi uvicorn
```

### 配置文件

创建或更新 `cookie.json` 文件，用于配置访问某些需要登录的网站：

```json
{
  "cookie": "你的cookie字符串"
}
```

## 使用方法

### 数据采集

运行以下命令抓取所有平台最新榜单数据：

```bash
python booklist_db.py
```

### 启动API服务

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

或者直接运行：

```bash
python api.py
```

## API文档

启动API服务后，可通过以下地址访问自动生成的API文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 主要API接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 获取API服务基本信息 |
| `/api/sites` | GET | 获取所有支持的站点信息 |
| `/api/rankings` | GET | 获取当日所有平台的榜单数据 |
| `/api/rankings/{site_code}` | GET | 获取指定站点的所有榜单数据 |
| `/api/rankings/{site_code}/{ranking_type}` | GET | 获取指定站点的指定榜单数据 |

### 查询参数

- `date`: 可选参数，指定获取哪一天的榜单数据，格式为YYYY-MM-DD，默认为今天

### 示例请求

```
GET /api/rankings/qidian/month_ticket?date=2025-03-30
```

## 数据库结构

系统使用SQLite数据库存储数据，主要包含以下表：

1. **sites**: 站点信息表
2. **ranking_types**: 榜单类型表
3. **rankings**: 榜单数据表
4. **fetch_logs**: 数据抓取日志表

## 技术栈

- **Python**: 核心开发语言
- **FastAPI**: API框架
- **SQLite**: 数据存储
- **requests/lxml/BeautifulSoup**: 数据爬取和解析
- **uvicorn**: ASGI服务器

## 扩展支持新平台

要添加对新小说平台的支持，需要：

1. 创建新的爬虫模块（参考现有的`ciwei.py`、`qidian.py`或`fanqie.py`）
2. 在`booklist_db.py`中的`SiteAdapter`类基础上实现新的适配器类
3. 在`init_preset_sites`方法中添加新站点信息
4. 在`get_adapter_for_site`函数中添加新适配器的映射

## 许可证

本项目仅用于学习和研究，请勿用于商业用途。

## 声明

本项目仅用于学习和个人使用，所有数据均来自公开网站。请遵守相关网站的使用条款和规定，合理使用API和爬取的数据。
