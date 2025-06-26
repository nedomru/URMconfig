import concurrent.futures
import os
import platform
import shutil
import subprocess
import sys
from typing import List, Tuple, Optional

import psutil

# All available iperf servers
IPERF_SERVERS = [
    {"name": "Барнаул", "code": "22", "host": "iperf.barnaul.ertelecom.ru", "city": "barnaul"},
    {"name": "Брянск", "code": "32", "host": "iperf.bryansk.ertelecom.ru", "city": "bryansk"},
    {"name": "Волгоград", "code": "34", "host": "iperf.volgograd.ertelecom.ru", "city": "volgograd"},
    {"name": "Краснодар", "code": "23", "host": "iperf.krd.ertelecom.ru", "city": "krd"},
    {"name": "Москва", "code": "77", "host": "st.msk.ertelecom.ru", "city": "msk"},
    {"name": "Воронеж", "code": "36", "host": "iperf.voronezh.ertelecom.ru", "city": "voronezh"},
    {"name": "Екатеринбург", "code": "66", "host": "iperf.ekat.ertelecom.ru", "city": "ekat"},
    {"name": "Ижевск", "code": "18", "host": "iperf.izhevsk.ertelecom.ru", "city": "izhevsk"},
    {"name": "Йошкар-Ола", "code": "12", "host": "iperf.yola.ertelecom.ru", "city": "yola"},
    {"name": "Иркутск", "code": "38", "host": "iperf.irkutsk.ertelecom.ru", "city": "irkutsk"},
    {"name": "Казань", "code": "16", "host": "iperf.kzn.ertelecom.ru", "city": "kzn"},
    {"name": "Киров", "code": "43", "host": "iperf.kirov.ertelecom.ru", "city": "kirov"},
    {"name": "Красноярск", "code": "24", "host": "iperf.krsk.ertelecom.ru", "city": "krsk"},
    {"name": "Курган", "code": "45", "host": "iperf.kurgan.ertelecom.ru", "city": "kurgan"},
    {"name": "Курск", "code": "46", "host": "iperf.kursk.ertelecom.ru", "city": "kursk"},
    {"name": "Липецк", "code": "48", "host": "iperf.lipetsk.ertelecom.ru", "city": "lipetsk"},
    {"name": "Магнитогорск", "code": "274", "host": "iperf.mgn.ertelecom.ru", "city": "mgn"},
    {"name": "Набережные Челны", "code": "161", "host": "iperf.chelny.ertelecom.ru", "city": "chelny"},
    {"name": "Архангельск", "code": "29", "host": "iperf.arkhangelsk.ertelecom.ru", "city": "arkhangelsk"},
    {"name": "Нижний Новгород", "code": "52", "host": "iperf.nn.ertelecom.ru", "city": "nn"},
    {"name": "Новосибирск", "code": "54", "host": "iperf.nsk.ertelecom.ru", "city": "nsk"},
    {"name": "Омск", "code": "55", "host": "iperf.omsk.ertelecom.ru", "city": "omsk"},
    {"name": "Оренбург", "code": "56", "host": "iperf.oren.ertelecom.ru", "city": "oren"},
    {"name": "Пенза", "code": "58", "host": "iperf.penza.ertelecom.ru", "city": "penza"},
    {"name": "Пермь", "code": "59", "host": "iperf.perm.ertelecom.ru", "city": "perm"},
    {"name": "Ростов-на-Дону", "code": "61", "host": "iperf.rostov.ertelecom.ru", "city": "rostov"},
    {"name": "Рязань", "code": "62", "host": "iperf.ryazan.ertelecom.ru", "city": "ryazan"},
    {"name": "Самара", "code": "63", "host": "iperf.samara.ertelecom.ru", "city": "samara"},
    {"name": "Санкт-Петербург", "code": "78", "host": "iperf.spb.ertelecom.ru", "city": "spb"},
    {"name": "Саратов", "code": "64", "host": "iperf.saratov.ertelecom.ru", "city": "saratov"},
    {"name": "Тверь", "code": "69", "host": "iperf.tver.ertelecom.ru", "city": "tver"},
    {"name": "Томск", "code": "70", "host": "iperf.tomsk.ertelecom.ru", "city": "tomsk"},
    {"name": "Тула", "code": "71", "host": "iperf.tula.ertelecom.ru", "city": "tula"},
    {"name": "Тюмень", "code": "72", "host": "iperf.tmn.ertelecom.ru", "city": "tmn"},
    {"name": "Улан-Удэ", "code": "30", "host": "iperf.ulu.ertelecom.ru", "city": "ulu"},
    {"name": "Ульяновск", "code": "73", "host": "iperf.ulsk.ertelecom.ru", "city": "ulsk"},
    {"name": "Уфа", "code": "102", "host": "iperf.ufa.ertelecom.ru", "city": "ufa"},
    {"name": "Чебоксары", "code": "21", "host": "iperf.cheb.ertelecom.ru", "city": "cheb"},
    {"name": "Челябинск", "code": "174", "host": "iperf.chel.ertelecom.ru", "city": "chel"},
    {"name": "Ярославль", "code": "76", "host": "iperf.yar.ertelecom.ru", "city": "yar"},
]

