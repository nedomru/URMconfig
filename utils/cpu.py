import platform
import sys

import psutil


def get_cpu_info():
    cpu_name = ""
    cpu_cores = 0
    cpu_logical_cores = 0

    try:
        if sys.platform == "win32":
            # Get CPU name
            import winreg
            registry_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as key:
                cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                cpu_name = cpu_name.strip()

            # Get CPU cores
            cpu_cores = psutil.cpu_count(logical=False)
            logical_cores = psutil.cpu_count(logical=True)

            return cpu_name, cpu_cores, logical_cores
        elif sys.platform.startswith("linux"):
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
        elif sys.platform == "darwin":
            import subprocess
            return subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"]
            ).strip().decode()
        else:
            return platform.processor()
    except Exception:
        return platform.processor() or "Неизвестно"
