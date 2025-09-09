import requests
from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from api import (
    get_cache_state,
    get_next_video_url,
    get_prev_video_url,
    refresh_videos,
    start_prefetch,
)


class VideoDownloadThread(QThread):
    """视频下载线程"""

    progress_updated = pyqtSignal(int)
    download_finished = pyqtSignal(str)
    download_error = pyqtSignal(str)

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0

            with open(self.save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.progress_updated.emit(progress)

            self.download_finished.emit(self.save_path)
        except Exception as e:
            self.download_error.emit(str(e))


class ModernButton(QPushButton):
    """现代化按钮样式"""

    def __init__(self, text, icon=None):
        super().__init__(text)
        self.setMinimumHeight(45)
        self.setMaximumHeight(55)
        self.setMinimumWidth(100)
        self.setMaximumWidth(120)

        # 设置现代化样式
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5CBF60, stop:1 #4CAF50);
                transform: scale(1.05);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3d8b40, stop:1 #2e7d32);
            }
            QPushButton:disabled {
                background: #cccccc;
                color: #666666;
            }
        """)


class BeautyVideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Beauty Tok")
        self.setGeometry(100, 100, 400, 700)

        # 设置现代化主题
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e3c72, stop:1 #2a5298);
            }
            QWidget {
                background: transparent;
            }
        """)

        # 初始化媒体播放器
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        # 视频显示组件
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("""
            QVideoWidget {
                background: black;
                border-radius: 15px;
                border: 3px solid #4CAF50;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
            }
        """)
        self.media_player.setVideoOutput(self.video_widget)

        # 当前视频索引
        self.current_video_index = 0
        self.video_urls = []
        self.auto_play = False

        # 下载相关
        self.download_thread = None
        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)

        # 初始化UI
        self.init_ui()

        # 连接信号
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.playbackStateChanged.connect(self.state_changed)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.errorOccurred.connect(self.on_media_error)

        # 加载第一个视频
        start_prefetch(10)
        self.load_video()

    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 视频显示区域 - 设置为手机长条比例 (9:16)
        video_layout = QHBoxLayout()
        video_layout.addStretch()

        # 设置视频组件的固定尺寸比例 (9:16)
        self.video_widget.setMinimumSize(300, 533)  # 9:16 比例，稍微小一点
        self.video_widget.setMaximumSize(360, 640)  # 最大尺寸
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        video_layout.addWidget(self.video_widget)
        video_layout.addStretch()
        main_layout.addLayout(video_layout)

        # 进度条
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4CAF50, stop:1 #45a049);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5CBF60, stop:1 #4CAF50);
            }
        """)
        self.position_slider.sliderMoved.connect(self.set_position)
        main_layout.addWidget(self.position_slider)

        # 时间标签
        time_layout = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        time_layout.addWidget(self.time_label)
        time_layout.addStretch()
        main_layout.addLayout(time_layout)

        # 控制按钮区域 - 分两行布局
        controls_container = QWidget()
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setSpacing(10)

        # 第一行：主要播放控制
        main_controls_layout = QHBoxLayout()
        main_controls_layout.addStretch()

        self.prev_button = ModernButton("⏮ 上一个")
        self.prev_button.clicked.connect(self.previous_video)
        main_controls_layout.addWidget(self.prev_button)

        self.play_button = ModernButton("▶ 播放")
        self.play_button.clicked.connect(self.play_pause)
        main_controls_layout.addWidget(self.play_button)

        self.next_button = ModernButton("下一个 ⏭")
        self.next_button.clicked.connect(self.next_video)
        main_controls_layout.addWidget(self.next_button)

        main_controls_layout.addStretch()
        controls_layout.addLayout(main_controls_layout)

        # 第二行：辅助功能
        aux_controls_layout = QHBoxLayout()
        aux_controls_layout.addStretch()

        self.auto_button = ModernButton("🔄 自动播放")
        self.auto_button.clicked.connect(self.toggle_auto_play)
        aux_controls_layout.addWidget(self.auto_button)

        self.download_button = ModernButton("💾 下载")
        self.download_button.clicked.connect(self.download_video)
        aux_controls_layout.addWidget(self.download_button)

        self.refresh_button = ModernButton("🔄 刷新")
        self.refresh_button.clicked.connect(self.refresh_all)
        aux_controls_layout.addWidget(self.refresh_button)

        aux_controls_layout.addStretch()
        controls_layout.addLayout(aux_controls_layout)

        main_layout.addWidget(controls_container)

        # 下载进度条
        main_layout.addWidget(self.download_progress)

    def refresh_all(self):
        """清空缓存并获取一个新视频。"""
        refresh_videos()
        self.video_urls = []
        self.current_video_index = -1
        self.load_video()

    def show_message(self, title: str, text: str, level: str = "info") -> None:
        """统一的消息弹窗，修复黑底看不见文字问题。

        level: info | warning | error
        """
        box = QMessageBox(self)
        if level == "warning":
            box.setIcon(QMessageBox.Icon.Warning)
        elif level == "error":
            box.setIcon(QMessageBox.Icon.Critical)
        else:
            box.setIcon(QMessageBox.Icon.Information)

        box.setWindowTitle(title)
        box.setText(text)
        # 统一深色主题（白色文字），按钮有明显对比度
        box.setStyleSheet(
            """
            QMessageBox {
                background-color: #202124;
                border: 1px solid #3c4043;
            }
            QLabel { color: #ffffff; font-size: 14px; }
            QPushButton {
                background-color: #4CAF50;
                color: #ffffff;
                padding: 6px 14px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #5CBF60; }
            QPushButton:pressed { background-color: #2e7d32; }
            """
        )
        box.exec()

    def load_video(self):
        """加载视频"""
        try:
            video_url = get_next_video_url()
            if video_url:
                # 同步本地历史（只保留到当前索引，追加新视频）
                self.video_urls = self.video_urls[: self.current_video_index + 1]
                self.video_urls.append(video_url)
                self.current_video_index = len(self.video_urls) - 1
                self.media_player.setSource(QUrl(video_url))
                cur, total = get_cache_state()
                # 新视频自动播放
                self.media_player.play()
                self.play_button.setText("⏸ 暂停")
                # 成功开始加载时重置连续失败计数
                self.consecutive_failures = 0
            else:
                self.show_message("获取视频失败", "获取视频失败", level="error")
        except Exception as e:
            self.show_message("加载视频时出错", f"加载视频时出错: {str(e)}", level="error")

    def play_pause(self):
        """播放/暂停切换"""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.play_button.setText("▶ 播放")
        else:
            self.media_player.play()
            self.play_button.setText("⏸ 暂停")

    def previous_video(self):
        """上一个视频"""
        # 优先使用本地历史
        if self.current_video_index > 0:
            self.current_video_index -= 1
            url = self.video_urls[self.current_video_index]
        else:
            prev = get_prev_video_url()
            if prev is None:
                return
            # 将此前历史同步到本地列表头部
            self.video_urls.insert(0, prev)
            self.current_video_index = 0
            url = prev

        # 同步API的游标后退一次，避免下一次“下一个”误判为新拉取
        try:
            _ = get_prev_video_url()
        except Exception:
            pass

        self.media_player.setSource(QUrl(url))
        cur, total = get_cache_state()
        self.media_player.play()
        self.play_button.setText("⏸ 暂停")

    def next_video(self):
        """下一个视频"""
        # 若本地已有“后一个”，先走本地历史，不触发网络请求
        if self.current_video_index + 1 < len(self.video_urls):
            self.current_video_index += 1
            url = self.video_urls[self.current_video_index]
            # 尝试同步API游标前进一次（若API缓存不足则保持不变，不会请求网络）
            try:
                _ = get_next_video_url()  # 尝试让API游标与本地一起前进
            except Exception:
                pass

            self.media_player.setSource(QUrl(url))
            cur, total = get_cache_state()
            self.media_player.play()
            self.play_button.setText("⏸ 暂停")
            return

        # 否则加载新的一个（会自动播放并追加到历史）
        self.load_video()

    def toggle_auto_play(self):
        """切换自动播放"""
        self.auto_play = not self.auto_play
        if self.auto_play:
            self.auto_button.setText("⏹ 停止自动")
            self.auto_button.setStyleSheet(self.auto_button.styleSheet().replace("#4CAF50", "#f44336"))
        else:
            self.auto_button.setText("🔄 自动播放")
            self.auto_button.setStyleSheet(self.auto_button.styleSheet().replace("#f44336", "#4CAF50"))

    def on_media_status_changed(self, status):
        """媒体状态变化处理：
        - 未开启自动播放时，播放到末尾循环当前视频
        - 开启自动播放时，自动切换到下一个视频
        """
        from PyQt6.QtMultimedia import QMediaPlayer as _MP

        if status == _MP.MediaStatus.EndOfMedia:
            if self.auto_play:
                # 自动连播：切换下一个
                self.next_video()
            else:
                # 循环当前
                self.media_player.setPosition(0)
                self.media_player.play()
                self.play_button.setText("⏸ 暂停")
        elif status in (_MP.MediaStatus.BufferedMedia, _MP.MediaStatus.LoadedMedia):
            # 媒体成功加载，重置失败计数
            self.consecutive_failures = 0

    def on_media_error(self, error, error_string):
        """处理媒体播放错误：若出现404/Not Found或其他错误，自动切到下一个。"""
        try:
            from PyQt6.QtMultimedia import QMediaPlayer as _MP

            if not hasattr(self, "consecutive_failures"):
                self.consecutive_failures = 0
            self.consecutive_failures += 1

            err_text = (error_string or "").lower()
            is_404 = ("404" in err_text) or ("not found" in err_text)
            is_error = error != _MP.Error.NoError

            if is_404 or is_error:
                if self.consecutive_failures <= 5:
                    self.next_video()
                else:
                    self.show_message("播放错误", "连续多次加载失败，请尝试刷新。", level="error")
                    self.consecutive_failures = 0
        except Exception:
            # 忽略错误处理中的异常，避免循环
            pass

    def download_video(self):
        """下载当前视频"""
        if not self.video_urls or self.current_video_index >= len(self.video_urls):
            self.show_message("警告", "没有可下载的视频", level="warning")
            return

        # 选择保存路径
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存视频", f"beauty_video_{self.current_video_index + 1}.mp4", "视频文件 (*.mp4 *.avi *.mov)"
        )

        if save_path:
            self.download_progress.setVisible(True)
            self.download_progress.setValue(0)
            self.download_button.setEnabled(False)

            # 启动下载线程
            self.download_thread = VideoDownloadThread(self.video_urls[self.current_video_index], save_path)
            self.download_thread.progress_updated.connect(self.download_progress.setValue)
            self.download_thread.download_finished.connect(self.download_finished)
            self.download_thread.download_error.connect(self.download_error)
            self.download_thread.start()

    def download_finished(self, file_path):
        """下载完成"""
        self.download_progress.setVisible(False)
        self.download_button.setEnabled(True)
        self.show_message("下载完成", f"视频已保存到:\n{file_path}", level="info")

    def download_error(self, error_msg):
        """下载错误"""
        self.download_progress.setVisible(False)
        self.download_button.setEnabled(True)
        self.show_message("下载错误", f"下载失败:\n{error_msg}", level="error")

    def position_changed(self, position):
        """播放位置改变"""
        self.position_slider.setValue(position)

    def duration_changed(self, duration):
        """视频时长改变"""
        self.position_slider.setRange(0, duration)

    def state_changed(self, state):
        """播放状态改变"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("⏸ 暂停")
        else:
            self.play_button.setText("▶ 播放")

    def set_position(self, position):
        """设置播放位置"""
        self.media_player.setPosition(position)

    def update_time_label(self):
        """更新时间标签"""
        position = self.media_player.position()
        duration = self.media_player.duration()

        position_time = self.format_time(position)
        duration_time = self.format_time(duration)

        self.time_label.setText(f"{position_time} / {duration_time}")

    def format_time(self, milliseconds):
        """格式化时间"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
