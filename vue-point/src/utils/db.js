import Dexie from 'dexie';

export const db = new Dexie('PointCloudDB');
db.version(1).stores({
  frames: 'frameId' // 以 frameId 作为索引
});

// 清空数据库的辅助函数
export const clearDB = () => db.frames.clear();