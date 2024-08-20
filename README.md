# pyrite
### A Python (v3.12+) library for finding Storage Devices and flashing Images onto Storage Devices.
This library is my first library I've ever made, so please give me feedback! I would love to improve it.

## About
- **pyrite** aims to be as simple as possible while providing the proper functionality needed to flash images.
- **pyrite** uses (**_Except for Windows_**) built in libraries to perform all of its functions, using built-in system
programs when necessary. Used external commands are as follows:
  - **Linux: <a href='https://man7.org/linux/man-pages/man8/sfdisk.8.html'>sfdisk</a>**
  - **macOS: <a href='https://www.unix.com/man-page/osx/8/diskutil/'>diskutil</a>**
  - **Windows: <a href='https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/diskpart'>diskpart</a>**
- The only exception to not using external libraries is the <a href='https://pypi.org/project/pywin32/'>**_pywin32_**</a>
  library, which is used for device handling on **Windows**. Other platforms do not need this library.