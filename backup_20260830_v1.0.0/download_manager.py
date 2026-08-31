# -*- coding: utf-8 -*-
"""
VoxelLauncher - 下载任务管理器
记录所有下载任务的进度, 支持启动器关闭后恢复下载。
下载任务状态保存到 JSON 文件, 下次启动时在设置页面可以继续下载。
"""
import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Callable
import threading


# 下载任务状态
STATUS_PENDING = "pending"       # 等待中
STATUS_DOWNLOADING = "downloading"  # 下载中
STATUS_PAUSED = "paused"         # 已暂停(启动器关闭后自动变成这个)
STATUS_COMPLETED = "completed"   # 已完成
STATUS_FAILED = "failed"         # 失败
STATUS_CANCELLED = "cancelled"   # 已取消


class DownloadTask:
    """单个下载任务"""

    def __init__(self, task_id: str = None):
        self.task_id = task_id or str(uuid.uuid4())[:8]
        self.url = ""
        self.dest_path = ""       # 目标文件完整路径
        self.file_name = ""       # 文件名
        self.total_size = 0       # 总大小(字节)
        self.downloaded_size = 0  # 已下载大小(字节)
        self.status = STATUS_PENDING
        self.created_at = time.time()
        self.updated_at = time.time()
        self.completed_at = None
        self.error_msg = ""
        self.source = ""          # 来源: modrinth / curseforge / version / manual
        self.item_name = ""       # 物品名称(模组名/资源包名等)
        self.expected_sha1 = ""   # 预期的 SHA1(用于校验)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "url": self.url,
            "dest_path": self.dest_path,
            "file_name": self.file_name,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error_msg": self.error_msg,
            "source": self.source,
            "item_name": self.item_name,
            "expected_sha1": self.expected_sha1,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadTask":
        task = cls(data.get("task_id"))
        task.url = data.get("url", "")
        task.dest_path = data.get("dest_path", "")
        task.file_name = data.get("file_name", "")
        task.total_size = data.get("total_size", 0)
        task.downloaded_size = data.get("downloaded_size", 0)
        task.status = data.get("status", STATUS_PENDING)
        task.created_at = data.get("created_at", time.time())
        task.updated_at = data.get("updated_at", time.time())
        task.completed_at = data.get("completed_at")
        task.error_msg = data.get("error_msg", "")
        task.source = data.get("source", "")
        task.item_name = data.get("item_name", "")
        task.expected_sha1 = data.get("expected_sha1", "")
        return task

    def progress_percent(self) -> float:
        """获取下载进度百分比"""
        if self.total_size <= 0:
            return 0.0
        return min(100.0, (self.downloaded_size / self.total_size) * 100)

    def speed_text(self) -> str:
        """获取速度文本(需要外部设置, 这里只返回占位)"""
        return ""


