# -*- coding: utf-8 -*-
"""
VoxelLauncher - 下载器模块
- 支持镜像源 URL 重写(官方源 <-> BMCLAPI)
- 下载文件 sha1 完整性校验, 损坏自动重下
- 断点续传(HTTP Range)
- 并发下载线程池(用于 libraries / assets)
"""
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from config import CONFIG


class DownloadError(Exception):
    """下载失败异常"""


# ---------------------------------------------------------------
# sha1 工具
# ---------------------------------------------------------------
def sha1_of_file(path, chunk_size=1 << 20):
    """计算文件 sha1 十六进制字符串"""
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------
# URL 镜像重写
# ---------------------------------------------------------------
def rewrite_url(url):
    """根据当前下载源把官方 URL 重写为镜像 URL。官方源则原样返回。"""
    source = CONFIG.get("download_source", "mojang")
    if source != "bmclapi":
        return url
    return _force_mirror_url(url)


def _force_mirror_url(url):
    """强制把官方 URL 转为 BMCLAPI 镜像(不管当前配置), 用于官方源失败时自动兜底"""
    if url.startswith("https://libraries.minecraft.net/"):
        return url.replace(
            "https://libraries.minecraft.net/", "https://bmclapi2.bangbang93.com/maven/"
        )
    if url.startswith("https://resources.download.minecraft.net/"):
        return url.replace(
            "https://resources.download.minecraft.net/",
            "https://bmclapi2.bangbang93.com/assets/",
        )
    if url.startswith("https://piston-meta.mojang.com/"):
        return url.replace(
            "https://piston-meta.mojang.com/",
            "https://bmclapi2.bangbang93.com/mc/game/",
        )
    if url.startswith("https://launchermeta.mojang.com/"):
        return url.replace(
            "https://launchermeta.mojang.com/",
            "https://bmclapi2.bangbang93.com/mc/",
        )
    if url.startswith("https://piston-data.mojang.com/"):
        return url.replace(
            "https://piston-data.mojang.com/",
            "https://bmclapi2.bangbang93.com/",
        )
    return url


