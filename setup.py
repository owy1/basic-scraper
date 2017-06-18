"""This is the Setup."""
from setuptools import setup


setup(
    name='healthinspect',
    description='',
    version='0.1',
    author='Ophelia',
    license='MIT',
    py_modules=['healthinspect'],
    package_dir={'': 'src'},
    extras_require={'testing': ['pytest', 'pytest-watch', 'tox']}
)