def get_subprocess_creation_flags():
    """Get appropriate subprocess creation flags to hide windows on Windows."""
    if platform.system() == "Windows" and getattr(sys, 'frozen', False):
        return subprocess.CREATE_NO_WINDOW
    return 0


def ping_server(server: dict, timeout: int = 5) -> Tuple[dict, float]:
    """
    Ping a single server and return the average response time.

    Args:
        server: Server dictionary with 'host' and 'name' keys
        timeout: Ping timeout in seconds

    Returns:
        tuple: (server_dict, average_ping_ms) - ping_ms is 999999 if failed
    """
    try:
        cmd = ["ping", "-n", "3", "-w", str(timeout * 1000), server["host"]]

        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding='cp866', errors='replace', timeout=timeout + 2, creationflags=get_subprocess_creation_flags())

        if result.returncode == 0:
            output = result.stdout
            import re
            # Handle Russian Windows ping output format
            # Look for patterns like: время<1мс, время=1мс, время=10мс
            ping_times = []

            # Try Russian format first
            russian_times = re.findall(r'время[<=](\d+)мс', output)
            if russian_times:
                ping_times = [int(t) for t in russian_times]
            else:
                # Fallback to English format
                english_times = re.findall(r'time[<=](\d+)ms', output)
                if english_times:
                    ping_times = [int(t) for t in english_times]
                else:
                    # Try to find any numeric values after время/time
                    all_times = re.findall(r'(?:время|time)[<=]?(\d+)', output)
                    if all_times:
                        ping_times = [int(t) for t in all_times]

            if ping_times:
                avg_ping = sum(ping_times) / len(ping_times)
                print(f"✓ {server['name']} ({server['host']}): {avg_ping:.0f}ms")
                return server, avg_ping
            else:
                # Debug: print the actual output to see what we're getting
                print(f"✗ {server['name']} ({server['host']}): no ping times found")
                print(f"   Raw output: {output[:200]}...")  # First 200 chars for debugging

    except Exception as e:
        print(f"✗ {server['name']} ({server['host']}): failed ({e})")

    return server, 999999  # Very high ping for failed servers


def find_best_servers(max_workers: int = 10, max_servers: int = 5) -> List[Tuple[dict, float]]:
    """
    Ping all servers in parallel and return the best ones sorted by ping time.

    Args:
        max_workers: Maximum number of concurrent ping operations
        max_servers: Maximum number of servers to return

    Returns:
        List of (server_dict, ping_ms) tuples sorted by ping time
    """
    print("Поиск ближайших серверов...")

    # Ping all servers in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all ping tasks
        future_to_server = {executor.submit(ping_server, server): server for server in IPERF_SERVERS}

        results = []
        for future in concurrent.futures.as_completed(future_to_server, timeout=30):
            try:
                server, ping_time = future.result()
                results.append((server, ping_time))
            except Exception as e:
                server = future_to_server[future]
                print(f"✗ {server['name']}: exception ({e})")
                results.append((server, 999999))

    # Sort by ping time and filter out failed servers
    results.sort(key=lambda x: x[1])
    successful_servers = [r for r in results if r[1] < 999999]

    if successful_servers:
        print(f"\nЛучшие серверы:")
        for i, (server, ping) in enumerate(successful_servers[:max_servers]):
            print(f"{i + 1}. {server['name']}: {ping:.0f}ms")
        return successful_servers[:max_servers]
    else:
        print("Ни один сервер не отвечает на ping!")
        return []


