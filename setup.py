"""This is the Setup."""
from setuptools import setup


setup(
    name='healthinspect',
    description='',
    version='0.1',
    author='Ophelia',
    license='MIT',
    py_modules=['scraper'],
    package_dir={'': 'src'},
    install_requires=['beautifulsoup4', 'requests']
    extras_require={'testing': ['pytest', 'pytest-watch', 'tox']}
)
