<template>
  <div class="player-container">
    <div ref="canvasContainer" class="canvas-view"></div>
    <div v-if="statusMsg" class="status-overlay">{{ statusMsg }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { db, clearDB } from '../utils/db';

// 接收外部传入的 WS 地址
const props = defineProps({
  wsUrl: { type: String, required: true }
});

const canvasContainer = ref(null);
const statusMsg = ref("正在连接...");
let scene, camera, renderer, points, geometry, controls, socket;
let workers = [];
let isRunning = true;

// --- 基础 Three.js 初始化 (精简版) ---
const initThree = () => {
  scene = new THREE.Scene();
  // 添加网格辅助以便观察
  scene.add(new THREE.GridHelper(100, 10));
  
  camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 20, 30);
  
  renderer = new THREE.WebGLRenderer();
  renderer.setSize(window.innerWidth, window.innerHeight);
  canvasContainer.value.appendChild(renderer.domElement);
  
  controls = new OrbitControls(camera, renderer.domElement);

  // 初始化点云粒子系统
  geometry = new THREE.BufferGeometry();
  // 预分配 20万点 buffer
  const maxPoints = 200000;
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(maxPoints * 3), 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(maxPoints * 3), 3));
  
  const material = new THREE.PointsMaterial({ size: 0.15, vertexColors: true });
  points = new THREE.Points(geometry, material);
  scene.add(points);

  const animate = () => {
    if (!isRunning) return;
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  };
  animate();
};

// --- WebSocket 逻辑 ---
const connectWS = () => {
  if (socket) socket.close();
  
  socket = new WebSocket(props.wsUrl);
  socket.binaryType = 'arraybuffer';
  
  socket.onopen = () => { statusMsg.value = ""; };
  socket.onclose = () => { statusMsg.value = "连接已断开"; };
  socket.onerror = () => { statusMsg.value = "连接错误"; };

  socket.onmessage = (event) => {
    // 简化处理：直接解析并渲染最新一帧（舍弃DB缓冲以降低延迟）
    processFrameDirectly(event.data);
  };
};

const processFrameDirectly = (buffer) => {
  const view = new DataView(buffer);
  const pointCount = view.getUint32(4, true); // Offset 4 is count
  const floatData = new Float32Array(buffer, 8); // Offset 8 is data
  
  // 更新 BufferGeometry
  // 注意：这里为了演示直接在主线程更新，生产环境建议保持原有的 Worker 架构
  const positions = geometry.attributes.position.array;
  const colors = geometry.attributes.color.array;
  
  let j = 0;
  for (let i = 0; i < pointCount; i++) {
    const x = floatData[i * 4 + 0];
    const y = floatData[i * 4 + 1];
    const z = floatData[i * 4 + 2];
    const intens = floatData[i * 4 + 3];

    positions[j] = x;
    positions[j+1] = z; // 交换 Y/Z 轴以适应 Three.js 坐标系
    positions[j+2] = y;
    
    // 简单着色：根据强度
    const val = Math.min(intens / 255.0, 1.0);
    colors[j] = val;
    colors[j+1] = 1.0 - val;
    colors[j+2] = 0.0;
    
    j += 3;
  }
  
  geometry.setDrawRange(0, pointCount);
  geometry.attributes.position.needsUpdate = true;
  geometry.attributes.color.needsUpdate = true;
};

onMounted(() => {
  initThree();
  connectWS();
});

onUnmounted(() => {
  isRunning = false;
  if (socket) socket.close();
  // 清理 Three.js 资源
  geometry?.dispose();
  renderer?.dispose();
});
</script>

<style scoped>
.player-container { width: 100%; height: 100%; position: relative; background: black; }
.status-overlay {
  position: absolute; top: 10px; left: 10px;
  color: yellow; background: rgba(0,0,0,0.5); padding: 5px;
}
</style>