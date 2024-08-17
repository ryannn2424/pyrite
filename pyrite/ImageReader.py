import os


class ImageReader:
    def __init__(self,
                 image_path: str,
                 check_extension: bool = True,
                 ) -> None:

        self.image_path = image_path
        self._check_if_exists()

        if check_extension:  # Can be skipped by setting check_extension to False
            self._verify_file_extension()

        self.image_bytes = self._read_image()

    def _check_if_exists(self):
        if not os.path.exists(self.image_path):
            raise FileNotFoundError('File not found')

    def _verify_file_extension(self):
        _valid_extensions: list[str] = ['iso', 'img']
        if self.image_path.split('.')[-1] not in _valid_extensions:
            raise ValueError('Invalid file extension')

    def _read_image(self):
        with open(self.image_path, 'rb') as file:
            return file.read()
