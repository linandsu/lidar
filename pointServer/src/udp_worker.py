import socket
import struct
import multiprocessing
import numpy as np
import time
from typing import Any
from lidar_parser import LSS3_Parser_UTC

def udp_parsing_worker(queue: Any, port: int, lidar_id: str, running_event: Any):
    """
    负责实时监听 UDP 端口，解析数据，并推送到队列
    """
    print(f"[Worker-{lidar_id}] 启动监听，绑定端口: {port}")
    
    # 1. 创建 UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024) 
    
    try:
        sock.bind(("0.0.0.0", port))
        sock.settimeout(0.5) # 0.5s 超时，方便响应退出信号
    except Exception as e:
        print(f"[Worker-{lidar_id}] ❌ 端口绑定失败: {e}")
        return

    # 2. 解析器初始化
    parser = LSS3_Parser_UTC()
    frame_chunks = []
    total_points = 0
    frame_id_counter = 0

    # 3. 循环接收
    while running_event.is_set():
        try:
            data, _ = sock.recvfrom(1500) # 接收数据
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[Worker-{lidar_id}] Socket Error: {e}")
            continue

        # 解析
        points_chunk, is_new_frame, _ = parser.parse_packet_batch(data)

        if points_chunk is not None:
            frame_chunks.append(points_chunk)
            total_points += len(points_chunk)

        # 帧结束处理
        if is_new_frame and total_points > 0:
            full_frame_np = np.vstack(frame_chunks)
            point_count = len(full_frame_np)

            # 打包协议: [Frame ID (4B)] [Point Count (4B)] [Data (N*16B)]
            header = struct.pack('<II', frame_id_counter, point_count)
            body = full_frame_np.astype(np.float32).tobytes()
            
            # 写入队列 (如果满了则丢弃旧帧，保证实时性)
            if not queue.full():
                queue.put(header + body)
            
            # 清理状态
            frame_chunks = []
            total_points = 0
            frame_id_counter += 1

    sock.close()
    print(f"[Worker-{lidar_id}] 进程已停止")