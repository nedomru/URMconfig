import os
import platform
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

import psutil
import pythoncom
from PIL import Image, ImageTk  # Import Image and ImageTk from Pillow

# Updated import for speedtest-cli
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


class SystemDiagnosticsApp:
    def __init__(self, root):
        self.logo_image = None
        self.root = root
        self.root.title("Диагностика возможности удаленной работы")
        self.root.geometry("600x700")
        self.root.configure(bg='#f0eded')  # Orange background like in screenshot
        self.root.resizable(False, False)

        self.diagnostics_complete = False
        self.all_results = []
        self.failed_checks = []

        # Add icon placeholder (you can add actual icon)
        self.create_header()
        self.create_main_panel()
        self.create_bottom_panel()

        # Start diagnostics automatically including speed test
        self.run_full_diagnostics()

    def create_header(self):
        """Create header with logo and title"""
        header_frame = tk.Frame(self.root, bg='#f0eded', height=80)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)

        original_image = Image.open("assets/logo.png")

        # Resize the image if necessary (e.g., to fit the 60x40 area or your desired size)
        # You might need to adjust these dimensions based on your actual logo size and desired display
        resized_image = original_image.resize((60, 40), Image.Resampling.LANCZOS)

        # Convert the Pillow image to a Tkinter PhotoImage
        self.logo_image = ImageTk.PhotoImage(resized_image)

        # Create a Label to display the image
        logo_label = tk.Label(header_frame, image=self.logo_image, bg='#f0eded')
        logo_label.pack(side='left', padx=(0, 10), pady=10)

        # Title
        title_label = tk.Label(header_frame, text="Диагностика возможности удаленной работы",
                               bg='#f0eded', fg='black', font=('Arial', 14, 'bold'))
        title_label.pack(side='left', pady=20)

    def create_main_panel(self):
        """Create main white panel with diagnostics results"""
        self.main_frame = tk.Frame(self.root, bg='white', relief='raised', bd=2)
        self.main_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Scrollable text area
        self.text_frame = tk.Frame(self.main_frame, bg='white')
        self.text_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Create text widget with scrollbar
        self.text_widget = tk.Text(self.text_frame, font=('Arial', 10), bg='white',
                                   relief='flat', wrap='word', state='disabled')
        scrollbar = tk.Scrollbar(self.text_frame, orient='vertical', command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)

        self.text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def create_bottom_panel(self):
        """Create bottom panel with execute button and progress"""
        bottom_frame = tk.Frame(self.root, bg='#f0eded', height=50)
        bottom_frame.pack(fill='x', padx=15, pady=(0, 15))
        bottom_frame.pack_propagate(False)

        # User agreement text
        agreement_text = "Используя данную программу вы принимаете условия пользовательского соглашения"
        agreement_label = tk.Label(bottom_frame, text=agreement_text, bg='#f0eded',
                                   font=('Arial', 10), wraplength=500)
        agreement_label.pack(anchor='center', pady=5)

    def insert_text(self, text, color='black'):
        """Insert text into the text widget"""
        self.text_widget.config(state='normal')

        # Create tag for color
        tag_name = f"color_{color}"
        if color == 'green':
            self.text_widget.tag_configure(tag_name, foreground='#008000')
        elif color == 'red':
            self.text_widget.tag_configure(tag_name, foreground='#FF0000')
        else:
            self.text_widget.tag_configure(tag_name, foreground='black')

        self.text_widget.insert(tk.END, text, tag_name)
        self.all_results.append((text, color))
        self.text_widget.config(state='disabled')
        self.text_widget.see(tk.END)
        self.root.update()

    def check_status(self, condition, ok_text, fail_text):
        """Check condition and return appropriate status text"""
        if condition:
            return f"[OK] {ok_text}\n", 'green'
        else:
            self.failed_checks.append(fail_text)
            return f"[НЕ OK] {fail_text}\n", 'red'

    def run_speed_test_safe(self):
        """Safe speed test with error handling for PyInstaller"""
        try:
            # Fix for PyInstaller - redirect stdin/stdout
            if getattr(sys, 'frozen', False):
                # Running in PyInstaller bundle
                sys.stdin = open(os.devnull, 'r')
                sys.stdout = open(os.devnull, 'w')
                sys.stderr = open(os.devnull, 'w')

            st = speedtest.Speedtest()
            st.get_best_server()

            download_speed = st.download() / 1024 / 1024  # в Мбит/с
            upload_speed = st.upload() / 1024 / 1024
            ping = st.results.ping

            return download_speed, upload_speed, ping, None

        except Exception as e:
            return 0, 0, 0, str(e)

    def run_full_diagnostics(self):
        """Run complete system diagnostics including speed test"""

        def full_diagnostics_thread():
            self.insert_text("Выполняется диагностика системы...\n\n")
            time.sleep(1)

            # 1. Internet Speed Test (FTTx, xPON >= 75Mbps)
            self.insert_text("Тестирование скорости интернета...\n")

            download_speed, upload_speed, ping, error = self.run_speed_test_safe()

            if error:
                self.insert_text(f"Ошибка тестирования скорости: {error}\nЗамерьте скорость вручную на speedtest.net\n",
                                 'red')
                self.failed_checks.append(
                    "Проводной интернет с пропускной способностью не менее 75 Мбит/с"
                )
            else:
                # Сначала определяем статус, чтобы вывести его первым
                status_text, status_color = self.check_status(
                    download_speed >= 75,
                    "Соединение в норме:",
                    "Проводной интернет по технологии FTTx, xPON с пропускной способностью не менее 75 Мбит/с"
                )

                # 1) Статус
                self.insert_text(f"{status_text}", status_color)

                # 2) Показатели (без дробной части)
                self.insert_text(f"     Загрузка: {download_speed:.0f} Мбит/с\n")
                self.insert_text(f"     Отдача:  {upload_speed:.0f} Мбит/с\n")
                self.insert_text(f"     Пинг:  {ping:.0f} мс\n")

            # 2. CPU cores check (>= 2 cores)
            cpu_name = utils.cpu.get_cpu_name()
            cpu_cores = psutil.cpu_count(logical=False)
            logical_cores = psutil.cpu_count(logical=True)

            text, color = self.check_status(
                cpu_cores >= 2,
                f"Процессор в норме",
                "Процессор с не менее чем двумя ядрами"
            )
            self.insert_text(text, color)

            self.insert_text(f"     Модель: {cpu_name}\n")
            self.insert_text(f"     Виртуальных ядер: {logical_cores}\n")
            self.insert_text(f"     Физических ядер: {cpu_cores}\n")

            # 3. Ethernet cable connection capability
            ethernet_available = utils.internet.check_ethernet_connection()
            text, color = self.check_status(
                ethernet_available,
                "Подключение по кабелю",
                "Нет возможности подключения кабелем (Ethernet адаптер отсутствует)"
            )

            if ethernet_available:
                self.insert_text(text, color)

                # Get ethernet adapter details
                adapters = utils.internet.get_ethernet_adapter_info()

                for adapter in adapters:
                    self.insert_text(f"     Сетевая карта: {adapter['adapter_name']}\n")
                    self.insert_text(f"     Дуплекс: {adapter['speed']} Мбит/с\n")
            else:
                self.insert_text(text, color)

            # 4. Operating System check
            citrix_compatible, os_info = utils.system.get_citrix_compatibility()
            text, color = self.check_status(
                citrix_compatible,
                f"Поддержка Citrix в норме",
                "Citrix не поддерживается"
            )
            self.insert_text(text, color)
            self.insert_text(
                f"     Версия ОС: {platform.system()} {platform.release()} {platform.version().split('.')[2]} \n")

            # 5. RAM check (>= 4 GB)
            ram_gb = psutil.virtual_memory().total / (1024 ** 3)
            pythoncom.CoInitialize()
            c = wmi.WMI()
            ram_freq_list = []
            for mem in c.Win32_PhysicalMemory():
                ram_freq_list.append(mem.Speed)
            pythoncom.CoUninitialize()
            text, color = self.check_status(
                ram_gb >= 4,
                f"Память в норме:",
                "Оперативная память от 4 ГБ"
            )
            self.insert_text(text, color)
            self.insert_text(f"     Всего ОЗУ: {ram_gb:.0f} ГБ\n")

            if ram_freq_list:
                self.insert_text(f"     Частота: {ram_freq_list[0]} МГц\n")

            # 6. Display resolution check (>= 1600x900)
            width, height = utils.system.get_screen_resolution(self)
            gpu_name = utils.gpu.get_gpu_name()
            text, color = self.check_status(
                width >= 1600 and height >= 900,
                f"Дисплей в норме",
                "Минимальное разрешение экрана 1600х900 и более"
            )
            self.insert_text(text, color)
            self.insert_text(f"     Разрешение дисплея: {width}x{height}\n")
            self.insert_text(f"     Видеокарта: {gpu_name}\n")

            # 7. Disk space check
            disk_usage = psutil.disk_usage("C:")
            free_gb = disk_usage.free / (1024 ** 3)
            text, color = self.check_status(
                free_gb >= 10,
                "Место на системном диске в норме",
                "Недостаточно места на диске"
            )
            self.insert_text(text, color)
            self.insert_text(f"     Свободно: {round(free_gb)} ГБ\n")

            # 11. Microphone check
            mic_available = utils.peripherals.check_microphone()
            text, color = self.check_status(
                mic_available,
                "Микрофон обнаружен",
                "Гарнитура – микрофон и наушники"
            )
            self.insert_text(text, color)

            if not mic_available:
                self.failed_checks.append(
                    "Микрофон"
                )

            # 12. Camera check
            camera_available, cam_width, cam_height = utils.peripherals.check_camera()
            camera_hd = cam_width >= 1280 and cam_height >= 720
            text, color = self.check_status(
                camera_available and camera_hd,
                "Web-камера обнаружена",
                "Web-камера не соответствует требованиям"
            )
            self.insert_text(text, color)

            if camera_available and camera_hd:
                self.insert_text(f"      Разрешение: {cam_width}x{cam_height}")

            # Add separator
            self.insert_text("\n" + "-" * 70 + "\n")

            # Final assessment
            if not self.failed_checks:
                self.insert_text("Все проверки пройдены. ПК соответствует требованиям для удаленной работы\n",
                                 'green')
            else:
                self.insert_text("ПК не соответствует требованиям:\n", 'red')

                # Show what needs to be fixed
                for issue in self.failed_checks:
                    if "процессор" in issue.lower():
                        self.insert_text("- Требуется обновить процессор\n", 'red')
                    elif "память" in issue.lower():
                        self.insert_text("- Информация о памяти не получена\n", 'red')
                    elif "кабель" in issue.lower() or "интернет" in issue.lower():
                        self.insert_text(
                            "- Скорость интернета > 75 Мбит/с\n", 'red')
                    elif "микрофон" in issue.lower():
                        self.insert_text(
                            "- Наличие микрофона\n", 'red')
                    elif "web-камера" in issue.lower():
                        self.insert_text(
                            "- Наличие web-камеры с разрешением не хуже HD (внешней или встроенной)\n", 'red')

            self.diagnostics_complete = True

        threading.Thread(target=full_diagnostics_thread, daemon=True).start()

    def copy_to_clipboard(self):
        """Copy diagnostics results to clipboard"""
        if self.diagnostics_complete:
            # Get all text from the text widget
            self.text_widget.config(state='normal')
            content = self.text_widget.get(1.0, tk.END)
            self.text_widget.config(state='disabled')

            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.root.update()

            messagebox.showinfo("Копирование", "Результаты диагностики скопированы в буфер обмена")
        else:
            messagebox.showwarning("Предупреждение", "Диагностика еще не завершена")


def main():
    # Check for required modules
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

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Ошибка", error_msg)
        return

    root = tk.Tk()
    app = SystemDiagnosticsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
