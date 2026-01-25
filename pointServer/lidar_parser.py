import numpy as np
import struct
from datetime import datetime

class LSS3_Parser_UTC:
    def __init__(self):
        # LS-S3 参数配置
        self.DEAD_ZONE_OFFSET = 6.37
        self.MIRROR_OFF_ANGLES = np.array([1.5, -0.5, 0.5, -1.5], dtype=np.float32)
        
        self.DIST_ACC = 0.001
        self.H_ANGLE_ACC = 0.01
        self.V_ANGLE_ACC = 0.0025
        self.DEG2RAD = np.pi / 180.0
        
        # 预计算常量
        self.rad_30 = 30 * self.DEG2RAD
        self.rad_60 = 60 * self.DEG2RAD
        self.cos_30 = np.cos(self.rad_30)
        self.sin_30 = np.sin(self.rad_30)
        self.sin_60 = np.sin(self.rad_60)

    def parse_packet_batch(self, payload):
        # 1. 长度校验
        if len(payload) < 1206: return None, False, 0.0
        
        data_part = payload[:1192]
        tail_part = payload[1192:]

        # --- [A] 解析尾部 UTC 时间戳 ---
        pkt_timestamp = 0.0
        try:
            t_bytes = tail_part[2:8]
            year = 2000 + t_bytes[0]
            month, day, hour, minute, second = t_bytes[1], t_bytes[2], t_bytes[3], t_bytes[4], t_bytes[5]
            ns_bytes = tail_part[8:12]
            nanoseconds = struct.unpack('>I', ns_bytes)[0]
            dt = datetime(year, month, day, hour, minute, second)
            pkt_timestamp = dt.timestamp() + (nanoseconds / 1e9)
        except Exception:
            pass

        # --- [B] 解析点云 ---
        raw_data = np.frombuffer(data_part, dtype=np.uint8).reshape(-1, 8)
        
        header_mask = (raw_data[:, 0] == 0xFF) & (raw_data[:, 1] == 0xAA) & \
                      (raw_data[:, 2] == 0xBB) & (raw_data[:, 3] == 0xCC) & \
                      (raw_data[:, 4] == 0xDD)
        is_new_frame = np.any(header_mask)
        valid_data = raw_data[~header_mask]
        
        if len(valid_data) == 0: 
            return None, is_new_frame, pkt_timestamp

        angle_h_raw = (valid_data[:, 0].astype(np.uint16) << 8) | valid_data[:, 1]
        angle_h_raw = angle_h_raw.astype(np.float32)
        angle_h_raw[angle_h_raw > 32767] -= 65536
        f_angle_h = angle_h_raw * self.H_ANGLE_ACC

        t_temp_angle = valid_data[:, 2]
        channel_id = t_temp_angle >> 6
        t_symbol = (t_temp_angle >> 5) & 0x01
        
        angle_v_val = (valid_data[:, 2].astype(np.uint16) << 8) | valid_data[:, 3]
        angle_v_final = np.zeros_like(angle_v_val, dtype=np.float32)
        angle_v_neg_mask = (t_symbol == 1)
        
        neg_v = angle_v_val[angle_v_neg_mask] | 0xC000
        neg_v = neg_v.astype(np.float32)
        neg_v[neg_v > 32767] -= 65536
        angle_v_final[angle_v_neg_mask] = neg_v
        
        pos_mask = ~angle_v_neg_mask
        pos_high = t_temp_angle[pos_mask] & 0x3F
        angle_v_final[pos_mask] = ((pos_high.astype(np.uint16) << 8) | valid_data[pos_mask, 3]).astype(np.float32)
        f_angle_v = angle_v_final * self.V_ANGLE_ACC

        dist_raw = (valid_data[:, 4].astype(np.uint32) << 16) | \
                   (valid_data[:, 5].astype(np.uint32) << 8) | \
                   valid_data[:, 6].astype(np.uint32)
        t_distance = dist_raw.astype(np.float32) * self.DIST_ACC
        intensity = valid_data[:, 7].astype(np.float32)

        idx = channel_id % 4
        f_put_mirror_off_angle = self.MIRROR_OFF_ANGLES[idx]
        
        rad_mirror = f_put_mirror_off_angle * self.DEG2RAD
        rad_galva = (f_angle_v + self.DEAD_ZONE_OFFSET) * self.DEG2RAD
        rad_h = f_angle_h * self.DEG2RAD
        
        cos_mirror = np.cos(rad_mirror)
        sin_mirror = np.sin(rad_mirror)
        cos_galva = np.cos(rad_galva)
        sin_galva = np.sin(rad_galva)
        cos_h = np.cos(rad_h)
        sin_h = np.sin(rad_h)

        f_angle_r0 = self.cos_30 * cos_mirror * cos_galva - sin_galva * sin_mirror
        f_sin_v_angle = 2 * f_angle_r0 * sin_galva + sin_mirror
        val_v = 1 - f_sin_v_angle**2
        val_v[val_v < 0] = 0
        f_cos_v_angle = np.sqrt(val_v)
        denom = f_cos_v_angle.copy()
        denom[denom == 0] = 1.0
        f_sin_cite = (2 * f_angle_r0 * cos_galva * self.sin_30 - cos_mirror * self.sin_60) / denom
        val_c = 1 - f_sin_cite**2
        val_c[val_c < 0] = 0
        f_cos_cite = np.sqrt(val_c)
        f_sin_cite_h = sin_h * f_cos_cite + cos_h * f_sin_cite
        f_cos_cite_h = cos_h * f_cos_cite - sin_h * f_sin_cite
        
        x = t_distance * f_cos_v_angle * f_sin_cite_h
        y = t_distance * f_cos_v_angle * f_cos_cite_h
        z = t_distance * f_sin_v_angle

        points = np.stack((x, y, z, intensity), axis=1)
        mask_valid = (np.abs(x) > 0.1) | (np.abs(y) > 0.1) | (np.abs(z) > 0.1)
        
        return points[mask_valid], is_new_frame, pkt_timestamp