def check_ethernet_connection():
    """
    Check for wired ethernet connection status.
    Returns True if an enabled/resolved Ethernet adapter is found.
    """
    try:
        if platform.system() == "Windows":
            try:
                # Get network interface information
                result = subprocess.run(['netsh', 'interface', 'show', 'interface'],
                                        capture_output=True,
                                        check=True,
                                        encoding='cp866',
                                        errors='replace', creationflags=get_subprocess_creation_flags())
                output = result.stdout
            except UnicodeDecodeError:
                print("Warning: cp866 decoding failed, trying default text encoding.")
                result = subprocess.run(['netsh', 'interface', 'show', 'interface'],
                                        capture_output=True,
                                        text=True,
                                        check=True,
                                        errors='replace', creationflags=get_subprocess_creation_flags())
                output = result.stdout
            except subprocess.CalledProcessError as e:
                print(f"Error running netsh command: {e}")
                return False
            except FileNotFoundError:
                print("Error: 'netsh' command not found.")
                return False

            lines = output.split('\n')

            for line in lines:
                line = line.strip()
                if not line or line.startswith('-') or 'Состояние адм' in line or 'Admin State' in line:
                    continue

                parts = [part for part in line.split() if part]
                if len(parts) >= 4:
                    admin_state = parts[0]
                    connection_state = parts[1]
                    interface_type = parts[2]
                    interface_name = ' '.join(parts[3:])

                    admin_enabled = admin_state.lower() in ['enabled', 'разрешен']
                    is_ethernet = ('ethernet' in interface_name.lower() or
                                   'local area connection' in interface_name.lower())
                    is_not_wireless = 'беспроводная' not in interface_name.lower() and 'wireless' not in interface_name.lower()

                    if admin_enabled and is_ethernet and is_not_wireless:
                        print(f"Found enabled Ethernet interface: {interface_name}")
                        return True

            return False
        else:
            print(f"Warning: Unsupported operating system: {platform.system()}")
            return False

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False


def get_ethernet_adapter_info():
    """Get detailed information about active ethernet adapters"""
    net_stats = psutil.net_if_stats()
    ethernet_adapters = []

    for interface_name, stats in net_stats.items():
        if any(skip_name in interface_name.lower() for skip_name in
               ['bluetooth', 'loopback', 'pseudo', 'meta', 'беспроводная', 'wireless']):
            continue

        if stats.isup and stats.speed > 0:
            adapter_name = get_adapter_hardware_name(interface_name)
            ethernet_adapters.append({
                'interface': interface_name,
                'adapter_name': adapter_name,
                'speed': stats.speed,
                'duplex': stats.duplex
            })

    return ethernet_adapters


def get_adapter_hardware_name(interface_name):
    """Get the actual hardware name of the network adapter"""
    try:
        cmd = f'wmic path win32_networkadapter where "NetConnectionID=\'{interface_name}\'" get Name /value'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='cp866', creationflags=get_subprocess_creation_flags())

        for line in result.stdout.split('\n'):
            if line.startswith('Name='):
                return line.split('Name=')[1].strip()
    except Exception:
        pass

    return interface_name


def test_iperf_server_connectivity(iperf3_exe: str, iperf_dir: str, server_host: str) -> bool:
    """Test if iperf server is responsive with a quick 1-second test"""
    print(f"Тестирование подключения к {server_host}...")
    test_cmd = [
        iperf3_exe,
        "-c", server_host,
        "-t", "1",  # Very short 1-second test
        "-J"
    ]

    try:
        process = subprocess.Popen(
            test_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            cwd=iperf_dir,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )

        process.stdin.close()
        stdout, stderr = process.communicate(timeout=10)

        if process.returncode == 0 and stdout.strip():
            print(f"✓ Сервер {server_host} доступен для iperf")
            return True
        else:
            print(f"✗ Сервер {server_host} недоступен для iperf: {stderr}")
            return False

    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        print(f"✗ Сервер {server_host} - таймаут iperf теста")
        return False
    except Exception as e:
        print(f"✗ Сервер {server_host} - ошибка iperf теста: {e}")
        return False


