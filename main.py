"""
System Diagnostics Application for Remote Work Capability Assessment

This application performs comprehensive system diagnostics to determine
if a computer meets the requirements for remote work, including:
- Internet speed testing
- Hardware compatibility checks
- Peripheral device verification
- OS and software compatibility
- Automatic FTP upload of results
"""

import os
import platform
import webbrowser
from typing import List, Optional

import psutil
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QFont, QPainter, QPainterPath, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QPushButton, QTextEdit, QFrame,
    QMessageBox, QCheckBox
)

# Import validation with user-friendly error handling
try:
    import speedtest
    import wmi
    import cv2
    import pyaudio
    import numpy
except ImportError as e:
    print(f"Missing required module: {e.name}")

# Local utility imports
import utils.cpu
import utils.gpu
import utils.internet
import utils.peripherals
import utils.system
import utils.ftp

# Application constants
LICENSE_URL = "https://sos.dom.ru/services/license_URM.pdf"
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 750  # Increased height for FTP option
ANIMATION_INTERVAL = 500
MIN_INTERNET_SPEED = 75  # Mbps
MIN_CPU_CORES = 2
MIN_RAM_GB = 4
MIN_SCREEN_WIDTH = 1600
MIN_SCREEN_HEIGHT = 900
MIN_DISK_SPACE_GB = 10
FTP_SERVER = "212.33.255.58"


class RoundedButton(QPushButton):
    """Custom QPushButton with rounded corners styling."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(45)

    def paintEvent(self, event):
        """Custom paint event for rounded button appearance."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        path = QPainterPath()
        radius = 22
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)

        # Determine button color based on state
        if self.isEnabled():
            color = QColor(self.palette().color(self.palette().Dark)) if self.isDown() \
                else QColor(self.palette().color(self.palette().Button))
        else:
            color = QColor(self.palette().color(self.palette().Mid))

        painter.fillPath(path, color)
        painter.setPen(QColor(self.palette().color(self.palette().ButtonText)))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignCenter, self.text())


