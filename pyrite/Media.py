from pyrite.ImageReader import ImageReader
import os


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
    

    def _find_windows_media_devices(self) -> list:
        removable_drivers = []

        # Get all physical drives
        drives_info = list(filter(None, os.popen('wmic diskdrive get DeviceID,MediaType').read().strip().split('\n')[1:]))
        print(drives_info)

        for drive_info in drives_info:
            drive_info = drive_info.strip()
            drive_info = drive_info.replace('  ', ' ')
            print(drive_info)
            
            if drive_info:
                print(drive_info.split(' '))
                try:
                    device_id, media_type, _ = drive_info.split(' ')
                except:
                    device_id, media_type, _, _, _ = drive_info.split(' ')
                # Filter out system drives (assuming system drives are not removable)
                if media_type == 'Removable':
                    removable_drivers.append(device_id)

        return removable_drivers

    def _find_macos_media_devices(self) -> list:
        pass  # Will be added later


    def find_media_devices(self,
                           show_all: bool = False
                           ) -> list:
        """
        Returns a list of storage devices connected to the system.
        If show_all is set to True, the list will include all devices regardless of their system importance.
        :param show_all:
        :return:
        List of storage devices.
        """

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

    def _write_image_linux(self):
        with open(self._device_path, 'wb') as device:
            ir = ImageReader(self._image_path, check_extension=True)
            _index = 0
            
            for chunk in ir.read_image():
                _index += 1
                print(f'{int(_index / ir._amount_of_chunks * 100)}%')

                device.write(chunk)

            print('Flushing device...')
            device.flush()
            os.fsync(device.fileno())

        print('Image written successfully!')
        
    def _windows_wipe_device(self):
        import subprocess
        import re
        
        # Holy crud
        
        def find_drive_index():        
            try: 
                result = subprocess.run(
                    ['wmic', 'diskdrive', 'get', 'DeviceID,Index'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode != 0:
                    print(f"Error retrieving disk information: {result.stderr}")
                    return None
                
                for line in result.stdout.splitlines():
                    if self._device_path in line:
                        foundMatch = re.search(r'(\d+)', line)
                        if foundMatch:
                            return int(foundMatch.group(1))
                        
                print(f"Device not found: {self._device_path}")
                return None
            
            except Exception as e:
                print(f"An error occurred while fetching the disk number: {e}")
                return None
            
        drive_index = find_drive_index()
        if drive_index is None:
            print("Unable to find the drive index.")
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
                print(f"All partitions on disk {drive_index} (DeviceID: {self._device_path}) have been deleted successfully.")
            else:
                print(f"Error deleting partitions on disk {drive_index}:\n{process.stderr}")
        
        except Exception as e:
            print(f"An error occurred: {e}")
        
    def _write_image_windows(self):
        import win32file
        import win32con
        import pywintypes
        import time
                
        # Calling this function will requitre the user to have admin privileges, so take account of that.
        
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
                print(f'{int(_index / ir._amount_of_chunks * 100)}% written', end='\r')

                try:
                    win32file.WriteFile(_device_handle, chunk)
                    win32file.FlushFileBuffers(_device_handle)
                except pywintypes.error as e:
                    if e.winerror == 5:  # Access is denied
                        print(f'Error writing chunk {_index}: {e.strerror}')
                        break
                    elif e.winerror == 433:
                        print('Device disconnected. Reconnecting...')
                        win32file.CloseHandle(_device_handle)
                        time.sleep(1)
                        _device_handle = open_handle()
                    else:
                        raise e

            print('Image written successfully!')
        finally:
            win32file.CloseHandle(_device_handle)
            