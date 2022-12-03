from setuptools import setup, find_packages

setup(name='server_chat_pyqt_001',
      version='0.1',
      description='Server_chat_pyqt',
      packages=find_packages(),
      author_email='volimots@mail.ru',
      author='GeekBrains',
      install_requeres=['PyQt5', 'sqlalchemy', 'pycryptodome']
      )
