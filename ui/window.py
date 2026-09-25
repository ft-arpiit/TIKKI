import sys

from .hud import UltronHUDCore

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from agent import TikkiAgent
from modules.stt import SpeechToText
from modules.tts import TextToSpeech


class STTWorker(QThread):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, stt):
        super().__init__()
        self.stt = stt

    def run(self):
        try:
            text = self.stt.listen_once()
            self.finished.emit(text)
        except Exception as exc:
            self.failed.emit(str(exc))


class TIKKIGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.agent = TikkiAgent()
        self.tts = TextToSpeech()
        self.stt = SpeechToText()
        self.stt_worker = None

        self.setWindowTitle("IKKI // ULTRON AI CORE INTERFACE")
        self.resize(1180, 740)

        self.init_ui()
        self.hud_core.set_state("idle")

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color:#020203;
            }

            QFrame#side_panel {
                background-color:#050508;
                border-right:1px solid #ff0033;
            }

            QFrame#right_panel {
                background-color:#05050a;
                border-left:1px solid #ff0033;
                border-top-left-radius:10px;
                border-bottom-left-radius:10px;
            }

            QFrame#separator {
                background-color:qlineargradient(
                    x1:0,y1:0,x2:1,y2:0,
                    stop:0 #ff0033,
                    stop:0.5 #00f0ff,
                    stop:1 #ff0033
                );
                max-height:2px;
                min-height:2px;
            }

            QTextEdit {
                background-color:#010103;
                color:#e2e8f0;
                border:1px solid #1a1a2e;
                border-radius:6px;
                font-family:'Consolas',monospace;
                font-size:13px;
                padding:10px;
            }

            QLineEdit {
                background-color:#080810;
                color:#00f0ff;
                border:1px solid #ff0033;
                border-radius:18px;
                padding:10px 16px;
                font-size:13px;
                font-family:'Consolas',monospace;
            }

            QPushButton#mic_btn {
                background-color:#ff0033;
                color:#ffffff;
                border:none;
                border-radius:18px;
                font-size:15px;
                font-weight:bold;
            }

            QPushButton#mic_btn:hover {
                background-color:#00f0ff;
                color:#000000;
            }

            QLabel {
                color:#64748b;
                font-family:'Consolas',monospace;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 8)

        main = QHBoxLayout()

        side = QFrame()
        side.setObjectName("side_panel")
        side.setFixedWidth(180)

        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(10, 20, 10, 20)

        banner = QVBoxLayout()
        banner.setSpacing(0)

        for char in ["I", "K", "K", "I"]:
            lbl = QLabel(char)
            lbl.setFont(
                QFont(
                    "Courier New",
                    64,
                    QFont.Weight.ExtraBold,
                )
            )
            lbl.setStyleSheet(
                "color:#ff0033;padding:0;margin:0;"
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            glow = QGraphicsDropShadowEffect(self)
            glow.setBlurRadius(25)
            glow.setColor(QColor(255, 0, 51, 180))
            glow.setOffset(0, 0)

            lbl.setGraphicsEffect(glow)
            banner.addWidget(lbl)

        side_layout.addLayout(banner)
        side_layout.addStretch()

        ver = QLabel(
            "SYSTEM VER:\nv4.0 Cyber Memory"
        )
        ver.setFont(QFont("Consolas", 8))
        ver.setStyleSheet("color:#00f0ff;")

        owner = QLabel(
            "OPERATOR:\nArpit Gupta\nECE Engineering"
        )
        owner.setFont(QFont("Consolas", 9))
        owner.setStyleSheet(
            "color:#ffffff;font-weight:bold;"
        )

        side_layout.addWidget(ver)
        side_layout.addSpacing(10)
        side_layout.addWidget(owner)

        main.addWidget(side)

        self.hud_core = UltronHUDCore()
        main.addWidget(self.hud_core, stretch=2)

        right = QFrame()
        right.setObjectName("right_panel")
        right.setFixedWidth(390)

        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel(
            "[ SYSTEM COMMUNICATIONS ]"
        )
        title.setStyleSheet(
            "color:#00f0ff;"
            "font-weight:bold;"
            "font-size:12px;"
            "letter-spacing:1px;"
        )

        right_layout.addWidget(title)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)

        right_layout.addWidget(self.chat_display)

        row = QHBoxLayout()

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText(
            "Enter command sequence..."
        )
        self.text_input.returnPressed.connect(
            self.handle_text_send
        )

        row.addWidget(self.text_input)

        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setObjectName("mic_btn")
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.clicked.connect(
            self.handle_mic
        )

        row.addWidget(self.mic_btn)

        right_layout.addLayout(row)

        main.addWidget(right)
        root_layout.addLayout(main)

        line = QFrame()
        line.setObjectName("separator")

        root_layout.addWidget(line)

    def append_message_ui(self, sender, text):
        color = (
            "#ff0033"
            if sender == "You"
            else "#00f0ff"
        )

        self.chat_display.append(
            f"<span style='color:{color};font-weight:bold;'>"
            f"{sender}:</span> "
            f"<span style='color:#e2e8f0;'>{text}</span><br>"
        )

    def handle_text_send(self):
        text = self.text_input.text().strip()

        if not text:
            return

        self.text_input.clear()
        self.process_command(text)

    def process_command(self, text):
        self.append_message_ui("You", text)

        self.hud_core.set_state("thinking")

        try:
            result = self.agent.run(text)
        except Exception as exc:
            result = f"I encountered an error: {exc}"

        self.append_message_ui("TIKKI", result)

        self.hud_core.set_state("speaking")
        self.tts.speak(result)

        from PyQt6.QtCore import QTimer

        QTimer.singleShot(
            max(1500, len(result) * 45),
            lambda: self.hud_core.set_state("idle"),
        )

    def handle_mic(self):
        if self.stt_worker is not None:
            if self.stt_worker.isRunning():
                return

        self.mic_btn.setEnabled(False)
        self.text_input.setEnabled(False)

        self.hud_core.set_state("listening")

        self.chat_display.append(
            "<span style='color:#64748b;'>"
            "[ LISTENING... ]"
            "</span><br>"
        )

        self.stt_worker = STTWorker(self.stt)

        self.stt_worker.finished.connect(
            self.handle_stt_result
        )

        self.stt_worker.failed.connect(
            self.handle_stt_error
        )

        self.stt_worker.finished.connect(
            self.cleanup_stt_worker
        )

        self.stt_worker.failed.connect(
            self.cleanup_stt_worker
        )

        self.stt_worker.start()

    def handle_stt_result(self, text):
        text = text.strip()

        if not text:
            self.chat_display.append(
                "<span style='color:#64748b;'>"
                "[ NO SPEECH DETECTED ]"
                "</span><br>"
            )

            self.hud_core.set_state("idle")
            return

        self.chat_display.append(
            "<span style='color:#64748b;'>"
            "[ HEARD ] "
            "</span>"
            f"<span style='color:#e2e8f0;'>{text}</span><br>"
        )

        self.process_command(text)

    def handle_stt_error(self, error):
        self.chat_display.append(
            "<span style='color:#ff0033;'>"
            "[ STT ERROR ] "
            f"{error}"
            "</span><br>"
        )

        self.hud_core.set_state("idle")

    def cleanup_stt_worker(self):
        self.mic_btn.setEnabled(True)
        self.text_input.setEnabled(True)

        if self.stt_worker is not None:
            self.stt_worker.deleteLater()
            self.stt_worker = None

    def closeEvent(self, event):
        if (
            self.stt_worker is not None
            and self.stt_worker.isRunning()
        ):
            self.stt_worker.quit()
            self.stt_worker.wait(2000)

        self.tts.stop()

        event.accept()


def main():
    app = QApplication(sys.argv)

    window = TIKKIGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()