import os


def _detect_os() -> str:
    _os_scan = os.uname()
    _os_type = _os_scan.sysname

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
        pass  # Will be added later


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
            case 'Windows':
                return self._find_windows_media_devices()
            case 'macOS':
                return self._find_macos_media_devices()

        if show_all:
            return _device_dict['r'] + _device_dict['nr']
        else:
            return _device_dict['r']


class MediaWriter:
    def __init__(self,
                 device_path: str,
                 chunk_list: bytes,
                 os_type: str | None = None
                 ) -> None:

        self._chunk_list = chunk_list
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
                pass
            case 'macOS':
                pass

    def _write_image_linux(self):
        with open(self._device_path, 'wb') as device:
            _index = 0
            for chunk in self._chunk_list:
                _index += 1
                print(f'{int(_index / len(self._chunk_list) * 100)}%')

                device.write(chunk)

            print('Flushing device...')
            device.flush()
            os.fsync(device.fileno())

        print('Image written successfully!')



