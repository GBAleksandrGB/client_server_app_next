from setuptools import setup, find_packages

setup(name='client_chat_pyqt_001',
      version='0.1',
      description='client_chat_pyqt5',
      packages=find_packages(),
      author_email='volimots@mail.ru',
      author='GeekBrains',
      install_requeres=['PyQt5', 'sqlalchemy', 'pycryptodome']
      )