class DiagnosticsThread(QThread):
    """Background thread for running system diagnostics."""

    # Signals for communicating with main thread
    status_update = pyqtSignal(str)
    text_insert = pyqtSignal(str, str)  # text, color
    diagnostics_complete = pyqtSignal()
    ftp_upload_result = pyqtSignal(bool, str)  # success, message

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance

    def run(self):
        """Execute the complete diagnostics routine."""
        self.app_instance.failed_checks = []

        # Run diagnostics in sequence
        self._test_internet_speed()
        self._test_cpu()
        self._test_network_adapter()
        self._test_os_compatibility()
        self._test_ram()
        self._test_display_gpu()
        self._test_disk_space()
        self._test_microphone()
        self._test_camera()
        self._generate_final_report()

        # Upload results to FTP
        self._upload_results_to_ftp()

        self.status_update.emit("Диагностика завершена")
        self.diagnostics_complete.emit()

    def _upload_results_to_ftp(self):
        """Upload diagnostic results to FTP server."""
        self.status_update.emit("Загружаю результаты на сервер...")

        # Get the diagnostic results text
        content = self.app_instance.text_widget.toPlainText()

        # Attempt FTP upload
        success, error_msg = utils.ftp.upload_diagnostic_results(content, FTP_SERVER)

        if success:
            self.ftp_upload_result.emit(True, "Результаты успешно загружены на сервер")
        else:
            self.ftp_upload_result.emit(False, f"Ошибка загрузки на сервер: {error_msg}")

    def _test_internet_speed(self):
        """Test internet connection speed."""
        self.status_update.emit("[1/4] Измеряю скорость интернета")

        download_speed, upload_speed, ping, error = utils.internet.run_speed_test_safe()

        if error:
            self._log_error(f"Ошибка тестирования скорости: {error}\nЗамерьте скорость вручную на speedtest.net")
            self.app_instance.failed_checks.append(f"internet")
        else:
            if download_speed >= MIN_INTERNET_SPEED:
                self._log_success("Соединение в норме")
            else:
                self._log_failure(
                    f"Проводной интернет с пропускной способностью не менее {MIN_INTERNET_SPEED} Мбит/с")
                self.app_instance.failed_checks.append(
                    f"internet")

            self._log_info(f"Загрузка: {download_speed:.0f} Мбит/с")
            self._log_info(f"Отдача: {upload_speed:.0f} Мбит/с")
            self._log_info(f"Пинг: {ping:.0f} мс")

    def _test_cpu(self):
        """Test CPU specifications."""
        self.status_update.emit("[2/4] Проверяю оборудование (процессор)")

        cpu_name, cpu_cores, cpu_logical_cores = utils.cpu.get_cpu_info()

        if cpu_cores >= MIN_CPU_CORES:
            self._log_success("Процессор в норме")
        else:
            self._log_failure(f"Процессор с не менее чем {MIN_CPU_CORES} ядрами")
            self.app_instance.failed_checks.append(f"cpu")

        self._log_info(f"Модель: {cpu_name}")
        self._log_info(f"Виртуальных ядер: {cpu_logical_cores}")
        self._log_info(f"Физических ядер: {cpu_cores}")

    def _test_network_adapter(self):
        """Test network adapter availability."""
        self.status_update.emit("[2/4] Проверяю оборудование (сетевой адаптер)")

        ethernet_available = utils.internet.check_ethernet_connection()

        if ethernet_available:
            self._log_success("Подключение по кабелю")
            adapters = utils.internet.get_ethernet_adapter_info()
            for adapter in adapters:
                self._log_info(f"Сетевая карта: {adapter['adapter_name']}")
                self._log_info(f"Дуплекс: {adapter['speed']} Мбит/с")
        else:
            self._log_failure("Нет возможности подключения кабелем (Ethernet адаптер отсутствует)")
            self.app_instance.failed_checks.append("ethernet")

    def _test_os_compatibility(self):
        """Test operating system compatibility with Citrix."""
        self.status_update.emit("[2/4] Проверяю оборудование (операционная система)")

        citrix_compatible, version = utils.system.get_citrix_compatibility()

        if citrix_compatible:
            self._log_success("Поддержка Citrix в норме")
        else:
            self._log_failure("Citrix не поддерживается")
            self.app_instance.failed_checks.append("citrix")

        os_version = platform.version().split('.')[2] if '.' in platform.version() else platform.version()
        self._log_info(f"Версия ОС: {platform.system()} {platform.release()} {os_version}")
        self._log_info(f"Версия Citrix: {version}")

    def _test_ram(self):
        """Test RAM specifications."""
        self.status_update.emit("[2/4] Проверяю оборудование (ОЗУ)")

        ram_gb, ram_freq = utils.system.get_ram()

        if ram_gb >= MIN_RAM_GB:
            self._log_success("Память в норме")
        else:
            self._log_failure(f"Оперативная память от {MIN_RAM_GB} ГБ")
            self.app_instance.failed_checks.append(f"ram")

        self._log_info(f"Всего ОЗУ: {ram_gb:.0f} ГБ")
        if ram_freq:
            self._log_info(f"Частота: {ram_freq[0]} МГц")

    def _test_display_gpu(self):
        """Test display and GPU specifications."""
        self.status_update.emit("[2/4] Проверяю оборудование (экран и видеокарта)")

        width = QApplication.desktop().screenGeometry().width()
        height = QApplication.desktop().screenGeometry().height()
        gpu_name = utils.gpu.get_gpu_name()
        gpu_driver = utils.gpu.get_gpu_driver()

        if width >= MIN_SCREEN_WIDTH and height >= MIN_SCREEN_HEIGHT:
            self._log_success("Дисплей в норме")
        else:
            self._log_failure(f"Минимальное разрешение экрана {MIN_SCREEN_WIDTH}x{MIN_SCREEN_HEIGHT} и более")
            self.app_instance.failed_checks.append("resolution")

        self._log_info(f"Разрешение дисплея: {width}x{height}")
        self._log_info(f"Видеокарта: {gpu_name}")
        self._log_info(f"Драйвер: {gpu_driver[0]}")

    def _test_disk_space(self):
        """Test available disk space."""
        self.status_update.emit("[3/4] Проверяю диск")

        disk_usage = psutil.disk_usage("C:")
        free_gb = disk_usage.free / (1024 ** 3)

        if free_gb >= MIN_DISK_SPACE_GB:
            self._log_success("Место на системном диске в норме")
        else:
            self._log_failure("Недостаточно места на диске")
            self.app_instance.failed_checks.append("space")

        self._log_info(f"Свободно: {round(free_gb)} ГБ")

    def _test_microphone(self):
        """Test microphone availability."""
        self.status_update.emit("[4/4] Проверяю периферию (микрофон)")

        mic_available = utils.peripherals.check_microphone()

        if mic_available:
            self._log_success("Микрофон обнаружен")
        else:
            self._log_failure("Микрофон не найден")
            self.app_instance.failed_checks.append("mic")

    def _test_camera(self):
        """Test camera availability and resolution."""
        self.status_update.emit("[4/4] Проверяю периферию (камера)")

        camera_available, cam_width, cam_height = utils.peripherals.check_camera()
        camera_hd = cam_width >= 1280 and cam_height >= 720

        if camera_available and camera_hd:
            self._log_success("Web-камера обнаружена")
            self._log_info(f"Разрешение: {cam_width}x{cam_height}")
        else:
            self._log_failure("Web-камера не соответствует требованиям")
            self.app_instance.failed_checks.append("cam")

    def _generate_final_report(self):
        """Generate final diagnostics report."""
        self.text_insert.emit("\n" + "-" * 70 + "\n", "black")

        if not self.app_instance.failed_checks:
            self._log_success("Все проверки пройдены. ПК соответствует требованиям для удаленной работы")
        else:
            self._log_failure("ПК не соответствует требованиям:")
            self._generate_failure_summary()

    def _generate_failure_summary(self):
        """Generate summary of failed checks."""
        failure_messages = {
            "internet": f"- Скорость интернета > {MIN_INTERNET_SPEED} Мбит/с",
            "cpu": f"- Процессор с не менее чем {MIN_CPU_CORES} ядрами",
            "ethernet": f"- Возможность подключения кабелем Ethernet",
            "citrix": f"- Поддержка приложения Citrix",
            "ram": f"- Оперативная память от {MIN_RAM_GB} ГБ",
            "resolution": f"- Возможность подключения кабелем Ethernet",
            "space": f"- Свободное место на системной диске не менее {MIN_DISK_SPACE_GB} ГБ",
            "mic": "- Наличие микрофона",
            "cam": "- Наличие web-камеры с разрешением не хуже HD (внешней или встроенной)"
        }

        for issue in self.app_instance.failed_checks:
            for keyword, message in failure_messages.items():
                if keyword in issue.lower():
                    self.text_insert.emit(f"{message}\n", 'red')
                    break

    def _log_success(self, message: str):
        """Log a successful check result."""
        self.text_insert.emit(f"[OK] {message}\n", "green")

    def _log_failure(self, message: str):
        """Log a failed check result."""
        self.text_insert.emit(f"[НЕ OK] {message}\n", "red")

    def _log_error(self, message: str):
        """Log an error message."""
        self.text_insert.emit(f"{message}\n", 'red')

    def _log_info(self, message: str):
        """Log an informational message."""
        self.text_insert.emit(f"     {message}\n", "black")


