import platform
import sys


def get_cpu_name():
    try:
        if sys.platform == "win32":
            import winreg
            registry_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as key:
                cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                return cpu_name.strip()
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
