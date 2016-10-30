Dependencies
############

Aptitude
********

Packages to be installed:

- python3-psycopg2
- python3-pil.imagetk
- python3-pip
- python3-reportlab

python3-pil.imagetk installs the Pillow library, a python3 clone of the
original PIL. It needs binary graphic libraries like libjpeg, libzlib,
libtiff.

Pip
***

- injector 0.9.1
- Pmw 2.0.1
- SQLAlchemy 1.0 Current patch level: 12
- chardet 2.3.0 (already installed on Debian)

For development
***************

Through aptitude: python3-sphinx, python3-coverage

Through pip3: pylint

On Windows
**********

Download the 3.4 installer from https://www.python.org/downloads/windows
and install Python

Open window shell

pip install psycopg2
pip install injector
pip install pmw
pip install sqlalchemy
pip install pillow