def run_speed_test_on_server(iperf3_exe: str, iperf_dir: str, server: dict, duration: int = 20) -> Tuple[
    Optional[float], Optional[float], Optional[str]]:
    """Run speed test on specified server"""
    server_host = server["host"]
    server_name = server["name"]

    print(f"\n=== Запуск теста скорости на сервере {server_name} ({server_host}) ===")

    # Run download test
    download_cmd = [
        iperf3_exe,
        "-c", server_host,
        "-t", str(duration),
        "-w", "2M",  # TCP window size 2MB
        "-P", "5",  # 5 parallel streams
        "-J"  # JSON output
    ]

    print(f"Тест загрузки: TCP окно 2MB, 5 потоков, {duration} секунд")

    try:
        process = subprocess.Popen(
            download_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            cwd=iperf_dir,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )

        process.stdin.close()
        stdout, stderr = process.communicate(timeout=duration + 60)

        if process.returncode != 0:
            error_msg = stderr.strip() if stderr else "Неизвестная ошибка"
            print(f"Тест загрузки неудачен: {error_msg}")
            return None, None, f"Ошибка при тестировании загрузки на {server_name}: {error_msg}"

    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        return None, None, f"Таймаут при тестировании загрузки на {server_name}"

    # Parse download results
    download_speed_mbps = 0
    try:
        if not stdout.strip():
            return None, None, f"Пустой ответ от iperf3 при тестировании загрузки на {server_name}"

        import json
        download_json = json.loads(stdout)
        if "end" in download_json and "sum_received" in download_json["end"]:
            download_speed_mbps = download_json["end"]["sum_received"]["bits_per_second"] / 1_000_000
        elif "end" in download_json and "sum_sent" in download_json["end"]:
            download_speed_mbps = download_json["end"]["sum_sent"]["bits_per_second"] / 1_000_000
        else:
            return None, None, f"Не удалось найти данные о скорости в ответе iperf3 на {server_name}"
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Ошибка парсинга результатов загрузки: {e}")
        return None, None, f"Ошибка при разборе результатов загрузки на {server_name}: {e}"

    print(f"Скорость загрузки: {download_speed_mbps:.2f} Мбит/с")

    # Run upload test (reverse mode)
    upload_cmd = [
        iperf3_exe,
        "-c", server_host,
        "-t", str(duration),
        "-w", "2M",  # TCP window size 2MB
        "-P", "5",  # 5 parallel streams
        "-R",  # Reverse mode (upload)
        "-J"  # JSON output
    ]

    print("Запуск теста отдачи...")

    upload_speed_mbps = 0
    try:
        process = subprocess.Popen(
            upload_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            cwd=iperf_dir,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )

        process.stdin.close()
        stdout, stderr = process.communicate(timeout=duration + 60)

        if process.returncode == 0 and stdout.strip():
            try:
                upload_json = json.loads(stdout)
                if "end" in upload_json and "sum_received" in upload_json["end"]:
                    upload_speed_mbps = upload_json["end"]["sum_received"]["bits_per_second"] / 1_000_000
                elif "end" in upload_json and "sum_sent" in upload_json["end"]:
                    upload_speed_mbps = upload_json["end"]["sum_sent"]["bits_per_second"] / 1_000_000
                print(f"Скорость отдачи: {upload_speed_mbps:.2f} Мбит/с")
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Ошибка парсинга результатов отдачи: {e}")
        else:
            print(f"Тест отдачи неудачен: {stderr}")

    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        print("Тест отдачи - таймаут")

    return download_speed_mbps, upload_speed_mbps, None