class DownloadManager:
    """下载任务管理器(单例)"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.tasks: Dict[str, DownloadTask] = {}
        self._save_path = None
        self._progress_callbacks: List[Callable] = []

    def init(self, save_dir: str):
        """初始化, 加载保存的任务"""
        self._save_path = Path(save_dir) / "download_tasks.json"
        self._load()
        # 把所有下载中的任务标记为暂停(因为启动器重启了)
        for task in self.tasks.values():
            if task.status == STATUS_DOWNLOADING:
                task.status = STATUS_PAUSED
                task.updated_at = time.time()
        self._save()

    def _load(self):
        """从文件加载任务"""
        if not self._save_path or not self._save_path.exists():
            return
        try:
            with open(self._save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for task_data in data.get("tasks", []):
                task = DownloadTask.from_dict(task_data)
                self.tasks[task.task_id] = task
        except Exception:
            pass

    def _save(self):
        """保存任务到文件"""
        if not self._save_path:
            return
        try:
            self._save_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "tasks": [t.to_dict() for t in self.tasks.values()],
                "saved_at": time.time(),
            }
            with open(self._save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_task(self, url: str, dest_path: str, item_name: str = "",
                 source: str = "", expected_sha1: str = "") -> DownloadTask:
        """添加一个下载任务"""
        task = DownloadTask()
        task.url = url
        task.dest_path = dest_path
        task.file_name = Path(dest_path).name
        task.item_name = item_name or task.file_name
        task.source = source
        task.expected_sha1 = expected_sha1
        task.status = STATUS_PENDING
        # 如果目标文件已存在, 记录已下载大小
        try:
            p = Path(dest_path)
            if p.exists():
                task.downloaded_size = p.stat().st_size
        except Exception:
            pass
        self.tasks[task.task_id] = task
        self._save()
        self._notify_callbacks()
        return task

    def update_progress(self, task_id: str, downloaded: int, total: int = None):
        """更新下载进度"""
        task = self.tasks.get(task_id)
        if not task:
            return
        task.downloaded_size = downloaded
        if total:
            task.total_size = total
        task.status = STATUS_DOWNLOADING
        task.updated_at = time.time()
        # 定期保存(每 1MB 或 5 秒保存一次, 这里简化为每次都保存但加锁)
        self._save()
        self._notify_callbacks()

    def mark_completed(self, task_id: str):
        """标记任务完成"""
        task = self.tasks.get(task_id)
        if not task:
            return
        task.status = STATUS_COMPLETED
        task.completed_at = time.time()
        task.updated_at = time.time()
        try:
            p = Path(task.dest_path)
            if p.exists():
                task.downloaded_size = p.stat().st_size
                task.total_size = task.downloaded_size
        except Exception:
            pass
        self._save()
        self._notify_callbacks()

    def mark_failed(self, task_id: str, error_msg: str = ""):
        """标记任务失败"""
        task = self.tasks.get(task_id)
        if not task:
            return
        task.status = STATUS_FAILED
        task.error_msg = error_msg
        task.updated_at = time.time()
        self._save()
        self._notify_callbacks()

    def mark_paused(self, task_id: str):
        """标记任务暂停"""
        task = self.tasks.get(task_id)
        if not task:
            return
        task.status = STATUS_PAUSED
        task.updated_at = time.time()
        self._save()
        self._notify_callbacks()

    def cancel_task(self, task_id: str):
        """取消任务(不删除文件)"""
        task = self.tasks.get(task_id)
        if not task:
            return
        task.status = STATUS_CANCELLED
        task.updated_at = time.time()
        self._save()
        self._notify_callbacks()

    def remove_task(self, task_id: str, delete_file: bool = False):
        """删除任务"""
        task = self.tasks.pop(task_id, None)
        if task and delete_file:
            try:
                p = Path(task.dest_path)
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        self._save()
        self._notify_callbacks()

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务"""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[DownloadTask]:
        """获取所有任务(按更新时间倒序)"""
        return sorted(self.tasks.values(), key=lambda t: t.updated_at, reverse=True)

    def get_pending_tasks(self) -> List[DownloadTask]:
        """获取未完成的任务(等待中/下载中/暂停/失败)"""
        active_status = {STATUS_PENDING, STATUS_DOWNLOADING, STATUS_PAUSED, STATUS_FAILED}
        return [t for t in self.get_all_tasks() if t.status in active_status]

    def get_paused_tasks(self) -> List[DownloadTask]:
        """获取暂停的任务(可以继续下载的)"""
        return [t for t in self.get_all_tasks() if t.status in (STATUS_PAUSED, STATUS_FAILED)]

    def clear_completed(self):
        """清除已完成的任务"""
        to_remove = [tid for tid, t in self.tasks.items() if t.status == STATUS_COMPLETED]
        for tid in to_remove:
            del self.tasks[tid]
        self._save()
        self._notify_callbacks()

    def register_callback(self, callback: Callable):
        """注册进度回调(任务变化时调用)"""
        self._progress_callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """取消注册回调"""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    def _notify_callbacks(self):
        """通知所有回调"""
        for cb in self._progress_callbacks:
            try:
                cb()
            except Exception:
                pass


# 全局单例
manager = DownloadManager()
