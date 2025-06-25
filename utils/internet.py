import os
import platform
import shutil
import subprocess

import psutil


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
                                        errors='replace')
                output = result.stdout
            except UnicodeDecodeError:
                print("Warning: cp866 decoding failed, trying default text encoding.")
                result = subprocess.run(['netsh', 'interface', 'show', 'interface'],
                                        capture_output=True,
                                        text=True,
                                        check=True,
                                        errors='replace')
                output = result.stdout
            except subprocess.CalledProcessError as e:
                print(f"Error running netsh command: {e}")
                print(f"Stderr: {e.stderr.decode('cp866', errors='replace') if e.stderr else 'N/A'}")
                return False
            except FileNotFoundError:
                print("Error: 'netsh' command not found. Ensure it's in your system's PATH.")
                return False

            # Debug: Print the captured output
            print("--- Debug: Full netsh output captured ---")
            print(output)
            print("--- End debug output ---")

            lines = output.split('\n')

            # Parse the netsh output more carefully
            # The output format is typically:
            # Состояние адм.  Состояние     Тип              Имя интерфейса
            # Разрешен       Подключен      Выделенный       Беспроводная сеть 2
            # Разрешен       Отключен       Выделенный       Ethernet 8

            for line in lines:
                line = line.strip()
                if not line or line.startswith('-') or 'Состояние адм' in line or 'Admin State' in line:
                    continue

                # Split the line into columns (they're space-separated, but need to handle multiple spaces)
                parts = [part for part in line.split() if part]
                if len(parts) >= 4:
                    admin_state = parts[0]
                    connection_state = parts[1]
                    interface_type = parts[2]
                    # Interface name might contain spaces, so join the rest
                    interface_name = ' '.join(parts[3:])

                    print(
                        f"Debug: Found interface - Admin: {admin_state}, State: {connection_state}, Type: {interface_type}, Name: {interface_name}")

                    # Check if this is an administratively enabled Ethernet interface
                    admin_enabled = admin_state.lower() in ['enabled', 'разрешен']
                    is_ethernet = ('ethernet' in interface_name.lower() or
                                   'local area connection' in interface_name.lower())
                    # Don't rely on interface_type for Ethernet detection as wireless also shows "Выделенный"
                    is_not_wireless = 'беспроводная' not in interface_name.lower() and 'wireless' not in interface_name.lower()

                    if admin_enabled and is_ethernet and is_not_wireless:
                        print(f"Found enabled Ethernet interface: {interface_name}")
                        return True

            # Alternative approach: check if any line contains both enabled state and ethernet
            for line in lines:
                line_lower = line.lower()
                if (('enabled' in line_lower or 'разрешен' in line_lower) and
                        ('ethernet' in line_lower or 'local area connection' in line_lower)):
                    print(f"Alternative check found Ethernet: {line.strip()}")
                    return True

            return False

        elif platform.system() == "Linux":
            # For Linux systems using 'ip link show'
            # Look for lines containing "state UP" and "UP" (for interface status)
            # and an "ether" type or "BROADCAST,MULTICAST" which usually indicates Ethernet
            # It's better to look for common Ethernet interface names like 'eth0', 'enpXsY', 'enoZ'
            # A more robust check might parse output more carefully, but this is a start.
            result = subprocess.run(['ip', 'link', 'show'],
                                    capture_output=True,
                                    text=True,
                                    check=True,
                                    encoding='utf-8',  # Linux generally uses UTF-8
                                    errors='replace')
            output = result.stdout

            # Debugging: Print the captured output to verify characters
            # print("--- Debug: Full ip link show output captured ---")
            # print(output)
            # print("--- End debug output ---")

            lines = output.split('\n')
            for line in lines:
                # A common pattern for active Ethernet adapters on Linux:
                # 2: enp0s3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT group default qlen 1000
                #    link/ether 08:00:27:f6:73:24 brd ff:ff:ff:ff:ff:ff
                if 'state UP' in line and \
                        ('ether' in line or 'BROADCAST,MULTICAST' in line) and \
                        ('eth' in line or 'enp' in line or 'eno' in line):  # Common Ethernet interface prefixes
                    return True
            return False

        elif platform.system() == "Darwin":  # macOS
            result = subprocess.run(['networksetup', '-listallhardwareports'],
                                    capture_output=True,
                                    text=True,
                                    check=True,
                                    encoding='utf-8',
                                    errors='replace')
            output = result.stdout

            # Debugging: Print the captured output
            # print("--- Debug: Full networksetup output captured ---")
            # print(output)
            # print("--- End debug output ---")

            # macOS output example:
            # Hardware Port: Ethernet
            # Device: en0
            # Ethernet Address: aabbccddeeff
            #
            # Hardware Port: Wi-Fi
            # Device: en1
            # Ethernet Address: gghhiijjkkll
            #
            # Vlan Configurations
            # ...
            # We need to find "Ethernet" and check its status.

            lines = output.split('\n')
            ethernet_port_found = False
            for i, line in enumerate(lines):
                if 'Hardware Port: Ethernet' in line:
                    ethernet_port_found = True
                    # Check the next few lines for "Status: Active" if available
                    # networksetup -listallhardwareports doesn't show active status directly for individual ports this way.
                    # A better way for macOS would be `ifconfig` or `ipconfig getifaddr en0`

            if ethernet_port_found:
                # For macOS, ifconfig is more common to check link status
                try:
                    # Check if 'en0' (common Ethernet interface) is up
                    ifconfig_result = subprocess.run(['ifconfig', 'en0'],
                                                     capture_output=True,
                                                     text=True,
                                                     check=True,
                                                     encoding='utf-8',
                                                     errors='replace')
                    if 'status: active' in ifconfig_result.stdout.lower() or 'UP' in ifconfig_result.stdout:
                        return True
                except subprocess.CalledProcessError:
                    # en0 might not exist or be down
                    return False
                except FileNotFoundError:
                    print("Warning: 'ifconfig' command not found on macOS. Cannot check Ethernet status.")
                    return False
            return False  # No Ethernet hardware port found or not active

        else:
            print(f"Warning: Unsupported operating system: {platform.system()}")
            return False

    except FileNotFoundError as e:
        print(f"Error: Command not found. Make sure system utilities are in your PATH: {e}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e.cmd}")
        print(f"Return Code: {e.returncode}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred: {e}")
        return False


