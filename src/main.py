import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from view import BeautyVideoPlayer


def main():
    app = QApplication(sys.argv)

    # 设置应用程序样式
    app.setStyle("Fusion")

    # 创建主窗口
    player = BeautyVideoPlayer()
    player.show()

    # 启动定时器更新时间标签
    timer = QTimer()
    timer.timeout.connect(player.update_time_label)
    timer.start(1000)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
