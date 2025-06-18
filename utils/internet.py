import os
import platform
import subprocess
import sys

import psutil
import speedtest


def check_ethernet_connection():
    """
    Check for wired ethernet connection status.
    Returns True if an enabled/resolved Ethernet adapter is found.
    """
    try:
        if platform.system() == "Windows":
            # Determine the correct encoding for Windows console output
            # Often 'cp866' for Russian consoles, but it's safer to try a few or let locale handle it
            # If `text=True` isn't working, explicitly decode with a known encoding.
            # Let's try explicit encoding first, fallback to default for text=True if it works.
            try:
                # Attempt to get output with cp866 which is common for Russian Windows consoles
                result = subprocess.run(['netsh', 'interface', 'show', 'interface'],
                                        capture_output=True,
                                        check=True,  # Raise an exception for non-zero exit codes
                                        encoding='cp866',  # Specify encoding
                                        errors='replace')  # Replace characters that can't be decoded
                output = result.stdout
            except UnicodeDecodeError:
                # Fallback if cp866 fails, let text=True handle it with default encoding
                print("Warning: cp866 decoding failed, trying default text encoding.")
                result = subprocess.run(['netsh', 'interface', 'show', 'interface'],
                                        capture_output=True,
                                        text=True,  # Uses default system encoding (e.g., locale.getpreferredencoding())
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

            # Debugging: Print the captured output to verify characters
            # print("--- Debug: Full netsh output captured ---")
            # print(output)
            # print("--- End debug output ---")

            lines = output.split('\n')
            for line in lines:
                # Check for administrative state (Enabled or Разрешен)
                # and for the interface type (Ethernet or Local Area Connection)
                if ('Enabled' in line or 'Разрешен' in line) and \
                        ('Ethernet' in line or 'Local Area Connection' in line):
                    # You might also want to check for "Подключен" (Connected)
                    # if you want to ensure the cable is physically plugged in.
                    # Example:
                    # if ('Подключен' in line or 'Connected' in line):
                    #     return True
                    # If just admin state is enough:
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


def run_speed_test_safe():
    try:
        if getattr(sys, 'frozen', False):
            sys.stdin = open(os.devnull, 'r')
            sys.stdout = open(os.devnull, 'w')
            sys.stderr = open(os.devnull, 'w')

        st = speedtest.Speedtest()
        st.get_best_server()

        download_speed = st.download() / 1024 / 1024
        upload_speed = st.upload() / 1024 / 1024
        ping = st.results.ping

        return download_speed, upload_speed, ping, None

    except Exception as e:
        return 0, 0, 0, str(e)