def get_ethernet_adapter_info():
    """Get detailed information about active ethernet adapters"""
    net_stats = psutil.net_if_stats()
    ethernet_adapters = []

    # Filter for active ethernet adapters
    for interface_name, stats in net_stats.items():
        # Skip non-ethernet interfaces
        if any(skip_name in interface_name.lower() for skip_name in
               ['bluetooth', 'loopback', 'pseudo', 'meta', 'беспроводная', 'wireless']):
            continue

        # Check if interface is up and has reasonable speed
        if stats.isup and stats.speed > 0:
            # Get the actual adapter name (not just interface name)
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
        # Use WMI query to get hardware name (Windows)
        cmd = f'wmic path win32_networkadapter where "NetConnectionID=\'{interface_name}\'" get Name /value'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='cp866')

        for line in result.stdout.split('\n'):
            if line.startswith('Name='):
                return line.split('Name=')[1].strip()

    except Exception:
        pass

    # Fallback to interface name if hardware name not found
    return interface_name


def run_speed_test_safe(primary_server="iperf.perm.ertelecom.ru", fallback_server="iperf.ekat.ertelecom.ru",
                        duration=20):
    """
    Download iperf3, run speed test with server fallback, and cleanup - using AppData directory
    Test parameters: TCP window 2MB, 5 parallel streams, 20 seconds duration

    Args:
        primary_server: Primary iperf server to test
        fallback_server: Fallback iperf server if primary fails
        duration: Test duration in seconds

    Returns:
        tuple: (download_speed_mbps, upload_speed_mbps, ping_ms, error_message, successful_server)
    """
    import os
    import platform
    import requests
    import zipfile
    import shutil
    import subprocess
    import json

    iperf3_url = "https://files.budman.pw/iperf3.19_64.zip"

    appdata_dir = os.path.expandvars('%APPDATA%')

    # Create URMConfig directory in AppData
    urmconfig_dir = os.path.join(appdata_dir, 'URMConfig')
    os.makedirs(urmconfig_dir, exist_ok=True)

    zip_path = os.path.join(urmconfig_dir, "iperf3.19_64.zip")
    iperf_dir = os.path.join(urmconfig_dir, "iperf")
    iperf3_exe = os.path.join(iperf_dir, "iperf3.exe" if platform.system() == "Windows" else "iperf3")

    print(f"Using AppData directory: {urmconfig_dir}")
    print(f"iperf3 executable path: {iperf3_exe}")

    def test_server_connectivity(server):
        """Test if iperf server is responsive"""
        print(f"Testing connectivity to {server}...")
        test_cmd = [
            iperf3_exe,
            "-c", server,
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
                print(f"✓ Server {server} is responsive")
                return True
            else:
                print(f"✗ Server {server} failed: {stderr}")
                return False

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            print(f"✗ Server {server} timed out")
            return False
        except Exception as e:
            print(f"✗ Server {server} error: {e}")
            return False

    def run_test_on_server(server):
        """Run speed test on specified server"""
        print(f"\n=== Running speed test on {server} ===")

        # Run download test with specified parameters:
        # -w 2M: TCP window size 2MB
        # -P 5: 5 parallel streams
        # -t duration: test duration
        download_cmd = [
            iperf3_exe,
            "-c", server,
            "-t", str(duration),
            "-w", "2M",  # TCP window size 2MB
            "-P", "5",  # 5 parallel streams
            "-J"  # JSON output
        ]
        print(f"Running download test: {' '.join(download_cmd)}")
        print(f"Test parameters: TCP window 2MB, 5 parallel streams, {duration} seconds")

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

            # Close stdin immediately to prevent hanging
            process.stdin.close()

            # Wait for completion with timeout (add extra buffer for 5 parallel streams)
            stdout, stderr = process.communicate(timeout=duration + 60)

            if process.returncode != 0:
                error_msg = stderr.strip() if stderr else "Неизвестная ошибка"
                print(f"Download test failed: {error_msg}")
                return None, None, f"Ошибка при тестировании загрузки на {server}: {error_msg}"

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return None, None, f"Таймаут при тестировании загрузки на {server}"

        # Parse download results
        download_speed_mbps = 0
        try:
            if not stdout.strip():
                return None, None, f"Пустой ответ от iperf3 при тестировании загрузки на {server}"

            download_json = json.loads(stdout)
            if "end" in download_json and "sum_received" in download_json["end"]:
                download_speed_mbps = download_json["end"]["sum_received"]["bits_per_second"] / 1_000_000
            elif "end" in download_json and "sum_sent" in download_json["end"]:
                download_speed_mbps = download_json["end"]["sum_sent"]["bits_per_second"] / 1_000_000
            else:
                return None, None, f"Не удалось найти данные о скорости в ответе iperf3 на {server}"
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error parsing download results: {e}")
            print(f"Raw output: {stdout}")
            return None, None, f"Ошибка при разборе результатов загрузки на {server}: {e}"

        print(f"Download speed: {download_speed_mbps:.2f} Mbps")

        # Run upload test (reverse mode) with same parameters
        upload_cmd = [
            iperf3_exe,
            "-c", server,
            "-t", str(duration),
            "-w", "2M",  # TCP window size 2MB
            "-P", "5",  # 5 parallel streams
            "-R",  # Reverse mode (upload)
            "-J"  # JSON output
        ]
        print(f"Running upload test: {' '.join(upload_cmd)}")

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

            # Close stdin immediately
            process.stdin.close()

            # Wait for completion with timeout (add extra buffer for 5 parallel streams)
            stdout, stderr = process.communicate(timeout=duration + 60)

            if process.returncode == 0 and stdout.strip():
                try:
                    upload_json = json.loads(stdout)
                    if "end" in upload_json and "sum_received" in upload_json["end"]:
                        upload_speed_mbps = upload_json["end"]["sum_received"]["bits_per_second"] / 1_000_000
                    elif "end" in upload_json and "sum_sent" in upload_json["end"]:
                        upload_speed_mbps = upload_json["end"]["sum_sent"]["bits_per_second"] / 1_000_000
                    print(f"Upload speed: {upload_speed_mbps:.2f} Mbps")
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    print(f"Error parsing upload results: {e}")
                    # Upload test failed, but continue with download results
                    pass
            else:
                print(f"Upload test failed: {stderr}")

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            print("Upload test timed out")
            # Continue with upload_speed_mbps = 0

        return download_speed_mbps, upload_speed_mbps, None

    def cleanup_iperf_installation():
        """Clean up iperf installation"""
        try:
            if os.path.exists(iperf_dir):
                shutil.rmtree(iperf_dir)
                print("Cleaned up iperf installation")
        except Exception as e:
            print(f"Error cleaning up: {e}")

    try:
        # Check if iperf3 already exists and is working
        if os.path.exists(iperf3_exe):
            try:
                print("Found existing iperf3, testing...")
                # Test if existing iperf3 works
                test_cmd = [iperf3_exe, "--version"]
                result = subprocess.run(test_cmd, capture_output=True, timeout=5)
                if result.returncode == 0:
                    print("Existing iperf3 works, skipping download")
                else:
                    print("Existing iperf3 doesn't work, removing...")
                    if os.path.exists(iperf_dir):
                        shutil.rmtree(iperf_dir)
                    raise Exception("Existing iperf3 corrupted")
            except Exception as e:
                print(f"Error testing existing iperf3: {e}")
                # Remove and re-download
                if os.path.exists(iperf_dir):
                    shutil.rmtree(iperf_dir)

        # Download and extract if needed
        if not os.path.exists(iperf3_exe):
            print(f"Downloading iperf3 from {iperf3_url}...")
            print(f"Saving to {zip_path}...")

            # Download the zip file
            response = requests.get(iperf3_url, timeout=30)
            response.raise_for_status()

            with open(zip_path, 'wb') as f:
                f.write(response.content)

            print(f"Downloaded {len(response.content)} bytes")

            # Extract the zip file
            print(f"Extracting to {urmconfig_dir}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # List contents first
                file_list = zip_ref.namelist()
                print(f"Archive contents: {file_list}")
                zip_ref.extractall(urmconfig_dir)

            # Find the extracted folder
            extracted_folder = os.path.join(urmconfig_dir, "iperf3.19_64")
            print(f"Looking for extracted folder: {extracted_folder}")

            if not os.path.exists(extracted_folder):
                # Try to find any folder that was extracted
                for item in os.listdir(urmconfig_dir):
                    item_path = os.path.join(urmconfig_dir, item)
                    if os.path.isdir(item_path) and item != 'iperf' and 'iperf' in item.lower():
                        extracted_folder = item_path
                        print(f"Found alternative extracted folder: {extracted_folder}")
                        break
                else:
                    return 0, 0, 0, f"Не удалось найти извлеченную папку в {urmconfig_dir}", None

            # Rename extracted folder to iperf
            if os.path.exists(iperf_dir):
                shutil.rmtree(iperf_dir)

            os.rename(extracted_folder, iperf_dir)
            print(f"Renamed {extracted_folder} to {iperf_dir}")

            # Make executable on Unix systems
            if platform.system() != "Windows":
                os.chmod(iperf3_exe, 0o755)

            # Clean up zip file
            if os.path.exists(zip_path):
                os.remove(zip_path)
                print("Cleaned up zip file")

        # Verify iperf3 executable exists
        if not os.path.exists(iperf3_exe):
            return 0, 0, 0, f"iperf3 executable not found at {iperf3_exe}", None

        print(f"iperf3 executable confirmed at: {iperf3_exe}")

        # Test server connectivity and choose which server to use
        servers_to_try = [primary_server, fallback_server]
        successful_server = None

        for server in servers_to_try:
            if test_server_connectivity(server):
                successful_server = server
                break

        if not successful_server:
            cleanup_iperf_installation()
            return 0, 0, 0, f"Оба сервера недоступны: {primary_server}, {fallback_server}", None

        print(f"Using server: {successful_server}")

        # Run the actual speed test
        download_speed, upload_speed, error = run_test_on_server(successful_server)

        if error:
            # If the chosen server fails during the actual test, try the other one
            print(f"Test failed on {successful_server}, trying fallback...")
            other_server = fallback_server if successful_server == primary_server else primary_server

            if test_server_connectivity(other_server):
                print(f"Fallback server {other_server} is available, running test...")
                download_speed, upload_speed, error = run_test_on_server(other_server)
                if not error:
                    successful_server = other_server

            if error:
                cleanup_iperf_installation()
                return 0, 0, 0, error, None

        # Get ping to the successful server
        print(f"Getting ping to {successful_server}...")
        ping_ms = get_ping_to_server(successful_server)
        print(f"Ping: {ping_ms} ms")

        cleanup_iperf_installation()

        return download_speed, upload_speed, ping_ms, None, successful_server

    except requests.RequestException as e:
        cleanup_iperf_installation()
        return 0, 0, 0, f"Ошибка при загрузке iperf3: {str(e)}", None
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        cleanup_iperf_installation()
        return 0, 0, 0, f"Ошибка при тестировании скорости: {str(e)}", None


def get_ping_to_server(server):
    """
    Get ping to the specified server using system ping command.

    Args:
        server (str): Server hostname or IP address

    Returns:
        float: Ping time in milliseconds, or 0 if failed
    """
    import platform
    import subprocess

    try:
        if platform.system() == "Windows":
            # Windows ping command
            cmd = ["ping", "-n", "4", server]
        else:
            # Linux/Mac ping command
            cmd = ["ping", "-c", "4", server]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            output = result.stdout
            if platform.system() == "Windows":
                # Parse Windows ping output
                import re
                ping_times = re.findall(r'time[<=](\d+)ms', output)
                if ping_times:
                    return sum(int(t) for t in ping_times) / len(ping_times)
            else:
                # Parse Linux/Mac ping output
                import re
                ping_times = re.findall(r'time=(\d+\.?\d*)', output)
                if ping_times:
                    return sum(float(t) for t in ping_times) / len(ping_times)

        return 0
    except Exception as e:
        print(f"Error getting ping: {e}")
        return 0


def cleanup_iperf_installation():
    """
    Optional function to clean up iperf installation from AppData
    Call this if you want to force re-download on next run
    """
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
