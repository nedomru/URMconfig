import platform
import re
import subprocess


def get_gpu_name():
    """Get GPU name using WMI query (Windows)"""
    try:
        cmd = 'wmic path win32_VideoController get Name /value'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='cp866')

        gpu_names = []
        for line in result.stdout.split('\n'):
            if line.startswith('Name=') and line.strip() != 'Name=':
                gpu_name = line.split('Name=')[1].strip()
                if gpu_name:  # Skip empty names
                    gpu_names.append(gpu_name)

        return gpu_names[0] if gpu_names else "Неизвестная видеокарта"

    except Exception:
        return "Неизвестная видеокарта"


def get_gpu_driver():
    driver_version = ""

    system = platform.system() # Windows or Linux or Darwin

    """Get Windows video driver version using wmic"""
    if system == "Windows":
        try:
            # Get GPU info using wmic
            result = subprocess.run([
                'wmic', 'path', 'win32_VideoController',
                'get', 'name,DriverVersion', '/format:csv'
            ], capture_output=True, text=True, check=True)

            lines = result.stdout.strip().split('\n')

            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 3:
                        version = parts[1].strip()
                        if version:
                            driver_version = version
                            break
        except Exception as e:
            print(f"Произошла ошибка при проверке драйвера: {e}")
    elif system == "Linux":
        try:
            # Check NVIDIA driver
            result = subprocess.run(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader,nounits'],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                driver_version = result.stdout.strip()
        except FileNotFoundError:
            pass

        try:
            # Check AMD driver via modinfo
            result = subprocess.run(['modinfo', 'amdgpu'], capture_output=True, text=True)
            if result.returncode == 0:
                version_match = re.search(r'version:\s*(.+)', result.stdout)
                if version_match:
                    driver_version = version_match.group(1).strip()
        except FileNotFoundError:
            pass

        try:
            # Check Intel driver
            result = subprocess.run(['modinfo', 'i915'], capture_output=True, text=True)
            if result.returncode == 0:
                version_match = re.search(r'version:\s*(.+)', result.stdout)
                if version_match:
                    driver_version = version_match.group(1).strip()
        except FileNotFoundError:
            pass

        # Fallback: check lspci for GPU info
        if not driver_version:
            try:
                result = subprocess.run(['lspci', '-k'], capture_output=True, text=True)
                if result.returncode == 0:
                    gpu_lines = [line for line in result.stdout.split('\n')
                                 if 'VGA' in line or 'Display' in line]
                    driver_version = gpu_lines[:3]  # Limit output
            except FileNotFoundError:
                pass
    return driver_version