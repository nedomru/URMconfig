import os
import platform
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox

import psutil
import pythoncom
from PIL import Image, ImageTk

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


class SystemDiagnosticsApp:
    def __init__(self, root):
        self.logo_image = None
        self.root = root
        self.root.title("Диагностика возможности удаленной работы")
        self.root.geometry("600x700")
        self.root.configure(bg="#f0eded")
        self.root.resizable(False, False)

        self.diagnostics_complete = False
        self.test_started = False
        self.all_results = []
        self.failed_checks = []

        self.status_label = None
        self.start_button = None
        self.copy_button = None
        self.restart_button = None

        self.create_header()
        self.create_main_panel()
        self.create_button_panel()
        self.create_bottom_panel()

        # Show initial message
        self.show_initial_message()

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def create_header(self):
        header_frame = tk.Frame(self.root, bg="#f0eded", height=80)
        header_frame.pack(fill="x", padx=10, pady=10)
        header_frame.pack_propagate(False)

        logopath = os.path.join(os.path.dirname(__file__), 'assets/logo.png')
        original_image = Image.open(logopath)
        resized_image = original_image.resize((60, 40), Image.Resampling.LANCZOS)
        self.logo_image = ImageTk.PhotoImage(resized_image)

        logo_label = tk.Label(header_frame, image=self.logo_image, bg="#f0eded")
        logo_label.pack(side="left", padx=(0, 10), pady=10)

        title_label = tk.Label(
            header_frame,
            text="Диагностика возможности удаленной работы",
            bg="#f0eded",
            fg="black",
            font=("Arial", 14, "bold"),
        )
        title_label.pack(side="left", pady=20)

    def create_main_panel(self):
        self.main_frame = tk.Frame(self.root, bg="white", relief="raised", bd=2)
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.text_frame = tk.Frame(self.main_frame, bg="white")
        self.text_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.status_label = tk.Label(
            self.main_frame,
            text="",
            bg="white",
            fg="gray",
            font=("Arial", 10, "italic"),
        )
        self.status_label.pack(fill="x", pady=(0, 10))

        self.text_widget = tk.Text(
            self.text_frame,
            font=("Arial", 10),
            bg="white",
            relief="flat",
            wrap="word",
            state="disabled",
        )
        scrollbar = tk.Scrollbar(self.text_frame, orient="vertical", command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)

        self.text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_button_panel(self):
        self.button_frame = tk.Frame(self.root, bg="#f0eded", height=60)
        self.button_frame.pack(fill="x", padx=15, pady=(0, 10))
        self.button_frame.pack_propagate(False)

        # Start test button (red rounded button)
        self.start_button = tk.Button(
            self.button_frame,
            text="Начать тест",
            bg="#FF312C",
            fg="white",
            font=("Arial", 12, "bold"),
            relief="flat",
            bd=0,
            padx=30,
            pady=10,
            command=self.start_test,
            cursor="hand2"
        )
        self.start_button.pack(pady=15)

        # Copy and restart buttons (initially hidden)
        button_container = tk.Frame(self.button_frame, bg="#f0eded")
        button_container.pack(pady=15)

        self.copy_button = tk.Button(
            button_container,
            text="Скопировать результат",
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            command=self.copy_to_clipboard,
            cursor="hand2"
        )

        self.restart_button = tk.Button(
            button_container,
            text="Перезапустить тест",
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            command=self.restart_test,
            cursor="hand2"
        )

        self.copy_button.pack(side="left", padx=(0, 10))
        self.restart_button.pack(side="left")

        # Initially hide copy and restart buttons
        self.copy_button.pack_forget()
        self.restart_button.pack_forget()

    def create_bottom_panel(self):
        bottom_frame = tk.Frame(self.root, bg="#f0eded", height=70)
        bottom_frame.pack(fill="x", padx=15, pady=(0, 15))
        bottom_frame.pack_propagate(False)

        prefix_label = tk.Label(
            bottom_frame,
            text="Используя данную программу вы принимаете",
            bg="#f0eded",
            font=("Arial", 10),
        )
        prefix_label.pack(side="left")

        link_label = tk.Label(
            bottom_frame,
            text="условия пользовательского соглашения",
            fg="blue",
            cursor="hand2",
            bg="#f0eded",
            font=("Arial", 10, "underline"),
        )
        link_label.pack(side="left")
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new(LICENSE_URL))

    def show_initial_message(self):
        """Show initial message asking user if they're ready to start the test."""
        self.insert_text("Добро пожаловать в программу диагностики возможности удаленной работы!\n\n")
        self.insert_text("Эта программа проверит:\n")
        self.insert_text("• Скорость интернет-соединения\n")
        self.insert_text("• Параметры процессора и оперативной памяти\n")
        self.insert_text("• Сетевое оборудование\n")
        self.insert_text("• Дисплей и видеокарту\n")
        self.insert_text("• Свободное место на диске\n")
        self.insert_text("• Наличие микрофона и веб-камеры\n\n")
        self.insert_text("Готовы начать тестирование? Нажмите кнопку 'Начать тест'.\n")

    def start_test(self):
        """Start the diagnostic test."""
        if not self.test_started:
            self.test_started = True
            self.start_button.pack_forget()  # Hide start button
            self.clear_text()
            self.run_full_diagnostics()

    def restart_test(self):
        """Restart the diagnostic test."""
        self.diagnostics_complete = False
        self.test_started = True
        self.failed_checks = []
        self.all_results = []

        # Hide copy and restart buttons
        self.copy_button.pack_forget()
        self.restart_button.pack_forget()

        self.clear_text()
        self.run_full_diagnostics()

    def clear_text(self):
        """Clear the text widget."""
        self.text_widget.config(state="normal")
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.config(state="disabled")

    def show_result_buttons(self):
        """Show copy and restart buttons after test completion."""
        self.copy_button.pack(side="left", padx=(0, 10))
        self.restart_button.pack(side="left")

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------
    def update_status(self, message: str):
        """Update progress/status label (thread‑safe)."""
        self.root.after(0, lambda: self.status_label.config(text=message))

    def insert_text(self, text: str, color: str = "black"):
        self.text_widget.config(state="normal")
        tag_name = f"color_{color}"
        if tag_name not in self.text_widget.tag_names():
            if color == "green":
                self.text_widget.tag_configure(tag_name, foreground="#008000")
            elif color == "red":
                self.text_widget.tag_configure(tag_name, foreground="#FF0000")
            else:
                self.text_widget.tag_configure(tag_name, foreground="black")

        self.text_widget.insert(tk.END, text, tag_name)
        self.text_widget.config(state="disabled")
        self.text_widget.see(tk.END)
        self.root.update()

    def check_status(self, condition, ok_text, fail_text):
        if condition:
            return f"[OK] {ok_text}\n", "green"
        else:
            self.failed_checks.append(fail_text)
            return f"[НЕ OK] {fail_text}\n", "red"

    def run_full_diagnostics(self):
        def full_diagnostics_thread():
            self.insert_text("Выполняется диагностика системы...\n\n")
            time.sleep(1)

            self.update_status("[1/4] Измеряю скорость интернета")
            download_speed, upload_speed, ping, error = utils.internet.run_speed_test_safe()

            if error:
                self.insert_text(f"Ошибка тестирования скорости: {error}\nЗамерьте скорость вручную на speedtest.net\n",
                                 'red')
                self.failed_checks.append("Проводной интернет с пропускной способностью не менее 75 Мбит/с")
            else:
                status_text, status_color = self.check_status(
                    download_speed >= 75,
                    "Соединение в норме",
                    "Проводной интернет по технологии FTTx, xPON с пропускной способностью не менее 75 Мбит/с"
                )
                self.insert_text(f"{status_text}", status_color)
                self.insert_text(f"     Загрузка: {download_speed:.0f} Мбит/с\n")
                self.insert_text(f"     Отдача:  {upload_speed:.0f} Мбит/с\n")
                self.insert_text(f"     Пинг:  {ping:.0f} мс\n")

            self.update_status("[2/4] Проверяю оборудование (процессор)")
            cpu_name = utils.cpu.get_cpu_name()
            cpu_cores = psutil.cpu_count(logical=False)
            logical_cores = psutil.cpu_count(logical=True)
            text, color = self.check_status(cpu_cores >= 2, "Процессор в норме",
                                            "Процессор с не менее чем двумя ядрами")
            self.insert_text(text, color)
            self.insert_text(f"     Модель: {cpu_name}\n")
            self.insert_text(f"     Виртуальных ядер: {logical_cores}\n")
            self.insert_text(f"     Физических ядер: {cpu_cores}\n")

            self.update_status("[2/4] Проверяю оборудование (сетевой адаптер)")
            ethernet_available = utils.internet.check_ethernet_connection()
            text, color = self.check_status(
                ethernet_available,
                "Подключение по кабелю",
                "Нет возможности подключения кабелем (Ethernet адаптер отсутствует)"
            )
            self.insert_text(text, color)
            if ethernet_available:
                adapters = utils.internet.get_ethernet_adapter_info()
                for adapter in adapters:
                    self.insert_text(f"     Сетевая карта: {adapter['adapter_name']}\n")
                    self.insert_text(f"     Дуплекс: {adapter['speed']} Мбит/с\n")

            self.update_status("[2/4] Проверяю оборудование (операционная система)")
            citrix_compatible, os_info = utils.system.get_citrix_compatibility()
            text, color = self.check_status(
                citrix_compatible,
                "Поддержка Citrix в норме",
                "Citrix не поддерживается"
            )
            self.insert_text(text, color)
            self.insert_text(
                f"     Версия ОС: {platform.system()} {platform.release()} {platform.version().split('.')[2]} \n")

            self.update_status("[2/4] Проверяю оборудование (ОЗУ)")
            ram_gb = psutil.virtual_memory().total / (1024 ** 3)
            pythoncom.CoInitialize()
            c = wmi.WMI()
            ram_freq_list = [mem.Speed for mem in c.Win32_PhysicalMemory()]
            pythoncom.CoUninitialize()
            text, color = self.check_status(ram_gb >= 4, "Память в норме", "Оперативная память от 4 ГБ")
            self.insert_text(text, color)
            self.insert_text(f"     Всего ОЗУ: {ram_gb:.0f} ГБ\n")
            if ram_freq_list:
                self.insert_text(f"     Частота: {ram_freq_list[0]} МГц\n")

            self.update_status("[2/4] Проверяю оборудование (экран и видеокарта)")
            width, height = utils.system.get_screen_resolution(self)
            gpu_name = utils.gpu.get_gpu_name()
            text, color = self.check_status(
                width >= 1600 and height >= 900,
                "Дисплей в норме",
                "Минимальное разрешение экрана 1600х900 и более"
            )
            self.insert_text(text, color)
            self.insert_text(f"     Разрешение дисплея: {width}x{height}\n")
            self.insert_text(f"     Видеокарта: {gpu_name}\n")

            self.update_status("[3/4] Проверяю диск")
            disk_usage = psutil.disk_usage("C:")
            free_gb = disk_usage.free / (1024 ** 3)
            text, color = self.check_status(free_gb >= 10, "Место на системном диске в норме",
                                            "Недостаточно места на диске")
            self.insert_text(text, color)
            self.insert_text(f"     Свободно: {round(free_gb)} ГБ\n")

            self.update_status("[4/4] Проверяю периферию (микрофон)")
            mic_available = utils.peripherals.check_microphone()
            text, color = self.check_status(mic_available, "Микрофон обнаружен", "Микрофон не найден")
            self.insert_text(text, color)

            self.update_status("[4/4] Проверяю периферию (камера)")
            camera_available, cam_width, cam_height = utils.peripherals.check_camera()
            camera_hd = cam_width >= 1280 and cam_height >= 720
            text, color = self.check_status(camera_available and camera_hd, "Web-камера обнаружена",
                                            "Web-камера не соответствует требованиям")
            self.insert_text(text, color)
            if camera_available and camera_hd:
                self.insert_text(f"      Разрешение: {cam_width}x{cam_height}")

            self.insert_text("\n" + "-" * 70 + "\n")

            if not self.failed_checks:
                self.insert_text("Все проверки пройдены. ПК соответствует требованиям для удаленной работы\n", 'green')
            else:
                self.insert_text("ПК не соответствует требованиям:\n", 'red')
                for issue in self.failed_checks:
                    if "процессор" in issue.lower():
                        self.insert_text("- Требуется обновить процессор\n", 'red')
                    elif "память" in issue.lower():
                        self.insert_text("- Информация о памяти не получена\n", 'red')
                    elif "кабель" in issue.lower() or "интернет" in issue.lower():
                        self.insert_text("- Скорость интернета > 75 Мбит/с\n", 'red')
                    elif "микрофон" in issue.lower():
                        self.insert_text("- Наличие микрофона\n", 'red')
                    elif "web-камера" in issue.lower():
                        self.insert_text("- Наличие web-камеры с разрешением не хуже HD (внешней или встроенной)\n",
                                         'red')

            self.update_status("Диагностика завершена")
            self.diagnostics_complete = True

            # Show result buttons after completion
            self.root.after(0, self.show_result_buttons)

        threading.Thread(target=full_diagnostics_thread, daemon=True).start()

    def copy_to_clipboard(self):
        if self.diagnostics_complete:
            self.text_widget.config(state='normal')
            content = self.text_widget.get(1.0, tk.END)
            self.text_widget.config(state='disabled')
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.root.update()
            messagebox.showinfo("Копирование", "Результаты диагностики скопированы в буфер обмена")
        else:
            messagebox.showwarning("Предупреждение", "Диагностика еще не завершена")


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

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Ошибка", error_msg)
        return

    root = tk.Tk()
    app = SystemDiagnosticsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()