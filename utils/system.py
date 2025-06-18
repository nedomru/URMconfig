import platform

import psutil
import pythoncom
import wmi


def get_screen_resolution(self):
    """Get screen resolution"""
    try:
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        return width, height
    except:
        return 0, 0


def get_citrix_compatibility():
    """
    Check Citrix Workspace App compatibility and return the supported version
    based on Windows 10/11 OS version and build.
    Returns:
        tuple: (True/False, "Supported Citrix Version" or "N/A")
    """
    os_name = platform.system()
    os_release = platform.release()
    try:
        os_build = platform.version().split('.')[2]
    except IndexError:
        os_build = None  # Handle cases where build number might not be available in expected format

    if os_name == "Windows":
        if os_release == "11":
            # Windows 11 Compatibility: {Build Number: Citrix Workspace App Version}
            windows_11_compat = {
                "26100": "2409 and later",
                "22631": "2311 and later",
                "22621": "2209 and later",
                "22000": "2109.1 and later"
            }
            if os_build and os_build in windows_11_compat:
                citrix_version_info = windows_11_compat[os_build]
                if "and later" in citrix_version_info:
                    # Extract the base version
                    base_version = citrix_version_info.split(" ")[0]
                    return True, f"{base_version} или выше"  # Indicate support for this and later versions
                else:
                    return True, citrix_version_info
            else:
                return False, "N/A"
        elif os_release == "10":
            # Windows 10 Compatibility: {Build Number: Citrix Workspace App Version}
            windows_10_compat = {
                "19045": "2206 and later",
                "19044": "2112.1 and later",
                "19043": "2106 and later",
                "19042": "2012 and later",
                "19041": "2006.1 and later",
                "18363": "1911 and later",
                "18362": "1909 and later",
                "17763": "1812 and later",
                "17134": "1808 and later"
            }
            if os_build and os_build in windows_10_compat:
                citrix_version_info = windows_10_compat[os_build]
                if "and later" in citrix_version_info:
                    # Extract the base version
                    base_version = citrix_version_info.split(" ")[0]
                    return True, f"{base_version} или выше"  # Indicate support for this and later versions
                else:
                    return True, citrix_version_info
            else:
                return False, "N/A"
        else:
            return False, "N/A"
    elif os_name == "Linux":
        # For Linux, assuming broad compatibility as per the original function.
        # If specific versions are needed, this would require more detailed lookup.
        return True, "latest"  # Or a specific known compatible version range for Linux
    else:
        return False, "N/A"


def get_ram():
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)

    try:
        pythoncom.CoInitialize()
        c = wmi.WMI()
        ram_freq_list = [mem.Speed for mem in c.Win32_PhysicalMemory()]
        pythoncom.CoUninitialize()
    except Exception:
        ram_freq_list = []

    return ram_gb, ram_freq_list
