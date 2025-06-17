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
