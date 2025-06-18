import os
import platform
import threading
import time
import webbrowser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel, QPushButton, QTextEdit, QFrame,
                             QScrollArea, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QFont, QPainter, QPainterPath, QColor, QIcon
import psutil
import pythoncom

try:
    import speedtest
except ImportError:
    print("speedtest-cli not found. Installing...")
    os.system("pip install speedtest-cli")
    import speedtest
import wmi

import utils.cpu
import utils.gpu
import utils.internet
import utils.peripherals
import utils.system

LICENSE_URL = "https://sos.dom.ru/services/license_URM.pdf"


class RoundedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(45)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get button rect
        rect = self.rect()

        # Create rounded rectangle path
        path = QPainterPath()
        radius = 22  # Half of minimum height for fully rounded
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)

        # Fill with background color
        if self.isEnabled():
            if self.isDown():
                painter.fillPath(path, QColor(self.palette().color(self.palette().Dark)))
            else:
                painter.fillPath(path, QColor(self.palette().color(self.palette().Button)))
        else:
            painter.fillPath(path, QColor(self.palette().color(self.palette().Mid)))

        # Draw text
        painter.setPen(QColor(self.palette().color(self.palette().ButtonText)))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignCenter, self.text())


class DiagnosticsThread(QThread):
    status_update = pyqtSignal(str)
    text_insert = pyqtSignal(str, str)  # text, color
    diagnostics_complete = pyqtSignal()

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance

    def run(self):
        self.app_instance.failed_checks = []

        # Internet speed test
        self.status_update.emit("[1/4] Измеряю скорость интернета")
        download_speed, upload_speed, ping, error = utils.internet.run_speed_test_safe()

        if error:
            self.text_insert.emit(
                f"Ошибка тестирования скорости: {error}\nЗамерьте скорость вручную на speedtest.net\n", 'red')
            self.app_instance.failed_checks.append("Проводной интернет с пропускной способностью не менее 75 Мбит/с")
        else:
            if download_speed >= 75:
                self.text_insert.emit("[OK] Соединение в норме\n", "green")
            else:
                self.text_insert.emit(
                    "[НЕ OK] Проводной интернет по технологии FTTx, xPON с пропускной способностью не менее 75 Мбит/с\n",
                    "red")
                self.app_instance.failed_checks.append(
                    "Проводной интернет по технологии FTTx, xPON с пропускной способностью не менее 75 Мбит/с")

            self.text_insert.emit(f"     Загрузка: {download_speed:.0f} Мбит/с\n", "black")
            self.text_insert.emit(f"     Отдача:  {upload_speed:.0f} Мбит/с\n", "black")
            self.text_insert.emit(f"     Пинг:  {ping:.0f} мс\n", "black")

        # CPU check
        self.status_update.emit("[2/4] Проверяю оборудование (процессор)")
        cpu_name = utils.cpu.get_cpu_name()
        cpu_cores = psutil.cpu_count(logical=False)
        logical_cores = psutil.cpu_count(logical=True)

        if cpu_cores >= 2:
            self.text_insert.emit("[OK] Процессор в норме\n", "green")
        else:
            self.text_insert.emit("[НЕ OK] Процессор с не менее чем двумя ядрами\n", "red")
            self.app_instance.failed_checks.append("Процессор с не менее чем двумя ядрами")

        self.text_insert.emit(f"     Модель: {cpu_name}\n", "black")
        self.text_insert.emit(f"     Виртуальных ядер: {logical_cores}\n", "black")
        self.text_insert.emit(f"     Физических ядер: {cpu_cores}\n", "black")

        # Network adapter check
        self.status_update.emit("[2/4] Проверяю оборудование (сетевой адаптер)")
        ethernet_available = utils.internet.check_ethernet_connection()

        if ethernet_available:
            self.text_insert.emit("[OK] Подключение по кабелю\n", "green")
            adapters = utils.internet.get_ethernet_adapter_info()
            for adapter in adapters:
                self.text_insert.emit(f"     Сетевая карта: {adapter['adapter_name']}\n", "black")
                self.text_insert.emit(f"     Дуплекс: {adapter['speed']} Мбит/с\n", "black")
        else:
            self.text_insert.emit("[НЕ OK] Нет возможности подключения кабелем (Ethernet адаптер отсутствует)\n", "red")
            self.app_instance.failed_checks.append("Нет возможности подключения кабелем (Ethernet адаптер отсутствует)")

        # OS compatibility check
        self.status_update.emit("[2/4] Проверяю оборудование (операционная система)")
        citrix_compatible, version = utils.system.get_citrix_compatibility()

        if citrix_compatible:
            self.text_insert.emit("[OK] Поддержка Citrix в норме\n", "green")
        else:
            self.text_insert.emit("[НЕ OK] Citrix не поддерживается\n", "red")
            self.app_instance.failed_checks.append("Citrix не поддерживается")

        self.text_insert.emit(
            f"     Версия ОС: {platform.system()} {platform.release()} {platform.version().split('.')[2]} \n", "black")
        self.text_insert.emit(f"     Версия Citrix: {version} \n", "black")

        # RAM check
        self.status_update.emit("[2/4] Проверяю оборудование (ОЗУ)")
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        pythoncom.CoInitialize()
        c = wmi.WMI()
        ram_freq_list = [mem.Speed for mem in c.Win32_PhysicalMemory()]
        pythoncom.CoUninitialize()

        if ram_gb >= 4:
            self.text_insert.emit("[OK] Память в норме\n", "green")
        else:
            self.text_insert.emit("[НЕ OK] Оперативная память от 4 ГБ\n", "red")
            self.app_instance.failed_checks.append("Оперативная память от 4 ГБ")

        self.text_insert.emit(f"     Всего ОЗУ: {ram_gb:.0f} ГБ\n", "black")
        if ram_freq_list:
            self.text_insert.emit(f"     Частота: {ram_freq_list[0]} МГц\n", "black")

        # Display and GPU check
        self.status_update.emit("[2/4] Проверяю оборудование (экран и видеокарта)")
        # Note: get_screen_resolution needs to be adapted for PyQt
        width = QApplication.desktop().screenGeometry().width()
        height = QApplication.desktop().screenGeometry().height()
        gpu_name = utils.gpu.get_gpu_name()

        if width >= 1600 and height >= 900:
            self.text_insert.emit("[OK] Дисплей в норме\n", "green")
        else:
            self.text_insert.emit("[НЕ OK] Минимальное разрешение экрана 1600х900 и более\n", "red")
            self.app_instance.failed_checks.append("Минимальное разрешение экрана 1600х900 и более")

        self.text_insert.emit(f"     Разрешение дисплея: {width}x{height}\n", "black")
        self.text_insert.emit(f"     Видеокарта: {gpu_name}\n", "black")

        # Disk space check
        self.status_update.emit("[3/4] Проверяю диск")
        disk_usage = psutil.disk_usage("C:")
        free_gb = disk_usage.free / (1024 ** 3)

        if free_gb >= 10:
            self.text_insert.emit("[OK] Место на системном диске в норме\n", "green")
        else:
            self.text_insert.emit("[НЕ OK] Недостаточно места на диске\n", "red")
            self.app_instance.failed_checks.append("Недостаточно места на диске")

        self.text_insert.emit(f"     Свободно: {round(free_gb)} ГБ\n", "black")

        # Microphone check
        self.status_update.emit("[4/4] Проверяю периферию (микрофон)")
        mic_available = utils.peripherals.check_microphone()

        if mic_available:
            self.text_insert.emit("[OK] Микрофон обнаружен\n", "green")
        else:
            self.text_insert.emit("[НЕ OK] Микрофон не найден\n", "red")
            self.app_instance.failed_checks.append("Микрофон не найден")

        # Camera check
        self.status_update.emit("[4/4] Проверяю периферию (камера)")
        camera_available, cam_width, cam_height = utils.peripherals.check_camera()
        camera_hd = cam_width >= 1280 and cam_height >= 720

        if camera_available and camera_hd:
            self.text_insert.emit("[OK] Web-камера обнаружена\n", "green")
            self.text_insert.emit(f"      Разрешение: {cam_width}x{cam_height}\n", "black")
        else:
            self.text_insert.emit("[НЕ OK] Web-камера не соответствует требованиям\n", "red")
            self.app_instance.failed_checks.append("Web-камера не соответствует требованиям")

        # Final results
        self.text_insert.emit("\n" + "-" * 70 + "\n", "black")

        if not self.app_instance.failed_checks:
            self.text_insert.emit("Все проверки пройдены. ПК соответствует требованиям для удаленной работы\n", 'green')
        else:
            self.text_insert.emit("ПК не соответствует требованиям:\n", 'red')
            for issue in self.app_instance.failed_checks:
                if "процессор" in issue.lower():
                    self.text_insert.emit("- Требуется обновить процессор\n", 'red')
                elif "память" in issue.lower():
                    self.text_insert.emit("- Информация о памяти не получена\n", 'red')
                elif "кабель" in issue.lower() or "интернет" in issue.lower():
                    self.text_insert.emit("- Скорость интернета > 75 Мбит/с\n", 'red')
                elif "микрофон" in issue.lower():
                    self.text_insert.emit("- Наличие микрофона\n", 'red')
                elif "web-камера" in issue.lower():
                    self.text_insert.emit("- Наличие web-камеры с разрешением не хуже HD (внешней или встроенной)\n",
                                          'red')

        self.status_update.emit("Диагностика завершена")
        self.diagnostics_complete.emit()


class SystemDiagnosticsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.failed_checks = []
        self.diagnostics_complete = False
        self.test_started = False
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_dots = 0
        self.base_status_text = ""

        self.init_ui()
        self.show_initial_message()

    def init_ui(self):
        self.setWindowTitle("Диагностика возможности удаленной работы")
        self.setFixedSize(600, 700)
        self.setStyleSheet("background-color: #f0eded;")

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Header
        self.create_header(main_layout)

        # Main panel
        self.create_main_panel(main_layout)

        # Button panel
        self.create_button_panel(main_layout)

        # Bottom panel
        self.create_bottom_panel(main_layout)

    def create_header(self, parent_layout):
        header_frame = QFrame()
        header_frame.setFixedHeight(65)
        header_frame.setStyleSheet("background-color: #f0eded;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 10, 0, 10)

        # Logo
        logo_label = QLabel()
        logopath = os.path.join(os.path.dirname(__file__), 'assets/logo.png')
        if os.path.exists(logopath):
            pixmap = QPixmap(logopath)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("LOGO")
            logo_label.setStyleSheet("background-color: #ddd; padding: 10px;")

        logo_label.setFixedSize(50, 45)
        header_layout.addWidget(logo_label)

        header_layout.addSpacing(10)

        # Title
        title_label = QLabel("Диагностика возможности удаленной работы")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: black;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()
        parent_layout.addWidget(header_frame)

    def create_main_panel(self, parent_layout):
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #ccc;
                border-radius: 5px;
            }
        """)

        main_frame_layout = QVBoxLayout(self.main_frame)
        main_frame_layout.setContentsMargins(20, 20, 20, 20)

        # Text area
        self.text_widget = QTextEdit()
        self.text_widget.setFont(QFont("Arial", 10))
        self.text_widget.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: white;
            }
        """)
        self.text_widget.setReadOnly(True)
        main_frame_layout.addWidget(self.text_widget)

        # Status label (initially hidden)
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Arial", 10, QFont.StyleItalic))
        self.status_label.setStyleSheet("color: gray; padding: 5px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()  # Initially hidden
        main_frame_layout.addWidget(self.status_label)

        parent_layout.addWidget(self.main_frame)

    def create_button_panel(self, parent_layout):
        button_frame = QFrame()
        button_frame.setStyleSheet("background-color: #f0eded;")
        button_layout = QVBoxLayout(button_frame)
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setContentsMargins(10, 10, 10, 10)

        # Start button
        self.start_button = RoundedButton("Начать тест")
        self.start_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #FF312C;
                color: white;
                border: none;
                padding: 10px 30px;
            }
            QPushButton:hover {
                background-color: #e02e29;
            }
            QPushButton:pressed {
                background-color: #c52821;
            }
        """)
        self.start_button.clicked.connect(self.start_test)
        button_layout.addWidget(self.start_button)

        # Result buttons container
        result_buttons_frame = QFrame()
        result_buttons_layout = QHBoxLayout(result_buttons_frame)
        result_buttons_layout.setAlignment(Qt.AlignCenter)

        # Copy button
        self.copy_button = RoundedButton("Скопировать результат")
        self.copy_button.setFont(QFont("Arial", 10, QFont.Bold))
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.hide()

        # Restart button
        self.restart_button = RoundedButton("Перезапустить тест")
        self.restart_button.setFont(QFont("Arial", 10, QFont.Bold))
        self.restart_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.restart_button.clicked.connect(self.restart_test)
        self.restart_button.hide()

        result_buttons_layout.addWidget(self.copy_button)
        result_buttons_layout.addSpacing(10)
        result_buttons_layout.addWidget(self.restart_button)

        button_layout.addWidget(result_buttons_frame)
        parent_layout.addWidget(button_frame)

    def create_bottom_panel(self, parent_layout):
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background-color: #f0eded;")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(10, 10, 10, 10)

        prefix_label = QLabel("Используя данную программу вы принимаете")
        prefix_label.setFont(QFont("Arial", 9))
        prefix_label.setStyleSheet("color: #333;")
        bottom_layout.addWidget(prefix_label)

        link_label = QLabel(
            '<a href="#" style="color: #0066cc; text-decoration: underline;">условия пользовательского соглашения</a>')
        link_label.setFont(QFont("Arial", 9))
        link_label.linkActivated.connect(lambda: webbrowser.open_new(LICENSE_URL))
        bottom_layout.addWidget(link_label)

        bottom_layout.addStretch()
        parent_layout.addWidget(bottom_frame)

    def show_initial_message(self):
        self.text_widget.append("Добро пожаловать в программу диагностики возможности удаленной работы!\n")
        self.text_widget.append("Эта программа проверит:")
        self.text_widget.append("• Скорость интернет-соединения")
        self.text_widget.append("• Параметры процессора и оперативной памяти")
        self.text_widget.append("• Сетевое оборудование")
        self.text_widget.append("• Дисплей и видеокарту")
        self.text_widget.append("• Свободное место на системном диске")
        self.text_widget.append("• Наличие микрофона и веб-камеры\n")
        self.text_widget.append("Готовы начать тестирование? Нажмите кнопку 'Начать тест'.")

    def start_test(self):
        if not self.test_started:
            self.test_started = True
            self.start_button.hide()
            self.text_widget.clear()
            self.run_diagnostics()

    def restart_test(self):
        self.animation_timer.stop()
        self.diagnostics_complete = False
        self.test_started = True
        self.failed_checks = []

        self.copy_button.hide()
        self.restart_button.hide()

        self.text_widget.clear()
        self.run_diagnostics()

    def run_diagnostics(self):
        self.diagnostics_thread = DiagnosticsThread(self)
        self.diagnostics_thread.status_update.connect(self.update_status)
        self.diagnostics_thread.text_insert.connect(self.insert_text)
        self.diagnostics_thread.diagnostics_complete.connect(self.on_diagnostics_complete)
        self.diagnostics_thread.start()

    def update_status(self, message):
        if message == "Диагностика завершена" or message == "":
            self.animation_timer.stop()
            if message == "":
                self.status_label.hide()
            else:
                self.status_label.setText(message)
                self.status_label.show()
        else:
            self.base_status_text = message
            self.animation_dots = 0
            self.status_label.show()
            if not self.animation_timer.isActive():
                self.animation_timer.start(500)

    def update_animation(self):
        dots = "." * ((self.animation_dots % 3) + 1)
        self.status_label.setText(f"{self.base_status_text}{dots}")
        self.animation_dots += 1

    def insert_text(self, text, color):
        if color == "green":
            self.text_widget.setTextColor(QColor("#008000"))
        elif color == "red":
            self.text_widget.setTextColor(QColor("#FF0000"))
        else:
            self.text_widget.setTextColor(QColor("black"))

        self.text_widget.insertPlainText(text)
        self.text_widget.moveCursor(self.text_widget.textCursor().End)

    def on_diagnostics_complete(self):
        self.diagnostics_complete = True
        self.copy_button.show()
        self.restart_button.show()

    def copy_to_clipboard(self):
        if self.diagnostics_complete:
            content = self.text_widget.toPlainText()
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            QMessageBox.information(self, "Копирование", "Результаты диагностики скопированы в буфер обмена")
        else:
            QMessageBox.warning(self, "Предупреждение", "Диагностика еще не завершена")


def main():
    required_modules = ['psutil', 'speedtest', 'cv2', 'pyaudio', 'numpy']
    missing_modules = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        error_msg = f"Отсутствуют необходимые модули: {', '.join(missing_modules)}\n\n"
        error_msg += "Установите зависимости:\n"
        if 'cv2' in missing_modules:
            error_msg += "pip install opencv-python\n"
        if 'pyaudio' in missing_modules:
            error_msg += "pip install pyaudio\n"
        if 'numpy' in missing_modules:
            error_msg += "pip install numpy\n"
        error_msg += "pip install psutil speedtest-cli"

        app = QApplication([])
        QMessageBox.critical(None, "Ошибка", error_msg)
        return

    app = QApplication([])
    window = SystemDiagnosticsApp()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()