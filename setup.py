from setuptools import setup, find_packages

setup(
    name='BKVisionCamera',
    version='0.0.2',
    description='BKVisionCamera',
    author='BKVision',
    author_email='',
    license="MIT Licence",
    packages=find_packages(exclude=('BKVisionCamera', 'utils')),
    platforms="any",
    package_data={
    },
    install_requires=[],
    zip_safe=False
)
