# Lidar Real-time Visualization System (激光雷达实时可视化系统)

这是一个基于 **FastAPI** 和 **Vue 3 + Three.js** 的全栈项目，用于实时接收、解析并可视化激光雷达（Lidar）的点云数据。

系统通过 UDP 协议接收雷达原始数据，在后端进行解析，并通过 WebSocket 实时推送到前端进行 3D 渲染。

## 📁 目录结构 (Project Structure)

```text
lidar-project/
├── pointserver/           # [Backend] Python FastAPI 后端
│   ├── main.py            # 启动入口 (Port: 8055)
│   ├── lidar_parser.py    # 雷达数据解析核心逻辑
│   ├── udp_worker.py      # UDP 多进程接收模块
│   └── requirements.txt   # Python 依赖清单
│
├── vue-point/             # [Frontend] Vue 3 前端
│   ├── src/               # 源代码
│   │   ├── components/    # 组件 (Dashboard, PointCloud)
│   │   └── ...
│   ├── vite.config.js     # Vite 配置
│   └── package.json       # Node.js 依赖清单
│
└── .gitignore             # Git 忽略配置
🛠️ 技术栈 (Tech Stack)
Backend (后端)
Language: Python 3.10+

Framework: FastAPI (ASGI)

Server: Uvicorn

Data Processing: NumPy, Multiprocessing (Shared Memory)

Protocol: UDP (Ingest), WebSocket (Stream)

Frontend (前端)
Framework: Vue 3 (Composition API)

Build Tool: Vite

3D Engine: Three.js

Optimization: ArrayBuffer / Float32Array (Zero-copy parsing)

🚀 本地开发指南 (Local Development)
1. 启动后端 (Backend)
确保你已安装 Python 3.10+。

Bash
# 1. 进入后端目录
cd pointserver

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 启动服务 (默认端口 8055)
python main.py
后端启动成功后，API 文档地址: http://localhost:8055/docs

2. 启动前端 (Frontend)
确保你已安装 Node.js (推荐 v16+)。

Bash
# 1. 打开一个新的终端窗口，进入前端目录
cd vue-point

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
前端启动通常位于: http://localhost:5173


⚙️ 配置说明 (Configuration)
端口配置
Backend API: 默认为 8055 (在 pointserver/main.py 中修改)。

UDP Listening: 默认监听端口范围 2309 - 2326 (对应雷达 ID 109-126)。

数据流逻辑
UDP Ingest: 后端监听特定 UDP 端口接收原始 Packet。

Parsing: 解析器将二进制数据转换为 XYZI 坐标。

Broadcast: 通过 WebSocket /ws/{lidar_id} 广播给前端。

Rendering: 前端通过 DataView 直接解析二进制流并在 Canvas 中绘制。
