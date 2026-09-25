import math
import comtypes

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget

from pycaw.pycaw import AudioUtilities, IAudioMeterInformation


class UltronHUDCore(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "idle"
        self.angle_fast = 0.0
        self.angle_slow = 0.0
        self.pulse = 0.0
        self.symbol_expression = "[ - _ - ]"

        # Real Windows output audio meter
        self.audio_peak = 0.0
        self.audio_meter = None

        try:
            comtypes.CoInitialize()

            device = AudioUtilities.GetSpeakers()

            meter = device._dev.Activate(
                IAudioMeterInformation._iid_,
                comtypes.CLSCTX_ALL,
                None,
            )

            self.audio_meter = meter.QueryInterface(
                IAudioMeterInformation
            )

        except Exception:
            self.audio_meter = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(25)

    def set_state(self, new_state):
        self.state = new_state
        if new_state == "idle":
            self.symbol_expression = "[ - _ - ]"
        elif new_state == "listening":
            self.symbol_expression = "[ o _ o ]"
        elif new_state == "thinking":
            self.symbol_expression = "[ > _ < ]"
        elif new_state == "speaking":
            self.symbol_expression = "[ ~ _ ~ ]"
        else:
            self.symbol_expression = "[ - _ - ]"
        self.update()

    def animate(self):
        # Read REAL Windows output level
        if self.audio_meter is not None:
            try:
                self.audio_peak = max(
                    0.0,
                    min(
                        1.0,
                        float(
                            self.audio_meter.GetPeakValue()
                        ),
                    ),
                )
            except Exception:
                self.audio_peak = 0.0

        spd = 2.5 if self.state in ["listening", "thinking", "speaking"] else 1.0
        self.angle_fast += 2.5 * spd
        self.angle_slow -= 1.2 * spd
        self.pulse += 0.08 * spd
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        if self.state == "listening":
            main_red, accent_cyan = QColor(255,0,51), QColor(0,240,255)
        elif self.state == "thinking":
            main_red, accent_cyan = QColor(255,0,128), QColor(255,200,0)
        elif self.state == "speaking":
            main_red, accent_cyan = QColor(0,240,255), QColor(255,0,85)
        else:
            main_red, accent_cyan = QColor(255,0,51), QColor(255,51,85)

        painter.setPen(QPen(QColor(255,0,51,140), 2))
        bk, margin = 20, 30
        painter.drawLine(margin, margin, margin+bk, margin)
        painter.drawLine(margin, margin, margin, margin+bk)
        painter.drawLine(w-margin, margin, w-margin-bk, margin)
        painter.drawLine(w-margin, margin, w-margin, margin+bk)

        glow_r = 170 + int(math.sin(self.pulse)*15)
        radial = QRadialGradient(cx, cy, glow_r)
        radial.setColorAt(0.0, QColor(main_red.red(), main_red.green(), main_red.blue(), 70))
        radial.setColorAt(1.0, QColor(0,0,0,0))
        painter.setBrush(QBrush(radial))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx-glow_r, cy-glow_r, glow_r*2, glow_r*2)

        num_bars, radius_bars = 40, 145

        for i in range(num_bars):
            angle_rad = math.radians(
                i*(360/num_bars)+self.angle_slow
            )

            # Real audio level drives the existing bars.
            # The sine factor keeps the original futuristic radial shape.
            wave = 0.65 + 0.35 * abs(
                math.sin(self.pulse + i * 0.5)
            )

            bar_h = 6 + int(
                self.audio_peak * 42 * wave
            )

            x1, y1 = (
                cx+radius_bars*math.cos(angle_rad),
                cy+radius_bars*math.sin(angle_rad)
            )

            x2, y2 = (
                cx+(radius_bars+bar_h)*math.cos(angle_rad),
                cy+(radius_bars+bar_h)*math.sin(angle_rad)
            )

            painter.setPen(
                QPen(
                    QColor(
                        main_red.red(),
                        main_red.green(),
                        main_red.blue(),
                        150
                    ),
                    2
                )
            )

            painter.drawLine(
                QPointF(x1,y1),
                QPointF(x2,y2)
            )

        r_outer = 130
        painter.setPen(QPen(main_red, 2.5, Qt.PenStyle.DashLine))
        painter.drawArc(
            QRectF(
                cx-r_outer,
                cy-r_outer,
                r_outer*2,
                r_outer*2
            ),
            int(self.angle_fast*16),
            140*16
        )

        r_inner = 110
        painter.setPen(QPen(accent_cyan,1.5))
        painter.drawArc(
            QRectF(
                cx-r_inner,
                cy-r_inner,
                r_inner*2,
                r_inner*2
            ),
            int(self.angle_slow*16),
            220*16
        )

        painter.setPen(QPen(QColor(255,255,255),2))
        font = QFont("Consolas",22,QFont.Weight.Bold)
        font.setLetterSpacing(
            QFont.SpacingType.AbsoluteSpacing,
            3
        )
        painter.setFont(font)

        painter.drawText(
            QRectF(cx-120,cy-25,240,50),
            Qt.AlignmentFlag.AlignCenter,
            self.symbol_expression
        )