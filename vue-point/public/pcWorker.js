self.onmessage = function (e) {
  const { frameId, pointCount, allData, config } = e.data;
  const positions = [];
  const colors = [];
 
  for (let i = 0; i < pointCount; i++) {
    const idx = i * 4;
    const x = allData[idx];
    const y = allData[idx + 1];
    const z = allData[idx + 2];
    const intensity = allData[idx + 3];

    // 1. 降采样 (确保 config.n 默认为 1 才是全量)
    if (config.mode === 'nth' && i % config.n !== 0) continue;

    // 2. 坐标系转换：对齐 Three.js (Y 向上)
    // 根据你的 lidar 安装方向，可能需要调整。
    // 如果想和 Open3D 一模一样，且你在 Three.js 里设置了 Z 向上，则保持 x,y,z
    positions.push(x, y, z); 

    // 3. 颜色映射：对齐 Python 脚本的黄色调
    const norm = Math.min(1.0, intensity / 255.0);
    colors.push(norm, norm, 0); // 红+绿 = 黄，与 Python 脚本一致
  }

  const posArray = new Float32Array(positions);
  const colArray = new Float32Array(colors);

  self.postMessage({
    frameId,
    positions: posArray,
    colors: colArray
  }, [posArray.buffer, colArray.buffer]);
};