import random
import threading
import time

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

URLS = [
    "https://v2.xxapi.cn/api/meinv?return=302",
    "https://api.jkyai.top/API/jxhssp.php",
    "https://api.jkyai.top/API/jxbssp.php",
]

# 全局视频缓存与当前位置索引
_VIDEO_CACHE: list[str] = []
_CURRENT_INDEX: int = -1
_LOCK = threading.RLock()

# 预取设置
_PREFETCH_AHEAD: int = 10  # 静默缓存后面N个
_RUN_PREFETCH = False
_PREFETCH_THREAD: threading.Thread | None = None


def _fetch_new_video_url() -> str:
    """从接口获取一个新的直链播放地址。"""
    resp = requests.get(URLS[0], headers=HEADERS, allow_redirects=True)
    return resp.url


def get_next_video_url() -> str:
    """获取下一个视频地址。
    - 如果缓存中已有下一个，则直接返回；
    - 否则拉取新地址，写入缓存，再返回。
    返回值：视频URL
    """
    global _CURRENT_INDEX, _VIDEO_CACHE
    # 先尝试走缓存
    with _LOCK:
        if _CURRENT_INDEX + 1 < len(_VIDEO_CACHE):
            _CURRENT_INDEX += 1
            url = _VIDEO_CACHE[_CURRENT_INDEX]
            # 触发后台预取
            _kick_prefetch()
            return url

    # 缓存没有，拉取一个新视频（网络请求不持锁）
    url = _fetch_new_video_url()
    with _LOCK:
        _VIDEO_CACHE.append(url)
        _CURRENT_INDEX = len(_VIDEO_CACHE) - 1
    # 触发后台预取
    _kick_prefetch()
    return url


def get_prev_video_url() -> str | None:
    """获取上一个视频地址；若没有上一个则返回None。"""
    global _CURRENT_INDEX
    with _LOCK:
        if _CURRENT_INDEX > 0:
            _CURRENT_INDEX -= 1
            return _VIDEO_CACHE[_CURRENT_INDEX]
        return None


def refresh_videos() -> None:
    """清空缓存列表和游标（供刷新按钮使用）。"""
    global _CURRENT_INDEX, _VIDEO_CACHE
    with _LOCK:
        _VIDEO_CACHE = []
        _CURRENT_INDEX = -1
    # 刷新后继续预取
    _kick_prefetch()


def get_cache_state() -> tuple[int, int]:
    """返回 (当前索引(从0开始), 缓存总数)。若尚未加载任何视频，则返回 (-1, 0)。"""
    with _LOCK:
        return _CURRENT_INDEX, len(_VIDEO_CACHE)


# 兼容旧接口名（如被其他地方引用）
def get_beauty_video() -> str:
    return get_next_video_url()


# ========== 预取实现 ==========
def _prefetch_loop() -> None:
    """后台线程：尽量保证 ahead 个缓存可用。"""
    global _RUN_PREFETCH
    while _RUN_PREFETCH:
        try:
            # 计算还差多少个
            with _LOCK:
                ahead = len(_VIDEO_CACHE) - (_CURRENT_INDEX + 1)
            if ahead >= _PREFETCH_AHEAD:
                time.sleep(0.3)
                continue

            # 一次只补一个，避免请求过快
            url = _fetch_new_video_url()
            with _LOCK:
                _VIDEO_CACHE.append(url)
            # 小憩，避免打爆接口
            time.sleep(0.2)
        except Exception:
            # 预取失败忽略，稍后重试
            time.sleep(0.5)


def _kick_prefetch() -> None:
    """确保预取线程在运行。"""
    global _RUN_PREFETCH, _PREFETCH_THREAD
    if not _RUN_PREFETCH:
        _RUN_PREFETCH = True
        _PREFETCH_THREAD = threading.Thread(target=_prefetch_loop, name="video_prefetch", daemon=True)
        _PREFETCH_THREAD.start()


def start_prefetch(ahead: int | None = None) -> None:
    """手动开启预取（可调整 ahead）。"""
    global _PREFETCH_AHEAD
    if isinstance(ahead, int) and ahead > 0:
        _PREFETCH_AHEAD = ahead
    _kick_prefetch()


def stop_prefetch() -> None:
    """停止预取线程。"""
    global _RUN_PREFETCH
    _RUN_PREFETCH = False
