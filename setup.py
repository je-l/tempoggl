import sys

from setuptools import setup, find_packages


if sys.version_info < (3, 6):
    sys.exit('Tempoggl requires python 3.6+')


setup(
    name='Tempoggl',
    url='https://github.com/je-l/tempoggl',
    packages=find_packages('.'),
    install_requires=[
        'pyhumps < 3.0.0, >= 1.2.2',
        'pydantic >= 1.0.0, < 2.0.0',
        'requests < 3.0.0, >= 2.21.0',
        'python-dateutil < 3.0.0, >= 2.0',
        'tzlocal < 3.0.0, >= 2.0.0',
    ],
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    entry_points={'console_scripts': ['tempoggl = tempoggl.__main__:run']},
)
