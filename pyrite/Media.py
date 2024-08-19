from pyrite.ImageReader import ImageReader
import logging
import os

logger = logging.getLogger(__name__)

def _detect_os() -> str:
    try:
        _os_scan = os.uname()
        _os_type = _os_scan.sysname
    except:
        try:  # I'm putting the import here to reduce import times as much as possible & use as little imports as I can.
            import platform
            _os_scan = platform.uname()
            _os_type = _os_scan.system
        except:
            raise ValueError('Unable to detect OS. Use the os_type parameter to specify the OS.')

    match _os_type:
        case 'Linux':
            return 'Linux'
        case 'Windows':
            return 'Windows'
        case 'Darwin':
            return 'macOS'
        case _:
            # Library only supports Windows, Linux, and macOS for now.
            raise ValueError('Unsupported OS')


class MediaFinder:
    def __init__(self,
                 os_type: str | None = None
                 ) -> None:

        if os_type is None:
            self.os_type = _detect_os()
        elif os_type not in ['Linux', 'Windows', 'macOS']:
            raise ValueError('Unsupported OS')
        else:
            self.os_type = os_type

    def _find_linux_media_devices(self) -> dict:
        _sorted_devices: dict = {  # This dictionary attempts to distinguish removable devices from system drives.
            'r': [],  # Removable
            'nr': []  # Non-removable
        }

        _devices: list[str] = os.listdir('/sys/block')

        for device in _devices:
            _removable_status = open(f'/sys/block/{device}/removable', 'r').read().replace('\n', '')
            if bool(int(_removable_status)):
                _sorted_devices['r'].append(f"/dev/{device}")
            else:
                _sorted_devices['nr'].append(f"/dev/{device}")

        return _sorted_devices


    def _find_windows_media_devices(self) -> dict:
        _sorted_devices = {
            'r': [],  # Removable
            'nr': []  # Non-removable
        }
        # Get all physical drives
        drives_info = list(filter(None,
                                  os.popen('wmic diskdrive get DeviceID,MediaType').read().strip().split('\n')[1:]))

        for drive_info in drives_info:
            drive_info = drive_info.strip()
            drive_info = drive_info.replace('  ', ' ')

            if drive_info:
                try:
                    device_id, media_type, _ = drive_info.split(' ')
                except:
                    device_id, media_type, _, _, _ = drive_info.split(' ')
                # Filter out system drives (assuming system drives are not removable)
                if media_type == 'Removable':
                    _sorted_devices['r'].append(device_id)
                else:
                    _sorted_devices['nr'].append(device_id)

        return _sorted_devices

    def _find_macos_media_devices(self) -> list:
        pass  # Will be added later


    def find_media_devices(self,
                           show_all: bool = False
                           ) -> list:
        _device_dict: dict = {}

        match self.os_type:
            case 'Linux':
                _device_dict = self._find_linux_media_devices()

                if show_all:
                    return _device_dict['r'] + _device_dict['nr']
                else:
                    return _device_dict['r']

            case 'Windows':  # This returns the device ID, not the device name.
                return self._find_windows_media_devices()
            case 'macOS':
                return self._find_macos_media_devices()



