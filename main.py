import os
import platform
import threading
import time
import webbrowser
import sys

import psutil
import pythoncom
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QScrollArea, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QFont, QTextCursor, QClipboard

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


class DiagnosticsThread(QThread):
    status_update = pyqtSignal(str)
    text_insert = pyqtSignal(str, str)  # text, color
    diagnostics_complete = pyqtSignal(list)  # failed_checks

    def __init__(self):
        super().__init__()
        self.failed_checks = []

    def run(self):
        self.failed_checks = []

        # Internet speed test
        self.status_update.emit("[1/4] Измеряю скорость интернета")
        download_speed, upload_speed, ping, error = utils.internet.run_speed_test_safe()

        if error:
            self.text_insert.emit(
                f"Ошибка тестирования скорости: {error}\nЗамерьте скорость вручную на speedtest.net\n", 'red')
            self.failed_checks.append("Проводной интернет с пропускной способностью не менее 75 Мбит/с")
        else:
            if download_speed >= 75:
                self.text_insert.emit("[OK] Соединение в норме\n", "green")
            else:
                self.text_insert.emit(
                    "[НЕ OK] Проводной интернет по технологии FTTx, xPON с пропускной способностью не менее 75 Мбит/с\n",
                    "red")
                self.failed_checks.append(
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
            self.failed_checks.append("Процессор с не менее чем двумя ядрами")

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
            self.failed_checks.append("Нет возможности подключения кабелем (Ethernet адаптер отсутствует)")

        # OS compatibility check
        self.status_update.emit("[2/4] Проверяю оборудование (операционная система)")
        citrix_compatible, version = utils.system.get_citrix_compatibility()

        if citrix_compatible:
            self.text_insert.emit("[OK] Поддержка Citrix в норме\n", "green")
        else:
            self.text_insert.emit("[НЕ OK] Citrix не поддерживается\n", "red")
            self.failed_checks.append("Citrix не поддерживается")

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
            self.failed_checks.append("Оперативная память от 4 ГБ")

        self.text_insert.emit(f"     Всего ОЗУ: {ram_gb:.0f} ГБ\n", "black")
        if ram_freq_list:
            self.text_insert.emit(f"     Частота: {ram_freq_list[0]} МГц\n", "black")

        # Display and GPU check
        self.status_update.emit("[2/4] Проверяю оборудование (экран и видеокарта)")
        # Note: For PyQt6, we'll get screen resolution differently
        app = QApplication.instance()
        if app:
            screen = app.primaryScreen()
            size = screen.size()
            width, height = size.width(), size.height()
        else:
            width, height = 1920, 1080  # fallback

        gpu_name = utils.gpu.get_gpu_name()

        if width >= 1600 and height >= 900:
            self.text_insert.emit("[OK] Дисплей в норме\n", "green")
        else:
            self.text_insert.emit("[НЕ OK] Минимальное разрешение экрана 1600х900 и более\n", "red")
            self.failed_checks.append("Минимальное разрешение экрана 1600х900 и более")

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
            self.failed_checks.append("Недостаточно места на диске")

        self.text_insert.emit(f"     Свободно: {round(free_gb)} ГБ\n", "black")

        # Microphone check
        self.status_update.emit("[4/4] Проверяю периферию (микрофон)")
        mic_available = utils.peripherals.check_microphone()

        if mic_available:
            self.text_insert.emit("[OK] Микрофон обнаружен\n", "green")
        else:
            self.text_insert.emit("[НЕ OK] Микрофон не найден\n", "red")
            self.failed_checks.append("Микрофон не найден")

        # Camera check
        self.status_update.emit("[4/4] Проверяю периферию (камера)")
        camera_available, cam_width, cam_height = utils.peripherals.check_camera()
        camera_hd = cam_width >= 1280 and cam_height >= 720

        if camera_available and camera_hd:
            self.text_insert.emit("[OK] Web-камера обнаружена\n", "green")
            self.text_insert.emit(f"      Разрешение: {cam_width}x{cam_height}\n", "black")
        else:
            self.text_insert.emit("[НЕ OK] Web-камера не соответствует требованиям\n", "red")
            self.failed_checks.append("Web-камера не соответствует требованиям")

        # Final results
        self.text_insert.emit("\n" + "-" * 70 + "\n", "black")

        if not self.failed_checks:
            self.text_insert.emit("Все проверки пройдены. ПК соответствует требованиям для удаленной работы\n", 'green')
        else:
            self.text_insert.emit("ПК не соответствует требованиям:\n", 'red')
            for issue in self.failed_checks:
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

        self.diagnostics_complete.emit(self.failed_checks)


class SystemDiagnosticsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.diagnostics_complete = False
        self.test_started = False
        self.failed_checks = []

        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_status)
        self.animation_dots = 0
        self.base_status_message = ""

        self.diagnostics_thread = None

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
        main_layout.setContentsMargins(10, 10, 10, 10)

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
        header_layout.setContentsMargins(0, 10, 10, 10)

        # Logo
        logo_label = QLabel()
        logopath = os.path.join(os.path.dirname(__file__), 'assets/logo.png')
        if os.path.exists(logopath):
            pixmap = QPixmap(logopath)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("LOGO")
            logo_label.setStyleSheet("background-color: #cccccc; border: 1px solid black;")
            logo_label.setFixedSize(50, 45)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(logo_label)

        # Title
        title_label = QLabel("Диагностика возможности удаленной работы")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: black; background-color: #f0eded;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()
        parent_layout.addWidget(header_frame)

    def create_main_panel(self, parent_layout):
        main_frame = QFrame()
        main_frame.setStyleSheet("background-color: white; border: 2px raised;")

        main_layout = QVBoxLayout(main_frame)
        main_layout.setContentsMargins(20, 20, 20, 10)

        # Text widget
        self.text_widget = QTextEdit()
        self.text_widget.setFont(QFont("Arial", 10))
        self.text_widget.setStyleSheet("background-color: white; border: none;")
        self.text_widget.setReadOnly(True)

        main_layout.addWidget(self.text_widget)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setStyleSheet("color: gray; font-style: italic; background-color: white;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(self.status_label)

        parent_layout.addWidget(main_frame)

    def create_button_panel(self, parent_layout):
        button_frame = QFrame()
        button_frame.setFixedHeight(60)
        button_frame.setStyleSheet("background-color: #f0eded;")

        button_layout = QVBoxLayout(button_frame)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Start button
        self.start_button = QPushButton("Начать тест")
        self.start_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #FF312C;
                color: white;
                border: none;
                padding: 10px 30px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e02823;
            }
            QPushButton:pressed {
                background-color: #c61f1b;
            }
        """)
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.clicked.connect(self.start_test)

        button_layout.addWidget(self.start_button)

        # Container for copy and restart buttons
        button_container = QWidget()
        container_layout = QHBoxLayout(button_container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Copy button
        self.copy_button = QPushButton("Скопировать результат")
        self.copy_button.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.hide()

        # Restart button
        self.restart_button = QPushButton("Перезапустить тест")
        self.restart_button.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.restart_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.restart_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restart_button.clicked.connect(self.restart_test)
        self.restart_button.hide()

        container_layout.addWidget(self.copy_button)
        container_layout.addWidget(self.restart_button)

        button_layout.addWidget(button_container)
        parent_layout.addWidget(button_frame)

    def create_bottom_panel(self, parent_layout):
        bottom_frame = QFrame()
        bottom_frame.setFixedHeight(30)
        bottom_frame.setStyleSheet("background-color: #f0eded;")

        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 5, 0, 5)

        prefix_label = QLabel("Используя данную программу вы принимаете")
        prefix_label.setFont(QFont("Arial", 10))
        prefix_label.setStyleSheet("background-color: #f0eded;")

        link_label = QLabel("условия пользовательского соглашения")
        link_label.setFont(QFont("Arial", 10))
        link_label.setStyleSheet("color: blue; text-decoration: underline; background-color: #f0eded;")
        link_label.setCursor(Qt.CursorShape.PointingHandCursor)
        link_label.mousePressEvent = lambda event: webbrowser.open_new(LICENSE_URL)

        bottom_layout.addWidget(prefix_label)
        bottom_layout.addWidget(link_label)
        bottom_layout.addStretch()

        parent_layout.addWidget(bottom_frame)

    def show_initial_message(self):
        """Show initial message asking user if they're ready to start the test."""
        self.insert_text("Добро пожаловать в программу диагностики возможности удаленной работы!\n\n")
        self.insert_text("Эта программа проверит:\n")
        self.insert_text("• Скорость интернет-соединения\n")
        self.insert_text("• Параметры процессора и оперативной памяти\n")
        self.insert_text("• Сетевое оборудование\n")
        self.insert_text("• Дисплей и видеокарту\n")
        self.insert_text("• Свободное место на системном диске\n")
        self.insert_text("• Наличие микрофона и веб-камеры\n\n")
        self.insert_text("Готовы начать тестирование? Нажмите кнопку 'Начать тест'.\n")

    def start_test(self):
        """Start the diagnostic test."""
        if not self.test_started:
            self.test_started = True
            self.start_button.hide()
            self.clear_text()
            self.run_full_diagnostics()

    def restart_test(self):
        """Restart the diagnostic test."""
        self.animation_timer.stop()
        self.diagnostics_complete = False
        self.test_started = True
        self.failed_checks = []

        # Hide result buttons
        self.copy_button.hide()
        self.restart_button.hide()

        self.clear_text()
        self.run_full_diagnostics()

    def clear_text(self):
        """Clear the text widget."""
        self.text_widget.clear()

    def show_result_buttons(self):
        """Show copy and restart buttons after test completion."""
        self.copy_button.show()
        self.restart_button.show()

    def update_status(self, message: str):
        """Update progress/status label with animation."""
        self.animation_timer.stop()

        if message == "Диагностика завершена" or message == "":
            self.status_label.setText(message)
        else:
            self.base_status_message = message
            self.animation_dots = 0
            self.animation_timer.start(500)  # 500ms interval

    def animate_status(self):
        """Animate dots after status message."""
        dots = [".", "..", "..."]
        current_message = f"{self.base_status_message}{dots[self.animation_dots]}"
        self.status_label.setText(current_message)
        self.animation_dots = (self.animation_dots + 1) % len(dots)

    def insert_text(self, text: str, color: str = "black"):
        """Insert text with specified color."""
        cursor = self.text_widget.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if color == "green":
            self.text_widget.setStyleSheet("color: #008000;")
        elif color == "red":
            self.text_widget.setStyleSheet("color: #FF0000;")
        else:
            self.text_widget.setStyleSheet("color: black;")

        cursor.insertText(text)
        self.text_widget.setTextCursor(cursor)
        self.text_widget.ensureCursorVisible()

        # Reset color to black for next insertion
        self.text_widget.setStyleSheet("color: black;")

    def run_full_diagnostics(self):
        """Start diagnostics in separate thread."""
        self.diagnostics_thread = DiagnosticsThread()
        self.diagnostics_thread.status_update.connect(self.update_status)
        self.diagnostics_thread.text_insert.connect(self.insert_text)
        self.diagnostics_thread.diagnostics_complete.connect(self.on_diagnostics_complete)
        self.diagnostics_thread.start()

    def on_diagnostics_complete(self, failed_checks):
        """Handle diagnostics completion."""
        self.failed_checks = failed_checks
        self.update_status("Диагностика завершена")
        self.diagnostics_complete = True
        self.show_result_buttons()

    def copy_to_clipboard(self):
        """Copy results to clipboard."""
        if self.diagnostics_complete:
            content = self.text_widget.toPlainText()
            clipboard = QApplication.clipboard()
            clipboard.setText(content)

            msg = QMessageBox()
            msg.setWindowTitle("Копирование")
            msg.setText("Результаты диагностики скопированы в буфер обмена")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
        else:
            msg = QMessageBox()
            msg.setWindowTitle("Предупреждение")
            msg.setText("Диагностика еще не завершена")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()


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

        app = QApplication(sys.argv)
        msg = QMessageBox()
        msg.setWindowTitle("Ошибка")
        msg.setText(error_msg)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.exec()
        return

    app = QApplication(sys.argv)
    window = SystemDiagnosticsApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()