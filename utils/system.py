import platform


def get_screen_resolution(self):
    """Get screen resolution"""
    try:
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        return width, height
    except:
        return 0, 0


def get_citrix_compatibility():
    """Check Citrix Workspace App compatibility"""
    os_name = platform.system()
    os_version = platform.release()

    if os_name == "Windows":
        try:
            version_num = float(os_version)
            if version_num >= 10:
                return True, f"Windows {os_version}"
            elif version_num >= 6.1:  # Windows 7
                return True, f"Windows {os_version}"
            else:
                return False, f"Windows {os_version}"
        except:
            return False, f"Windows {os_version}"
    elif os_name == "Linux":
        return True, f"Linux {os_version}"
    else:
        return False, f"{os_name} {os_version}"
