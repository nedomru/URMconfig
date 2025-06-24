import ftplib
import os
from datetime import datetime
from typing import Tuple, Optional


def upload_diagnostic_results(content: str, ftp_host: str = "212.33.255.58") -> Tuple[
    bool, Optional[str]]:
    """
    Upload diagnostic results to FTP server anonymously.

    Args:
        content (str): The diagnostic results text to upload
        ftp_host (str): FTP server hostname

    Returns:
        Tuple[bool, Optional[str]]: (Success status, Error message if failed)
    """
    try:
        # Generate filename with current date and time
        now = datetime.now()
        filename = f"OtcherURM-{now.strftime('%Y-%m-%d %H-%M-%S')}.txt"

        # Create FTP connection
        ftp = ftplib.FTP()
        ftp.connect(ftp_host, 21)  # Default FTP port

        # Anonymous login
        ftp.login('anonymous', 'anonymous@domain.com')

        # Change to diagnostic-results directory
        ftp.cwd('URMconfig')

        # Create a temporary file-like object from string content
        from io import BytesIO
        content_bytes = content.encode('cp1251')
        file_obj = BytesIO(content_bytes)

        # Upload the file
        ftp.storbinary(f'STOR {filename}', file_obj)

        # Close connection
        ftp.quit()

        return True, None

    except ftplib.error_perm as e:
        return False, f"FTP Permission Error: {str(e)}"
    except ftplib.error_temp as e:
        return False, f"FTP Temporary Error: {str(e)}"
    except ConnectionRefusedError:
        return False, "Connection refused - FTP server may be unavailable"
    except OSError as e:
        return False, f"Network Error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected Error: {str(e)}"


def test_ftp_connection(ftp_host: str = "212.33.255.58") -> Tuple[bool, Optional[str]]:
    """
    Test FTP connection to the server.

    Args:
        ftp_host (str): FTP server hostname

    Returns:
        Tuple[bool, Optional[str]]: (Success status, Error message if failed)
    """
    try:
        ftp = ftplib.FTP()
        ftp.connect(ftp_host, 21, timeout=10)
        ftp.login('anonymous', 'anonymous@domain.com')
        ftp.quit()
        return True, None
    except Exception as e:
        return False, str(e)