def run_speed_test_safe(duration: int = 20) -> Tuple[float, float, float, Optional[str], Optional[str]]:
    """
    Enhanced speed test with automatic server selection based on ping times.

    Args:
        duration: Test duration in seconds

    Returns:
        tuple: (download_speed_mbps, upload_speed_mbps, ping_ms, error_message, successful_server_name)
    """
    import os
    import platform
    import requests
    import zipfile
    import shutil
    import subprocess

    iperf3_url = "https://files.budman.pw/iperf3.19_64.zip"
    appdata_dir = os.path.expandvars('%APPDATA%')
    urmconfig_dir = os.path.join(appdata_dir, 'URMConfig')
    os.makedirs(urmconfig_dir, exist_ok=True)

    zip_path = os.path.join(urmconfig_dir, "iperf3.19_64.zip")
    iperf_dir = os.path.join(urmconfig_dir, "iperf")
    iperf3_exe = os.path.join(iperf_dir, "iperf3.exe" if platform.system() == "Windows" else "iperf3")

    def cleanup_iperf_installation():
        """Clean up iperf installation"""
        try:
            if os.path.exists(iperf_dir):
                shutil.rmtree(iperf_dir)
                print("Очистка установки iperf")
        except Exception as e:
            print(f"Ошибка очистки: {e}")

    try:
        # Check if iperf3 already exists and is working
        if os.path.exists(iperf3_exe):
            try:
                print("Найден существующий iperf3, проверка...")
                test_cmd = [iperf3_exe, "--version"]
                result = subprocess.run(test_cmd, capture_output=True, timeout=5, creationflags=get_subprocess_creation_flags())
                if result.returncode == 0:
                    print("Существующий iperf3 работает, пропуск загрузки")
                else:
                    print("Существующий iperf3 не работает, удаление...")
                    if os.path.exists(iperf_dir):
                        shutil.rmtree(iperf_dir)
                    raise Exception("Существующий iperf3 поврежден")
            except Exception as e:
                print(f"Ошибка проверки существующего iperf3: {e}")
                if os.path.exists(iperf_dir):
                    shutil.rmtree(iperf_dir)

        # Download and extract if needed
        if not os.path.exists(iperf3_exe):
            print(f"Загрузка iperf3 с {iperf3_url}...")

            response = requests.get(iperf3_url, timeout=30)
            response.raise_for_status()

            with open(zip_path, 'wb') as f:
                f.write(response.content)

            print(f"Загружено {len(response.content)} байт")

            # Extract the zip file
            print(f"Извлечение в {urmconfig_dir}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(urmconfig_dir)

            # Find and rename extracted folder
            extracted_folder = os.path.join(urmconfig_dir, "iperf3.19_64")
            if not os.path.exists(extracted_folder):
                for item in os.listdir(urmconfig_dir):
                    item_path = os.path.join(urmconfig_dir, item)
                    if os.path.isdir(item_path) and item != 'iperf' and 'iperf' in item.lower():
                        extracted_folder = item_path
                        break
                else:
                    return 0, 0, 0, f"Не удалось найти извлеченную папку в {urmconfig_dir}", None

            if os.path.exists(iperf_dir):
                shutil.rmtree(iperf_dir)

            os.rename(extracted_folder, iperf_dir)

            if platform.system() != "Windows":
                os.chmod(iperf3_exe, 0o755)

            if os.path.exists(zip_path):
                os.remove(zip_path)

        if not os.path.exists(iperf3_exe):
            return 0, 0, 0, f"iperf3 исполняемый файл не найден в {iperf3_exe}", None

        print(f"iperf3 исполняемый файл подтвержден: {iperf3_exe}")

        # Find best servers by ping
        best_servers = find_best_servers(max_workers=15, max_servers=5)

        if not best_servers:
            cleanup_iperf_installation()
            return 0, 0, 0, "Ни один сервер не отвечает на ping", None

        # Try servers in order of ping time
        for server, ping_time in best_servers:
            print(f"\nПопытка подключения к серверу {server['name']} (ping: {ping_time:.0f}ms)")

            # Test iperf connectivity
            if not test_iperf_server_connectivity(iperf3_exe, iperf_dir, server["host"]):
                print(f"Сервер {server['name']} недоступен для iperf, пробуем следующий...")
                continue

            # Run actual speed test
            download_speed, upload_speed, error = run_speed_test_on_server(
                iperf3_exe, iperf_dir, server, duration
            )

            if error:
                print(f"Тест скорости неудачен на {server['name']}: {error}")
                print("Пробуем следующий сервер...")
                continue

            # Success! Clean up and return results
            print(f"Тест скорости успешно завершен на сервере {server['name']}")
            cleanup_iperf_installation()

            return download_speed, upload_speed, ping_time, None, server['name']

        # If we get here, all servers failed
        cleanup_iperf_installation()
        return 0, 0, 0, "Все серверы недоступны или тестирование неудачно", None

    except requests.RequestException as e:
        cleanup_iperf_installation()
        return 0, 0, 0, f"Ошибка при загрузке iperf3: {str(e)}", None
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        cleanup_iperf_installation()
        return 0, 0, 0, f"Ошибка при тестировании скорости: {str(e)}", None


def cleanup_iperf_installation():
    """Clean up iperf installation from AppData"""
    try:
        if platform.system() == "Windows":
            appdata_dir = os.path.expandvars('%APPDATA%')
        else:
            appdata_dir = os.path.expanduser('~/.local/share')

        urmconfig_dir = os.path.join(appdata_dir, 'URMConfig')
        iperf_dir = os.path.join(urmconfig_dir, "iperf")

        if os.path.exists(iperf_dir):
            shutil.rmtree(iperf_dir)
            return True
    except Exception:
        pass
    return False