class SystemDiagnosticsApp(QMainWindow):
    """Main application window for system diagnostics."""

    def __init__(self):
        super().__init__()
        self.failed_checks: List[str] = []
        self.diagnostics_complete = False
        self.test_started = False
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_dots = 0
        self.base_status_text = ""

        self._init_ui()
        self._show_initial_message()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Диагностика возможности удаленной работы")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet("background-color: #f0eded;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self._create_header(main_layout)
        self._create_main_panel(main_layout)
        self._create_ftp_option(main_layout)
        self._create_button_panel(main_layout)
        self._create_bottom_panel(main_layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create the application header with logo and title."""
        header_frame = QFrame()
        header_frame.setFixedHeight(65)
        header_frame.setStyleSheet("background-color: #f0eded;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 10, 0, 10)

        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), 'assets/logo.png')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
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

    def _create_main_panel(self, parent_layout: QVBoxLayout):
        """Create the main content panel with text area and status."""
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

        # Text display area
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

        # Status label
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Arial", 10, QFont.StyleItalic))
        self.status_label.setStyleSheet("color: gray; padding: 5px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()
        main_frame_layout.addWidget(self.status_label)

        parent_layout.addWidget(self.main_frame)

    def _create_ftp_option(self, parent_layout: QVBoxLayout):
        """Create the FTP upload option checkbox."""
        ftp_frame = QFrame()
        ftp_frame.setStyleSheet("background-color: #f0eded;")
        ftp_layout = QHBoxLayout(ftp_frame)
        ftp_layout.setContentsMargins(10, 5, 10, 5)

        ftp_layout.addStretch()
        parent_layout.addWidget(ftp_frame)

    def _create_button_panel(self, parent_layout: QVBoxLayout):
        """Create the button panel with start, copy, and restart buttons."""
        button_frame = QFrame()
        button_frame.setStyleSheet("background-color: #f0eded;")
        button_layout = QVBoxLayout(button_frame)
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setContentsMargins(10, 10, 10, 10)

        # Start button
        self.start_button = RoundedButton("Начать тест")
        self.start_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.start_button.setStyleSheet(self._get_button_style("#FF312C", "#e02e29", "#c52821"))
        self.start_button.clicked.connect(self.start_test)
        button_layout.addWidget(self.start_button)

        # Result buttons
        self._create_result_buttons(button_layout)
        parent_layout.addWidget(button_frame)

    def _create_result_buttons(self, parent_layout: QVBoxLayout):
        """Create copy and restart buttons."""
        result_buttons_frame = QFrame()
        result_buttons_layout = QHBoxLayout(result_buttons_frame)
        result_buttons_layout.setAlignment(Qt.AlignCenter)

        # Copy button
        self.copy_button = RoundedButton("Скопировать результат")
        self.copy_button.setFont(QFont("Arial", 10, QFont.Bold))
        self.copy_button.setStyleSheet(self._get_button_style("#4CAF50", "#45a049", "#3d8b40"))
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.hide()

        # Restart button
        self.restart_button = RoundedButton("Перезапустить тест")
        self.restart_button.setFont(QFont("Arial", 10, QFont.Bold))
        self.restart_button.setStyleSheet(self._get_button_style("#2196F3", "#1976D2", "#1565C0"))
        self.restart_button.clicked.connect(self.restart_test)
        self.restart_button.hide()

        result_buttons_layout.addWidget(self.copy_button)
        result_buttons_layout.addSpacing(10)
        result_buttons_layout.addWidget(self.restart_button)

        parent_layout.addWidget(result_buttons_frame)

    def _create_bottom_panel(self, parent_layout: QVBoxLayout):
        """Create the bottom panel with license agreement link."""
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background-color: #f0eded;")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(10, 10, 10, 10)

        prefix_label = QLabel("Используя данную программу вы принимаете")
        prefix_label.setFont(QFont("Arial", 9))
        prefix_label.setStyleSheet("color: #333;")
        bottom_layout.addWidget(prefix_label)

        link_label = QLabel(
            '<a href="#" style="color: #0066cc; text-decoration: underline;">условия пользовательского соглашения</a>'
        )
        link_label.setFont(QFont("Arial", 9))
        link_label.linkActivated.connect(lambda: webbrowser.open_new(LICENSE_URL))
        bottom_layout.addWidget(link_label)

        bottom_layout.addStretch()
        parent_layout.addWidget(bottom_frame)

    def _get_button_style(self, normal_color: str, hover_color: str, pressed_color: str) -> str:
        """Generate button stylesheet with specified colors."""
        return f"""
            QPushButton {{
                background-color: {normal_color};
                color: white;
                border: none;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
        """

    def _show_initial_message(self):
        """Display the initial welcome message."""
        messages = [
            "Добро пожаловать в программу диагностики возможности удаленной работы!\n",
            "Эта программа проверит:",
            "• Скорость интернет-соединения",
            "• Параметры процессора и оперативной памяти",
            "• Сетевое оборудование",
            "• Дисплей и видеокарту",
            "• Свободное место на системном диске",
            "• Наличие микрофона и веб-камеры\n",
            "Готовы начать тестирование? Нажмите кнопку 'Начать тест'."
        ]

        for message in messages:
            self.text_widget.append(message)

    def start_test(self):
        """Start the diagnostics test."""
        if not self.test_started:
            self.test_started = True
            self.start_button.hide()
            self.text_widget.clear()
            self._run_diagnostics()

    def restart_test(self):
        """Restart the diagnostics test."""
        self.animation_timer.stop()
        self.diagnostics_complete = False
        self.test_started = True
        self.failed_checks = []

        self.copy_button.hide()
        self.restart_button.hide()
        self.text_widget.clear()
        self._run_diagnostics()

    def _run_diagnostics(self):
        """Execute diagnostics in a separate thread."""
        self.diagnostics_thread = DiagnosticsThread(self)
        self.diagnostics_thread.status_update.connect(self._update_status)
        self.diagnostics_thread.text_insert.connect(self._insert_text)
        self.diagnostics_thread.diagnostics_complete.connect(self._on_diagnostics_complete)
        self.diagnostics_thread.ftp_upload_result.connect(self._handle_ftp_upload_result)
        self.diagnostics_thread.start()

    def _update_status(self, message: str):
        """Update the status display with animation."""
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
                self.animation_timer.start(ANIMATION_INTERVAL)

    def _update_animation(self):
        """Update the animated dots in status message."""
        dots = "." * ((self.animation_dots % 3) + 1)
        self.status_label.setText(f"{self.base_status_text}{dots}")
        self.animation_dots += 1

    def _insert_text(self, text: str, color: str):
        """Insert colored text into the display widget."""
        color_map = {
            "green": QColor("#008000"),
            "red": QColor("#FF0000"),
            "black": QColor("black")
        }

        self.text_widget.setTextColor(color_map.get(color, QColor("black")))
        self.text_widget.insertPlainText(text)
        self.text_widget.moveCursor(self.text_widget.textCursor().End)

    def _on_diagnostics_complete(self):
        """Handle completion of diagnostics."""
        self.diagnostics_complete = True
        self.copy_button.show()
        self.restart_button.show()

    def _handle_ftp_upload_result(self, success: bool, message: str):
        """Handle FTP upload result."""
        if success:
            self._insert_text(f"\n[OK] {message}\n", "green")
        else:
            self._insert_text(f"\n[Предупреждение] {message}\n", "red")

    def copy_to_clipboard(self):
        """Copy diagnostics results to clipboard."""
        if self.diagnostics_complete:
            content = self.text_widget.toPlainText()
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            QMessageBox.information(self, "Копирование", "Результаты диагностики скопированы в буфер обмена")
        else:
            QMessageBox.warning(self, "Предупреждение", "Диагностика еще не завершена")


def validate_dependencies() -> Optional[str]:
    """Validate that required modules are available."""
    required_modules = {
        'psutil': 'psutil',
        'speedtest': 'speedtest-cli',
        'cv2': 'opencv-python',
        'pyaudio': 'pyaudio',
        'numpy': 'numpy'
    }

    missing_modules = []
    for module, package in required_modules.items():
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(package)

    if missing_modules:
        return f"""Отсутствуют необходимые модули: {', '.join(missing_modules)}

Установите зависимости:
pip install {' '.join(missing_modules)}"""

    return None


def main():
    """Main application entry point."""
    # Validate dependencies
    dependency_error = validate_dependencies()
    if dependency_error:
        app = QApplication([])
        QMessageBox.critical(None, "Ошибка", dependency_error)
        return

    # Launch application
    app = QApplication([])
    window = SystemDiagnosticsApp()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()