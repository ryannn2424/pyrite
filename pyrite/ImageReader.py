import os
import math


class ImageReader:
    """
    Class for reading writable image files.

    Attributes:
        image_path (str): Path to the image file.
        check_extension (bool): Whether to check the file extension of the image file.
        chunk_size (int): Size of the chunks (in bytes) to read the image file into.
        supported_image_formats (list[str]): List of supported image file formats.
    """
    def __init__(self,
                 image_path: str,
                 check_extension: bool = True,
                 chunk_size: int = 32768,
                 supported_image_formats: list[str] | None =None
                 ) -> None:

        if supported_image_formats is None:
            self._supported_image_formats = ['iso', 'img']
        else:
            self._supported_image_formats = supported_image_formats
        self.image_path = image_path
        self._check_if_exists()
        self._chunk_size = chunk_size
        self._amount_of_chunks: int = 0

        if check_extension:  # Can be skipped by setting check_extension to False
            self._verify_file_extension()

    def _check_if_exists(self):
        """
        Checks if the image file exists.
        """
        if not os.path.exists(self.image_path):
            raise FileNotFoundError('File not found')

    def _verify_file_extension(self):
        """
        Verifies that the file extension of the image file is supported.
        """
        if self.image_path.split('.')[-1] not in self._supported_image_formats:
            raise ValueError('Invalid file extension')
        
    def _calculate_chunk_amount(self):
        """
        Calculates total number of chunks to read the image file into.
        """
        file_size = os.path.getsize(self.image_path)
        num_chunks = math.ceil(file_size / self._chunk_size)
        self._amount_of_chunks = num_chunks
        return num_chunks

    def read_image(self):
        """
        Generator function that reads the image file in chunks.
        
        Yields:
            bytes: Chunks of the image file data with size specified by self._chunk_size
        """
        self._calculate_chunk_amount()
        with open(self.image_path, 'rb') as file:
            while True:
                chunk = file.read(self._chunk_size)
                if not chunk:
                    break
                yield chunk
