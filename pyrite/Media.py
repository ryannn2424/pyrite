from pyrite.ImageReader import ImageReader
import logging
import subprocess
import os

logger = logging.getLogger(__name__)

def _detect_os() -> str:
    try:
        os_scan = os.uname()
        os_type = os_scan.sysname
    except:
        try:  # I'm putting the import here to reduce import times as much as possible & use as little imports as I can.
            import platform
            os_scan = platform.uname()
            os_type = os_scan.system
        except:
            raise ValueError('Unable to detect OS. Use the os_type parameter to specify the OS.')

    match os_type:
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
        sorted_devices: dict = {  # This dictionary attempts to distinguish removable devices from system drives.
            'r': [],  # Removable
            'nr': []  # Non-removable
        }

        devices: list[str] = os.listdir('/sys/block')

        for device in devices:
            removable_status = open(f'/sys/block/{device}/removable', 'r').read().replace('\n', '')
            device_name = "NNF"

            try:
                device_name = open(f'/sys/block/{device}/device/model', 'r').read().replace('\n', '').strip()
            except Exception as e:
                logger.error(f"Unable to read device name for {device}: {e}")

            if bool(int(removable_status)):
                sorted_devices['r'].append((f"/dev/{device}", device_name))
            else:
                sorted_devices['nr'].append((f"/dev/{device}", device_name))

        return sorted_devices

    def _find_windows_media_devices(self) -> dict:
        sorted_devices = {
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
                    sorted_devices['r'].append(device_id)
                else:
                    sorted_devices['nr'].append(device_id)

        return sorted_devices

    def _find_macos_media_devices(self) -> dict:
        sorted_devices = {
            'r': [],  # Removable
            'nr': []  # Non-removable
        }

        try:
            scan_results = subprocess.run(['diskutil', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if scan_results.returncode != 0:
                logger.error(f"An error occurred while scanning for devices: {scan_results.stderr}")

            for line in scan_results.stdout.splitlines():
                if '/dev/disk' in line:
                    device = line.split()[0]
                    info_results = subprocess.run(['diskutil', 'info', device], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    trimmed_info_results = info_results.stdout.replace(' ','')

                    if info_results.returncode != 0:
                        logger.error(f"An error occurred while fetching device information: {info_results.stderr}")

                    if 'Protocol:DiskImage' not in trimmed_info_results:
                        device_name = 'NNF'  # No Name Found
                        for device_specific_line in trimmed_info_results.splitlines():
                            if 'Device/MediaName:' in device_specific_line:
                                device_name = device_specific_line.split('Device/MediaName:')[1]
                        if 'RemovableMedia:Removable' in trimmed_info_results:
                            sorted_devices['r'].append([device, device_name])
                        else:
                            sorted_devices['nr'].append([device, device_name])

            return sorted_devices

        except Exception as e:
            logger.error(f"An error occurred while scanning for devices: {e}")

    def find_media_devices(self,
                           show_all: bool = False
                           ) -> list:
        device_dict: dict = {}

        match self.os_type:
            case 'Linux':
                device_dict = self._find_linux_media_devices()
            case 'Windows':  # This returns the device ID, not the device name.
                device_dict = self._find_windows_media_devices()
            case 'macOS':
                device_dict = self._find_macos_media_devices()

        if show_all:
            return device_dict['r'] + device_dict['nr']
        else:
            return device_dict['r']

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
                self._write_image_macos()

    def _linux_wipe_device(self):
        # We simply use sfdisk to delete the partition table. Most systems ship with fdisk installed, so we're assuming it's installed.

        logger.info('Wiping device with sfdisk (Linux)')

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
            index = 0

            for chunk in ir.read_image():
                index += 1
                # print(f'{int(_index / ir._amount_of_chunks * 100)}%', end='\r')
                self.write_progress_percent = int(index / ir._amount_of_chunks * 100)

                device.write(chunk)

            logger.debug('Flushing device...')
            device.flush()
            os.fsync(device.fileno())

        logger.info(f'Image written successfully to {self._device_path}')

    def _windows_wipe_device(self):
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

        try:
            process = subprocess.run(
                ['diskpart'],
                input=diskpart_script,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

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

        device_handle = open_handle()

        try:
            ir = ImageReader(image_path=self._image_path, check_extension=True)
            index = 0
            for chunk in ir.read_image():
                index += 1
                # print(f'{int(_index / ir._amount_of_chunks * 100)}% written', end='\r')
                self.write_progress_percent = int(index / ir._amount_of_chunks * 100)

                try:
                    win32file.WriteFile(device_handle, chunk)
                    win32file.FlushFileBuffers(device_handle)
                except pywintypes.error as e:
                    if e.winerror == 5:  # Access is denied error
                        logger.error(f'Access denied when writing chunk {index}: {e.strerror}')
                        break
                    elif e.winerror == 433:  # This error occurs when the device is disconnected. We can try to reconnect by opening another handle.
                        logger.debug('Device disconnected. Reconnecting...')
                        win32file.CloseHandle(device_handle)
                        time.sleep(1)
                        device_handle = open_handle()
                    else:  # Handles other fatal errors
                        raise e

            logger.info('Image written successfully!')
        finally:
            win32file.CloseHandle(device_handle)

    def _macos_wipe_device(self):
        wipe_command = ['diskutil', 'eraseDisk', '-noEFI', 'FREE', 'GPT', self._device_path]

        wipe_results = subprocess.run(wipe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:

            if wipe_results.returncode != 0:
                logger.error(f"An error occurred while wiping the device: {wipe_results.stderr}")
            else:
                logger.info(f"Device {self._device_path} wiped successfully.")

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

    def _write_image_macos(self):
        self._macos_wipe_device()

        logger.debug('Attempting to write image to device (macOS)')
        with open(self._device_path, 'wb') as device:
            ir = ImageReader(self._image_path, check_extension=True)
            index = 0

            for chunk in ir.read_image():
                index += 1
                self.write_progress_percent = int(index / ir._amount_of_chunks * 100)
                print(f'{self.write_progress_percent}%', end='\r')

                device.write(chunk)

            logger.debug('Flushing device...')
            device.flush()
            os.fsync(device.fileno())

