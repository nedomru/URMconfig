"""
Simple updater module for URMconfig application.

Checks GitHub releases and directs users to download new versions
from the browser instead of automatic installation.
"""

import webbrowser
from typing import Optional, Tuple

import requests
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

# Application constants
GITHUB_API_URL = "https://api.github.com/repos/nedomru/URMconfig/releases/latest"
GITHUB_RELEASES_URL = "https://github.com/nedomru/URMconfig/releases"
CURRENT_VERSION = "1.2"  # Update this with each release
TIMEOUT = 30  # seconds


class UpdateChecker(QThread):
    """Background thread for checking updates."""

    update_available = pyqtSignal(str, str, str)  # version, download_url, fallback_url
    update_check_failed = pyqtSignal(str)
    no_update_available = pyqtSignal()

    def run(self):
        """Check for updates in background."""
        try:
            has_update, version, download_url = check_for_updates()
            if has_update:
                fallback_url = GITHUB_RELEASES_URL if not download_url else ""
                self.update_available.emit(version, download_url or "", fallback_url)
            else:
                self.no_update_available.emit()
        except Exception as e:
            self.update_check_failed.emit(str(e))


def get_current_version() -> str:
    """Get current application version."""
    return CURRENT_VERSION


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse version string to comparable tuple."""
    version = version.lstrip('v')
    try:
        parts = version.split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except (ValueError, IndexError):
        return (0, 0, 0)


def is_newer_version(current: str, latest: str) -> bool:
    """Check if latest version is newer than current."""
    return parse_version(latest) > parse_version(current)


def get_latest_release() -> Optional[dict]:
    """Get latest release info from GitHub."""
    try:
        headers = {'User-Agent': 'URMconfig-Updater'}
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def find_exe_download_url(assets: list) -> Optional[str]:
    """Find URMconfig.exe download URL from release assets."""
    for asset in assets:
        if asset['name'] == 'URMconfig.exe':
            return asset['browser_download_url']
    return None


def check_for_updates() -> Tuple[bool, str, Optional[str]]:
    """
    Check if newer version is available.

    Returns:
        tuple: (has_update, latest_version, download_url)
    """
    release_info = get_latest_release()
    if not release_info:
        raise Exception("Не удалось получить информацию о релизах")

    latest_version = release_info.get('tag_name', '')
    current_version = get_current_version()

    has_update = is_newer_version(current_version, latest_version)
    download_url = None

    if has_update:
        assets = release_info.get('assets', [])
        download_url = find_exe_download_url(assets)

    return has_update, latest_version, download_url


class Updater:
    """Main updater class for user interaction."""

    def __init__(self, parent=None):
        self.parent = parent
        self.checker = None

    def check_for_updates(self, silent=False):
        """
        Check for updates with UI feedback.

        Args:
            silent: If True, don't show "no updates" message
        """
        # Don't start new check if one is already running
        if self.checker and self.checker.isRunning():
            return

        self.silent = silent

        self.checker = UpdateChecker()
        self.checker.update_available.connect(self._on_update_available)
        self.checker.update_check_failed.connect(self._on_check_failed)
        self.checker.no_update_available.connect(self._on_no_update)
        self.checker.finished.connect(self._on_check_finished)
        self.checker.start()

    def _on_check_finished(self):
        """Handle checker thread completion."""
        if self.checker:
            self.checker.wait()  # Wait for thread to fully finish
            self.checker = None

    def _on_update_available(self, version: str, download_url: str, fallback_url: str):
        """Handle update available."""
        current = get_current_version()

        if download_url:
            message = (f"Доступна новая версия!\n\n"
                       f"Текущая версия: {current}\n"
                       f"Новая версия: {version}\n\n"
                       f"Скачать новую версию?")

            reply = QMessageBox.question(self.parent, "Обновление доступно", message,
                                         QMessageBox.Yes | QMessageBox.No)

            if reply == QMessageBox.Yes:
                webbrowser.open(download_url)
        else:
            # Fallback to releases page if direct download not found
            message = (f"Доступна новая версия!\n\n"
                       f"Текущая версия: {current}\n"
                       f"Новая версия: {version}\n\n"
                       f"Файл URMconfig.exe не найден в релизе.\n"
                       f"Открыть страницу релизов?")

            reply = QMessageBox.question(self.parent, "Обновление доступно", message,
                                         QMessageBox.Yes | QMessageBox.No)

            if reply == QMessageBox.Yes:
                webbrowser.open(fallback_url or GITHUB_RELEASES_URL)

    def _on_check_failed(self, error: str):
        """Handle check failure."""
        if not self.silent:
            QMessageBox.warning(self.parent, "Ошибка проверки обновлений",
                                f"Не удалось проверить обновления:\n{error}")

    def _on_no_update(self):
        """Handle no update available."""
        if not self.silent:
            QMessageBox.information(self.parent, "Обновления",
                                    "У вас установлена последняя версия.")

    def cleanup(self):
        """Clean up threads before application exit."""
        if self.checker and self.checker.isRunning():
            self.checker.terminate()
            self.checker.wait()


# Convenience functions for easy integration
def check_updates_silent(parent=None):
    """Check for updates without showing 'no update' message."""
    updater = Updater(parent)
    updater.check_for_updates(silent=True)


def check_updates_with_message(parent=None):
    """Check for updates and show result message."""
    updater = Updater(parent)
    updater.check_for_updates(silent=False)


def open_releases_page():
    """Open GitHub releases page in browser."""
    webbrowser.open(GITHUB_RELEASES_URL)