# ---------------------------------------------------------------
# 单个文件下载
# ---------------------------------------------------------------
def download_file(url, dest, expected_sha1=None, resume=True, max_retry=3,
                  progress_cb=None):
    """
    下载单个文件到 dest。
    - 若 dest 已存在且 sha1 匹配, 直接跳过
    - 支持断点续传(resume=True)
    - 下载完成后校验 sha1, 不通过则删除重下
    - 自动镜像互备: 官方源失败自动切 BMCLAPI 镜像重试(无需手动切换)
    返回 True 表示成功。
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    primary_url = rewrite_url(url)
    mirror_url = _force_mirror_url(url)
    # 候选 URL 列表: 先当前配置源, 失败后切镜像(如果不同)
    use_mirror = False

    # 已存在且校验通过 -> 跳过
    if expected_sha1 and dest.exists() and dest.stat().st_size > 0:
        try:
            if sha1_of_file(dest) == expected_sha1.lower():
                return True
        except OSError:
            pass
        dest.unlink(missing_ok=True)

    for attempt in range(max_retry):
        current_url = mirror_url if use_mirror else primary_url
        try:
            headers = {}
            mode = "wb"
            # 断点续传: 已存在部分文件则用 Range
            if resume and dest.exists() and dest.stat().st_size > 0:
                headers["Range"] = "bytes={}-".format(dest.stat().st_size)
                mode = "ab"

            resp = requests.get(current_url, headers=headers, stream=True,
                                timeout=(30, 120))  # 连接30s, 读取120s, 避免永久卡住
            if resp.status_code == 416:
                # 范围不可满足 => 文件其实已完整, 直接校验
                resp.close()
            elif resp.status_code in (200, 206):
                if resp.status_code == 200 and "Range" in headers:
                    # 服务器忽略了 Range, 从头写
                    dest.unlink(missing_ok=True)
                    mode = "wb"
                with open(dest, mode) as f:
                    for chunk in resp.iter_content(chunk_size=1 << 16):
                        f.write(chunk)
                        if progress_cb:
                            progress_cb(len(chunk))
                resp.close()
            else:
                resp.close()
                raise DownloadError("HTTP {}: {}".format(resp.status_code,
                                                          current_url))

            # sha1 校验
            if expected_sha1 and dest.exists() and dest.stat().st_size > 0:
                if sha1_of_file(dest) != expected_sha1.lower():
                    dest.unlink(missing_ok=True)
                    continue  # 损坏, 重试
            return True
        except DownloadError:
            raise
        except Exception as exc:  # 网络异常, 重试
            # 第一次失败且有可用镜像 -> 自动切镜像
            if attempt == 0 and mirror_url != primary_url and not use_mirror:
                use_mirror = True
                continue
            if attempt == max_retry - 1:
                raise DownloadError("下载失败 {}: {}".format(current_url, exc))

    raise DownloadError("下载校验失败: {}".format(url))


# ---------------------------------------------------------------
# 并发下载池
# ---------------------------------------------------------------
class DownloadPool:
    """用线程池并发下载多个文件, 收集失败项"""

    def __init__(self, max_workers=8):
        self.pool = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()
        self.failed = []
        self.futures = []

    def submit(self, fn, *args, **kwargs):
        fut = self.pool.submit(fn, *args, **kwargs)
        self.futures.append(fut)
        return fut

    def submit_download(self, url, dest, expected_sha1=None):
        """并发下载一个文件, 失败记录到 self.failed"""
        def _do():
            try:
                download_file(url, dest, expected_sha1=expected_sha1)
            except Exception as exc:
                with self.lock:
                    self.failed.append((str(dest), str(exc)))
        return self.submit(_do)

    def wait(self):
        """等待所有任务完成"""
        for fut in self.futures:
            fut.result()
        return list(self.failed)

    def shutdown(self):
        self.pool.shutdown(wait=True)


# ---------------------------------------------------------------
# 高速多线程分块下载器(单文件多线程, 支持断点续传)
# 基于用户自写的 MultiThreadDownloader 核心逻辑整合
# ---------------------------------------------------------------
class FastDownloader:
    """
    单文件多线程分块下载器。
    - 线程数 1~50 可调
    - HTTP Range 分块, 每线程下载一块
    - 断点续传(.part 临时文件, 重试时从已写位置继续)
    - 每线程 3 次重试, 全部失败自动降级单线程
    - 服务器不支持 Range 时自动降级单线程
    - 下载完成后 sha1 校验
    - 线程间随机 50~100ms 启动延迟避免被封
    """
    CHUNK_BUFFER = 8192
    MAX_RETRIES = 3

    def __init__(self, url, dest, thread_count=10, expected_sha1=None,
                 progress_cb=None, mirror_url=None):
        self.url = url
        self.dest = Path(dest)
        self.thread_count = max(1, min(50, thread_count))
        self.expected_sha1 = expected_sha1
        self.progress_cb = progress_cb
        self.mirror_url = mirror_url
        self.total_size = 0
        self.downloaded = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._need_fallback = False
        self._part_file = None

    def download(self):
        """执行下载, 返回 True 表示成功。"""
        self.dest.parent.mkdir(parents=True, exist_ok=True)
        # 已存在且校验通过 -> 跳过
        if self.expected_sha1 and self.dest.exists() and self.dest.stat().st_size > 0:
            try:
                if sha1_of_file(self.dest) == self.expected_sha1.lower():
                    return True
            except OSError:
                pass
            self.dest.unlink(missing_ok=True)

        # 探测服务器
        total, supports_range = self._probe(self.url)
        if total is None and self.mirror_url:
            total, supports_range = self._probe(self.mirror_url)
            if total is not None:
                self.url = self.mirror_url
        if total is None:
            raise DownloadError("无法连接服务器: " + self.url)

        self.total_size = total

        if supports_range and total > 0 and self.thread_count > 1:
            ok = self._multi_thread()
            if not ok and not self._stop.is_set():
                # 降级单线程
                self._cleanup_part()
                self.downloaded = 0
                return self._single_thread()
            return ok
        else:
            return self._single_thread()

    def _probe(self, url):
        """探测文件大小和 Range 支持, 返回 (size, supports_range)"""
        try:
            resp = requests.head(url, allow_redirects=True, timeout=15)
            if resp.status_code != 200:
                resp = requests.get(url, stream=True, allow_redirects=True, timeout=15)
            cl = resp.headers.get("Content-Length")
            total = int(cl) if cl else 0
            accept = resp.headers.get("Accept-Ranges", "").lower()
            supports = accept == "bytes"
            resp.close()
            if supports and total > 0:
                supports = self._verify_range(url)
            return total, supports
        except Exception:
            return None, False

    def _verify_range(self, url):
        """用 1 字节请求验证 Range 支持"""
        try:
            resp = requests.get(url, headers={"Range": "bytes=0-0"},
                                stream=True, timeout=15)
            status = resp.status_code
            resp.close()
            return status == 206
        except Exception:
            return False

    def _multi_thread(self):
        """多线程分块下载"""
        chunk = self.total_size // self.thread_count
        self._part_file = str(self.dest) + ".part"
        # 预分配文件
        try:
            with open(self._part_file, "wb") as f:
                f.truncate(self.total_size)
        except OSError as e:
            raise DownloadError("创建临时文件失败(磁盘空间不足?): " + str(e))

        threads = []
        for i in range(self.thread_count):
            if self._stop.is_set():
                break
            start = i * chunk
            end = self.total_size - 1 if i == self.thread_count - 1 else start + chunk - 1
            t = threading.Thread(target=self._download_chunk,
                                 args=(i, start, end), daemon=True)
            threads.append(t)
            t.start()
            if i < self.thread_count - 1:
                import random as _r
                import time as _t
                _t.sleep(_r.uniform(0.05, 0.10))

        for t in threads:
            t.join()

        if self._need_fallback:
            return False
        if self._stop.is_set():
            self._cleanup_part()
            return False

        # 校验大小
        if self.downloaded >= self.total_size:
            import shutil as _sh
            _sh.move(self._part_file, str(self.dest))
            if self.expected_sha1:
                if sha1_of_file(self.dest) != self.expected_sha1.lower():
                    self.dest.unlink(missing_ok=True)
                    return False
            return True
        self._cleanup_part()
        return False

    def _download_chunk(self, tid, start, end):
        """下载一个分块, 支持断点续传"""
        current = start
        headers = {"Range": "bytes={}-{}".format(start, end)}
        for attempt in range(1, self.MAX_RETRIES + 1):
            if self._stop.is_set() or self._need_fallback:
                return
            try:
                resp = requests.get(self.url, headers=headers, stream=True,
                                    allow_redirects=True, timeout=30)
                if resp.status_code == 200:
                    resp.close()
                    self._need_fallback = True
                    self._stop.set()
                    return
                resp.raise_for_status()
                with open(self._part_file, "r+b") as f:
                    f.seek(current)
                    for data in resp.iter_content(chunk_size=self.CHUNK_BUFFER):
                        if self._stop.is_set() or self._need_fallback:
                            resp.close()
                            return
                        if data:
                            f.write(data)
                            with self._lock:
                                self.downloaded += len(data)
                            current += len(data)
                            if self.progress_cb:
                                self.progress_cb(len(data))
                resp.close()
                return
            except Exception:
                if attempt < self.MAX_RETRIES:
                    import time as _t
                    _t.sleep(1)
                    if current > start:
                        headers["Range"] = "bytes={}-{}".format(current, end)
                else:
                    self._need_fallback = True
                    self._stop.set()

    def _single_thread(self):
        """单线程下载(降级或线程数=1)"""
        part = str(self.dest) + ".part"
        try:
            resp = requests.get(self.url, stream=True, allow_redirects=True, timeout=30)
            resp.raise_for_status()
            if self.total_size == 0:
                cl = resp.headers.get("Content-Length")
                if cl:
                    self.total_size = int(cl)
            with open(part, "wb") as f:
                for data in resp.iter_content(chunk_size=self.CHUNK_BUFFER):
                    if data:
                        f.write(data)
                        self.downloaded += len(data)
                        if self.progress_cb:
                            self.progress_cb(len(data))
            resp.close()
            import shutil as _sh
            _sh.move(part, str(self.dest))
            if self.expected_sha1:
                if sha1_of_file(self.dest) != self.expected_sha1.lower():
                    self.dest.unlink(missing_ok=True)
                    return False
            return True
        except Exception:
            self._cleanup_part()
            return False

    def stop(self):
        """停止下载"""
        self._stop.set()

    def get_progress(self):
        """返回 (downloaded, total_size) 用于 UI 显示"""
        return self.downloaded, self.total_size

    def _cleanup_part(self):
        try:
            if self._part_file and os.path.exists(self._part_file):
                os.remove(self._part_file)
        except OSError:
            pass


def fast_download(url, dest, thread_count=None, expected_sha1=None,
                  progress_cb=None):
    """
    便捷函数: 使用多线程下载器下载单个文件。
    thread_count 为 None 时从 CONFIG 读取(默认10), 范围1~50。
    """
    if thread_count is None:
        thread_count = CONFIG.get("download_threads", 10)
    mirror = _force_mirror_url(url) if rewrite_url(url) != url else None
    dl = FastDownloader(url, dest, thread_count=thread_count,
                        expected_sha1=expected_sha1, progress_cb=progress_cb,
                        mirror_url=mirror)
    return dl.download()


# ---------------------------------------------------------------
# 带任务管理的下载(支持断点续传 + 进度记录)
# ---------------------------------------------------------------
def download_with_task(task, progress_cb=None):
    """
    使用下载任务对象下载文件, 自动记录进度。
    task: DownloadTask 对象
    progress_cb: 额外的进度回调 callback(downloaded_bytes)
    返回 True 表示成功
    """
    import download_manager
    from download_manager import STATUS_COMPLETED, STATUS_FAILED

    dest = Path(task.dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # 已存在且校验通过 -> 直接标记完成
    if task.expected_sha1 and dest.exists() and dest.stat().st_size > 0:
        try:
            if sha1_of_file(dest) == task.expected_sha1.lower():
                download_manager.manager.mark_completed(task.task_id)
                return True
        except OSError:
            pass
        dest.unlink(missing_ok=True)

    primary_url = rewrite_url(task.url)
    mirror_url = _force_mirror_url(task.url)
    use_mirror = False
    max_retry = 3

    for attempt in range(max_retry):
        current_url = mirror_url if use_mirror else primary_url
        try:
            headers = {}
            mode = "wb"
            # 断点续传: 已存在部分文件则用 Range
            if dest.exists() and dest.stat().st_size > 0:
                headers["Range"] = "bytes={}-".format(dest.stat().st_size)
                mode = "ab"
                task.downloaded_size = dest.stat().st_size

            resp = requests.get(current_url, headers=headers, stream=True,
                                timeout=(30, 120))
            # 获取总大小
            total = int(resp.headers.get("Content-Length", 0))
            if resp.status_code == 200:
                task.total_size = total
                task.downloaded_size = 0
            elif resp.status_code == 206:
                # 部分内容, 总大小 = 已下载 + 剩余
                content_range = resp.headers.get("Content-Range", "")
                if "/" in content_range:
                    try:
                        task.total_size = int(content_range.split("/")[-1])
                    except Exception:
                        task.total_size = total + task.downloaded_size
                else:
                    task.total_size = total + task.downloaded_size
            elif resp.status_code == 416:
                # 范围不可满足 => 文件其实已完整
                resp.close()
                download_manager.manager.mark_completed(task.task_id)
                return True
            else:
                resp.close()
                raise DownloadError("HTTP {}: {}".format(resp.status_code, current_url))

            if resp.status_code == 200 and "Range" in headers:
                # 服务器忽略了 Range, 从头写
                dest.unlink(missing_ok=True)
                mode = "wb"
                task.downloaded_size = 0

            with open(dest, mode) as f:
                for chunk in resp.iter_content(chunk_size=1 << 16):
                    f.write(chunk)
                    task.downloaded_size += len(chunk)
                    # 更新任务进度
                    download_manager.manager.update_progress(
                        task.task_id, task.downloaded_size, task.total_size)
                    if progress_cb:
                        progress_cb(task.downloaded_size)
            resp.close()

            # sha1 校验
            if task.expected_sha1 and dest.exists() and dest.stat().st_size > 0:
                if sha1_of_file(dest) != task.expected_sha1.lower():
                    dest.unlink(missing_ok=True)
                    task.downloaded_size = 0
                    continue  # 损坏, 重试

            download_manager.manager.mark_completed(task.task_id)
            return True
        except DownloadError:
            raise
        except Exception as exc:
            # 第一次失败且有可用镜像 -> 自动切镜像
            if attempt == 0 and mirror_url != primary_url and not use_mirror:
                use_mirror = True
                continue
            if attempt == max_retry - 1:
                download_manager.manager.mark_failed(task.task_id, str(exc))
                raise DownloadError("下载失败 {}: {}".format(current_url, exc))

    download_manager.manager.mark_failed(task.task_id, "下载校验失败")
    raise DownloadError("下载校验失败: {}".format(task.url))
