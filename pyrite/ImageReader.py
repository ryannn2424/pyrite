import os
import math


class ImageReader:
    def __init__(self,
                 image_path: str,
                 check_extension: bool = True,
                 chunk_size: int = 32768,
                 _supported_image_formats: list[str] | None =None
                 ) -> None:

        if _supported_image_formats is None:
            self._supported_image_formats = ['iso', 'img']
        else:
            self._supported_image_formats = _supported_image_formats
        self.image_path = image_path
        self._check_if_exists()
        self._chunk_size = chunk_size
        self._amount_of_chunks: int = 0

        if check_extension:  # Can be skipped by setting check_extension to False
            self._verify_file_extension()

    def _check_if_exists(self):
        if not os.path.exists(self.image_path):
            raise FileNotFoundError('File not found')

    def _verify_file_extension(self):
        if self.image_path.split('.')[-1] not in self._supported_image_formats:
            raise ValueError('Invalid file extension')
        
    def _calculate_chunk_amount(self):
        _file_size = os.path.getsize(self.image_path)
        _num_chunks = math.ceil(_file_size / self._chunk_size)
        self._amount_of_chunks = _num_chunks
        return _num_chunks

    def read_image(self):  # Old function is incredibly memory inefficient sooo
        self._calculate_chunk_amount()
        with open(self.image_path, 'rb') as file:
            while True:
                chunk = file.read(self._chunk_size)
                if not chunk:
                    break
                yield chunk