class MediaWriter:
    def __init__(self,
                 device_path: str,
                 image_path: str,
                 os_type: str | None = None
                 ) -> None:

        self._image_path = image_path
        self._device_path = device_path
        self.write_progress_percent: int = 0

        if os_type is None:
            self._os_type = _detect_os()
        elif os_type not in ['Linux', 'Windows', 'macOS']:
            raise ValueError('Unsupported OS')
        else:
            self._os_type = os_type

    def write_image(self):
        match self._os_type:
            case 'Linux':
                self._write_image_linux()
            case 'Windows':
                self._write_image_windows()
            case 'macOS':
                pass

    def _linux_wipe_device(self):
        import subprocess
        # We simply use sfdisk to delete the partition table. Most systems ship with fdisk installed, so we're assuming it's installed.

        logger.info('Wiping device with dd (Linux)')

        try:
            wipe_command = ['sfdisk', '--delete', self._device_path]  # We're also assuming fdisk is installed.

            subprocess.run(wipe_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f'Device {self._device_path} wiped successfully.')
        except subprocess.CalledProcessError as e:
            logger.error(f"An error occurred while creating the partition table: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    def _write_image_linux(self):
        self._linux_wipe_device()

        logger.debug('Attempting to write image to device (Linux)')
        with open(self._device_path, 'wb') as device:
            ir = ImageReader(self._image_path, check_extension=True)
            _index = 0

            for chunk in ir.read_image():
                _index += 1
                # print(f'{int(_index / ir._amount_of_chunks * 100)}%', end='\r')
                self.write_progress_percent = int(_index / ir._amount_of_chunks * 100)

                device.write(chunk)

            logger.debug('Flushing device...')
            device.flush()
            os.fsync(device.fileno())

        logger.info(f'Image written successfully to {self._device_path}')

    def _windows_wipe_device(self):
        import subprocess
        import re

        # Holy crud
        logger.debug('Wiping device with diskpart (Windows)')

        def find_drive_index():
            try:
                result = subprocess.run(
                    ['wmic', 'diskdrive', 'get', 'DeviceID,Index'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode != 0:
                    logger.error(f"Error retrieving disk information: {result.stderr}")
                    return None

                for line in result.stdout.splitlines():
                    if self._device_path in line:
                        found_match = re.search(r'(\d+)', line)
                        if found_match:
                            return int(found_match.group(1))

                logger.error(f"Device not found: {self._device_path}")
                return None

            except Exception as diskpart_error:
                logger.error(f"An error occurred while fetching the disk number: {diskpart_error}")
                return None

        drive_index = find_drive_index()
        if drive_index is None:
            logger.error("Unable to find the drive index.")
            return

        diskpart_script = f"""
        select disk {drive_index}
        clean
        """

        # Run the diskpart script
        try:
            process = subprocess.run(
                ['diskpart'],
                input=diskpart_script,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Check for errors
            if process.returncode == 0:
                logger.debug(f"All partitions on disk {drive_index} (DeviceID: {self._device_path}) have been deleted successfully.")
            else:
                logger.error(f"Error deleting partitions on disk {drive_index}:\n{process.stderr}")

        except Exception as e:
            logger.error(f"An error occurred: {e}")

    def _write_image_windows(self):
        #  These libraries ONLY work on Windows.
        import win32file
        import win32con
        import pywintypes
        import time

        self._windows_wipe_device()  # Wiping the device with diskpart before otherwise windows throws a fit

        def open_handle():
            return win32file.CreateFile(
                self._device_path,
                win32con.GENERIC_WRITE,
                0,
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )

        _device_handle = open_handle()

        try:
            ir = ImageReader(image_path=self._image_path, check_extension=True)
            _index = 0
            for chunk in ir.read_image():
                _index += 1
                # print(f'{int(_index / ir._amount_of_chunks * 100)}% written', end='\r')
                self.write_progress_percent = int(_index / ir._amount_of_chunks * 100)

                try:
                    win32file.WriteFile(_device_handle, chunk)
                    win32file.FlushFileBuffers(_device_handle)
                except pywintypes.error as e:
                    if e.winerror == 5:  # Access is denied error
                        logger.error(f'Access denied when writing chunk {_index}: {e.strerror}')
                        break
                    elif e.winerror == 433:  # This error occurs when the device is disconnected. We can try to reconnect by opening another handle.
                        logger.debug('Device disconnected. Reconnecting...')
                        win32file.CloseHandle(_device_handle)
                        time.sleep(1)
                        _device_handle = open_handle()
                    else:  # Handles other fatal errors
                        raise e

            logger.info('Image written successfully!')
        finally:
            win32file.CloseHandle(_device_handle)
