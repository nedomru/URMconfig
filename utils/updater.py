"""
Auto-updater module for URMconfig application (Windows only).

Simple and professional updater that checks GitHub releases,
downloads new versions, and handles installation.
"""

import os
import subprocess
import sys
import tempfile
from typing import Optional, Tuple

import requests
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QProgressDialog

# Application constants
GITHUB_API_URL = "https://api.github.com/repos/nedomru/URMconfig/releases/latest"
CURRENT_VERSION = "1.1"  # Update this with each release
TIMEOUT = 30  # seconds


class UpdateChecker(QThread):
    """Background thread for checking updates."""

    update_available = pyqtSignal(str, str, str)  # version, download_url, release_notes
    update_check_failed = pyqtSignal(str)
    no_update_available = pyqtSignal()

    def run(self):
        """Check for updates in background."""
        try:
            has_update, version, url, notes = check_for_updates()
            if has_update:
                self.update_available.emit(version, url, notes)
            else:
                self.no_update_available.emit()
        except Exception as e:
            self.update_check_failed.emit(str(e))


class UpdateDownloader(QThread):
    """Background thread for downloading updates."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(str)  # file_path
    error = pyqtSignal(str)

    def __init__(self, url: str, file_path: str):
        super().__init__()
        self.url = url
        self.file_path = file_path

    def run(self):
        """Download the update file."""
        try:
            response = requests.get(self.url, stream=True, timeout=TIMEOUT)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(self.file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.progress.emit(progress)

            self.finished.emit(self.file_path)

        except Exception as e:
            self.error.emit(str(e))


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
    """Find Windows executable download URL from release assets."""
    for asset in assets:
        name = asset['name'].lower()
        if name.endswith('.exe') and 'urmconfig' in name:
            return asset['browser_download_url']
    return None


def check_for_updates() -> Tuple[bool, str, Optional[str], str]:
    """
    Check if newer version is available.

    Returns:
        tuple: (has_update, latest_version, download_url, release_notes)
    """
    release_info = get_latest_release()
    if not release_info:
        raise Exception("Не удалось получить информацию о релизах")

    latest_version = release_info.get('tag_name', '')
    release_notes = release_info.get('body', 'Нет описания изменений')
    current_version = get_current_version()

    has_update = is_newer_version(current_version, latest_version)
    download_url = None

    if has_update:
        assets = release_info.get('assets', [])
        download_url = find_exe_download_url(assets)

    return has_update, latest_version, download_url, release_notes


def install_update(update_file: str):
    """Install update and restart application."""
    if not getattr(sys, 'frozen', False):
        raise Exception("Автообновление доступно только для exe версии")

    current_exe = sys.executable

    # Create batch script for update
    batch_content = f'''@echo off
timeout /t 2 /nobreak > nul
move /y "{update_file}" "{current_exe}"
if errorlevel 1 (
    echo Ошибка при обновлении
    pause
    exit /b 1
)
start "" "{current_exe}"
del "%~f0"
'''

    batch_file = os.path.join(tempfile.gettempdir(), 'urmconfig_update.bat')

    try:
        with open(batch_file, 'w', encoding='cp1251') as f:
            f.write(batch_content)

        # Start update process and exit
        subprocess.Popen(['cmd', '/c', batch_file],
                         creationflags=subprocess.CREATE_NO_WINDOW)
        sys.exit(0)

    except Exception as e:
        raise Exception(f"Ошибка при создании скрипта обновления: {e}")


class Updater:
    """Main updater class for user interaction."""

    def __init__(self, parent=None):
        self.parent = parent
        self.checker = None
        self.downloader = None
        self.progress_dialog = None

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

    def _on_update_available(self, version: str, download_url: str, notes: str):
        """Handle update available."""
        if not download_url:
            QMessageBox.warning(self.parent, "Ошибка обновления",
                                "Новая версия найдена, но файл для загрузки недоступен.")
            return

        current = get_current_version()

        # Truncate release notes if too long
        if len(notes) > 300:
            notes = notes[:300] + "..."

        message = (f"Доступна новая версия URMconfig!\n\n"
                   f"Текущая версия: {current}\n"
                   f"Новая версия: {version}\n\n"
                   f"Обновить сейчас?")

        reply = QMessageBox.question(self.parent, "Обновление доступно", message,
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            self._download_update(download_url)

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

    def _download_update(self, url: str):
        """Download the update file."""
        # Don't start new download if one is already running
        if self.downloader and self.downloader.isRunning():
            return

        file_path = os.path.join(tempfile.gettempdir(), 'URMconfig_update.exe')

        # Remove existing file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

        # Show progress dialog
        self.progress_dialog = QProgressDialog("Загрузка обновления...", "Отмена", 0, 100, self.parent)
        self.progress_dialog.setWindowTitle("Загрузка")
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()

        # Start download
        self.downloader = UpdateDownloader(url, file_path)
        self.downloader.progress.connect(self.progress_dialog.setValue)
        self.downloader.finished.connect(self._on_download_finished)
        self.downloader.error.connect(self._on_download_error)
        self.downloader.finished.connect(self._on_download_thread_finished)
        self.downloader.error.connect(self._on_download_thread_finished)
        self.progress_dialog.canceled.connect(self._on_download_canceled)
        self.downloader.start()

    def _on_download_thread_finished(self):
        """Handle downloader thread completion."""
        if self.downloader:
            self.downloader.wait()  # Wait for thread to fully finish
            self.downloader = None

    def _on_download_canceled(self):
        """Handle download cancellation."""
        if self.downloader and self.downloader.isRunning():
            self.downloader.terminate()
            self.downloader.wait()
            self.downloader = None

    def _on_download_finished(self, file_path: str):
        """Handle download completion."""
        self.progress_dialog.close()

        reply = QMessageBox.question(self.parent, "Загрузка завершена",
                                     "Обновление загружено.\n"
                                     "Установить сейчас?\n\n"
                                     "(Программа будет перезапущена)",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                install_update(file_path)
            except Exception as e:
                QMessageBox.critical(self.parent, "Ошибка установки",
                                     f"Не удалось установить обновление:\n{e}")

    def _on_download_error(self, error: str):
        """Handle download error."""
        if self.progress_dialog:
            self.progress_dialog.close()
        QMessageBox.critical(self.parent, "Ошибка загрузки",
                             f"Не удалось загрузить обновление:\n{error}")

    def cleanup(self):
        """Clean up threads before application exit."""
        if self.checker and self.checker.isRunning():
            self.checker.terminate()
            self.checker.wait()

        if self.downloader and self.downloader.isRunning():
            self.downloader.terminate()
            self.downloader.wait()

        if self.progress_dialog:
            self.progress_dialog.close()


# Convenience functions for easy integration
def check_updates_silent(parent=None):
    """Check for updates without showing 'no update' message."""
    updater = Updater(parent)
    updater.check_for_updates(silent=True)


def check_updates_with_message(parent=None):
    """Check for updates and show result message."""
    updater = Updater(parent)
    updater.check_for_updates(silent=False)
