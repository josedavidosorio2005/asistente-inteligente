from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QTimer, QPointF, Qt
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient
import random

class Particula:
    def __init__(self, ancho, alto):
        self.x = random.uniform(0, ancho)
        self.y = random.uniform(0, alto)
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-0.5, 0.5)
        self.size = random.uniform(2, 5)
        # Colores personalizados: azul, magenta, blanco, amarillo neón
        self.color = QColor(random.choice([
            QColor(0, 180, 255, 180),  # azul neón
            QColor(255, 0, 180, 180),  # magenta neón
            QColor(255, 255, 255, 120), # blanco
            QColor(255, 255, 0, 120)   # amarillo neón
        ]))

    def mover(self, ancho, alto):
        self.x += self.vx
        self.y += self.vy
        if self.x < 0 or self.x > ancho:
            self.vx *= -1
        if self.y < 0 or self.y > alto:
            self.vy *= -1

class FondoParticulas(QWidget):
    def __init__(self, parent=None, n=40):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.particulas = [Particula(self.width(), self.height()) for _ in range(n)]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animar)
        self.timer.start(30)

    def resizeEvent(self, event):
        for p in self.particulas:
            p.x = random.uniform(0, self.width())
            p.y = random.uniform(0, self.height())

    def animar(self):
        for p in self.particulas:
            p.mover(self.width(), self.height())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        # Fondo negro con degradado a gris
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, QColor(10,10,10))
        grad.setColorAt(1, QColor(60,60,60))
        painter.fillRect(rect, grad)
        painter.setRenderHint(QPainter.Antialiasing)
        for p in self.particulas:
            painter.setBrush(QBrush(p.color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)
