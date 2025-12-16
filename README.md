# contact-gen-be

合同模版生成后端

                  ┌-------------------------------┐
                  │  浏览器 (PC / Mobile)          │
                  │  Vue3 + Vite + Axios          │
                  └------------┬------------------┘
                               │  HTTPS / WebSocket
                  ┌------------┴------------------┐
                  │  Nginx (反向代理 + 静态托管)   │
                  │  80/443 端口                  │
                  └------------┬------------------┘
                               │  uWSGI 协议
                  ┌------------┴------------------┐
                  │  Django 3.2+ (虚拟环境)       │
                  │  ┌-------------------------┐ │
                  │  │  Django REST Framework  │ │
                  │  │  JWT / Session Auth     │ │
                  │  │  CORS 已开启             │ │
                  │  └------------┬------------┘ │
                  │               │ ORM          │
                  │  ┌------------┴------------┐ │
                  │  │     Django-Sqlite3       │ │
                  │  │  (db.sqlite3 单文件)     │ │
                  │  └--------------------------┘ │
                  └-------------------------------┘

python版本：
sqlite版本：
Nginx版本：

## 后端模块

### 用户登陆

### 处理用户输入文本

### 生成合同模版

### 爬虫处理合同

### 输出文档

### 大语言模型调用
模型以及版本选择：doubao-seed-1-6-251015

### 激活虚拟环境
source venv/bin/activate

### 下载依赖包
conda install -c conda-forge fastapi uvicorn transformers pytorch openai

### 运行
uvicorn model_api.main:app --reload

### 查看网页，使用大模型
http://127.0.0.1:8000/docs