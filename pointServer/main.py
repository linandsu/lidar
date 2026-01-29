import multiprocessing
import uvicorn
import asyncio
import socket
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from udp_worker import udp_parsing_worker

# ================= 配置区 =================
# 生成 18 台雷达配置 (109~126)
LIDAR_CONFIG = {}
for i in range(109, 127):
    lid_id = str(i)
    LIDAR_CONFIG[lid_id] = {
        "id": lid_id,
        "ip": f"192.168.50.{i}",
        "port": 2309 + (i - 109)
    }

print(f"Loaded {len(LIDAR_CONFIG)} Lidar configs.")

# ================= 进程管理 =================
class ProcessManager:
    def __init__(self):
        self.workers = {} # {lidar_id: {process, queue, event}}

    def start_lidar(self, lidar_id):
        if lidar_id in self.workers:
            return self.workers[lidar_id]["queue"]
        
        cfg = LIDAR_CONFIG.get(lidar_id)
        if not cfg: return None

        print(f"[Manager] 启动雷达 {lidar_id} (Port {cfg['port']})")
        
        queue = multiprocessing.Queue(maxsize=5) # 小队列，防积压
        event = multiprocessing.Event()
        event.set()
        
        p = multiprocessing.Process(
            target=udp_parsing_worker,
            args=(queue, cfg['port'], lidar_id, event),
            daemon=True
        )
        p.start()
        
        self.workers[lidar_id] = {"process": p, "queue": queue, "event": event}
        return queue

    def stop_lidar(self, lidar_id):
        # 使用 pop 安全移除，防止 ws 断开和 shutdown 同时调用引发 KeyError 或二次操作
        worker = self.workers.pop(lidar_id, None)
        
        if worker:
            print(f"[Manager] 正在停止进程: {lidar_id}")
            worker["event"].clear()
            # 设置超时，防止 join 卡死
            worker["process"].join(timeout=1.0)
            if worker["process"].is_alive():
                print(f"[Manager] 超时强制终止: {lidar_id}")
                worker["process"].terminate()
            else:
                print(f"[Manager] 进程正常退出: {lidar_id}")

    def stop_all(self):
        for lid in list(self.workers.keys()):
            self.stop_lidar(lid)

manager = ProcessManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    print("Shutting down workers...")
    manager.stop_all()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= API 接口 =================

@app.get("/api/lidars")
async def get_lidars():
    return LIDAR_CONFIG

@app.get("/api/test_udp/{port}")
async def test_udp(port: int):
    """检测端口是否有 UDP 数据流入"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        sock.bind(("0.0.0.0", port))
        data, addr = sock.recvfrom(1024)
        sock.close()
        return {"status": "ok", "msg": f"收到 {len(data)} 字节来自 {addr}"}
    except socket.timeout:
        return {"status": "fail", "msg": "超时：未收到数据"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

@app.websocket("/ws/{lidar_id}")
async def ws_endpoint(websocket: WebSocket, lidar_id: str):
    await websocket.accept()
    
    # 校验配置
    if lidar_id not in LIDAR_CONFIG:
        await websocket.close()
        return

    print(f"[WS] 前端连接雷达: {lidar_id}，正在启动子进程...")
    
    # 1. 启动子进程 (Worker)
    queue = manager.start_lidar(lidar_id)
    
    try:
        while True:
            # 从队列取数据发送给前端
            if not queue.empty():
                data = queue.get()
                await websocket.send_bytes(data)
                # 极短休眠，防止 CPU 空转死锁
                await asyncio.sleep(0.001)
            else:
                # 队列为空时多睡一会，降低 CPU 占用
                await asyncio.sleep(0.01)

    except WebSocketDisconnect:
        print(f"[WS] 前端主动断开连接: {lidar_id}")
        
    except Exception as e:
        print(f"[WS] 连接发生异常: {e}")
        
    finally:
        print(f"[Resource] 正在清理雷达 {lidar_id} 的后台进程...")
        # 将阻塞的进程 Join 操作放入线程池，避免阻塞 FastAPI 事件循环
        await asyncio.to_thread(manager.stop_lidar, lidar_id)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(app, host="0.0.0.0", port=8055)