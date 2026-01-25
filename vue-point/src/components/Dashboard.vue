<template>
  <div class="dashboard-layout">
    <div class="sidebar">
      <h2>📡 雷达监控中心</h2>
      
      <div class="control-section">
        <label>选择雷达设备:</label>
        <select v-model="selectedId" @change="handleLidarChange" :disabled="isStreaming">
          <option v-for="(cfg, id) in lidars" :key="id" :value="id">
            雷达 #{{ id }} (端口 {{ cfg.port }})
          </option>
        </select>
        <p class="ip-info" v-if="currentLidar">IP: {{ currentLidar.ip }}</p>
      </div>

      <div class="control-section">
        <button class="btn test-btn" @click="testConnection" :disabled="testing || isStreaming">
          🛠 UDP 信号检测
        </button>
        <div v-if="testResult" :class="['result-box', testResult.status]">
          {{ testResult.msg }}
        </div>
      </div>

      <div class="control-section main-action">
        <button 
          class="btn stream-btn" 
          :class="{ 'stop-btn': isStreaming }"
          @click="toggleStream"
        >
          {{ isStreaming ? '⏹ 停止监控' : '▶ 开始实时监控' }}
        </button>
      </div>
    </div>

    <div class="viewer-area">
      <PointCloud 
        v-if="isStreaming" 
        :key="selectedId" 
        :ws-url="wsUrl" 
      />
      
      <div v-else class="placeholder">
        <div class="icon">🛰</div>
        <p>请在左侧选择雷达并点击“开始实时监控”</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import PointCloud from './PointCloud.vue';

const lidars = ref({});
const selectedId = ref("109");
const isStreaming = ref(false);
const testing = ref(false);
const testResult = ref(null);

// 计算属性
const currentLidar = computed(() => lidars.value[selectedId.value]);
const wsUrl = computed(() => `ws://${location.hostname}:8055/ws/${selectedId.value}`);

// 获取配置
onMounted(async () => {
  try {
    const res = await fetch(`http://${location.hostname}:8055/api/lidars`);
    lidars.value = await res.json();
  } catch (e) {
    console.error("无法获取雷达配置", e);
  }
});

const handleLidarChange = () => {
  testResult.value = null;
};

// 测试 UDP 连接
const testConnection = async () => {
  if (!currentLidar.value) return;
  
  testing.value = true;
  testResult.value = { status: 'info', msg: '正在侦听 UDP 端口...' };
  
  try {
    const port = currentLidar.value.port;
    const res = await fetch(`http://${location.hostname}:8055/api/test_udp/${port}`);
    const data = await res.json();
    
    if (data.status === 'ok') {
      testResult.value = { status: 'success', msg: '✅ 连接正常: ' + data.msg };
    } else {
      testResult.value = { status: 'error', msg: '❌ ' + data.msg };
    }
  } catch (e) {
    testResult.value = { status: 'error', msg: '请求失败' };
  } finally {
    testing.value = false;
  }
};

const toggleStream = () => {
  if (!isStreaming.value) {
    // Start
    isStreaming.value = true;
  } else {
    // Stop
    isStreaming.value = false;
  }
};
</script>

<style scoped>
.dashboard-layout { display: flex; height: 100vh; font-family: sans-serif; }

/* Sidebar Styles */
.sidebar {
  width: 320px;
  background: #1e1e24;
  color: #fff;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: 2px 0 10px rgba(0,0,0,0.5);
  z-index: 10;
}

h2 { margin: 0 0 10px 0; font-size: 1.2rem; border-bottom: 1px solid #444; padding-bottom: 10px; }

.control-section { background: #2b2b36; padding: 15px; border-radius: 8px; }
label { display: block; margin-bottom: 8px; color: #aaa; font-size: 0.9rem; }
select { width: 100%; padding: 8px; background: #333; color: white; border: 1px solid #555; border-radius: 4px; }
.ip-info { margin-top: 5px; font-size: 0.8rem; color: #666; font-family: monospace; }

.btn { width: 100%; padding: 10px; cursor: pointer; border: none; border-radius: 4px; font-weight: bold; transition: 0.2s; }
.test-btn { background: #4a4e69; color: white; }
.test-btn:hover { background: #5c6185; }
.test-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.stream-btn { background: #2a9d8f; color: white; font-size: 1.1rem; padding: 15px; }
.stream-btn:hover { background: #21867a; }
.stop-btn { background: #e63946; }
.stop-btn:hover { background: #d62828; }

.result-box { margin-top: 10px; font-size: 0.85rem; padding: 8px; border-radius: 4px; }
.result-box.success { background: rgba(42, 157, 143, 0.2); color: #2a9d8f; border: 1px solid #2a9d8f; }
.result-box.error { background: rgba(230, 57, 70, 0.2); color: #e63946; border: 1px solid #e63946; }
.result-box.info { color: #aaa; }

/* Viewer Styles */
.viewer-area { flex: 1; background: #000; position: relative; }
.placeholder { 
  height: 100%; display: flex; flex-direction: column; 
  align-items: center; justify-content: center; color: #444; 
}
.placeholder .icon { font-size: 4rem; margin-bottom: 20px; }
</style>