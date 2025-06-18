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
    """Get Windows video driver version using wmic"""
    try:
        # Get GPU info using wmic
        result = subprocess.run([
            'wmic', 'path', 'win32_VideoController',
            'get', 'name,DriverVersion', '/format:csv'
        ], capture_output=True, text=True, check=True)

        lines = result.stdout.strip().split('\n')
        drivers = []

        for line in lines[1:]:  # Skip header
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 3:
                    name = parts[2].strip()
                    version = parts[1].strip()
                    if name and version:
                        drivers.append(f"{version}")

        return drivers if drivers else ["Не найдено"]

    except subprocess.CalledProcessError as e:
        return [f"Ошибка проверки драйвера: {e}"]