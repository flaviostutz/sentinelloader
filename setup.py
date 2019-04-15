from setuptools import setup, find_packages

setup(
    name='sentinelloader',
    version='1.0.0',
    url='https://github.com/flaviostutz/sentinelloader.git',
    author='Flávio Stutz',
    license='MIT',
    author_email= 'flaviostutz@gmail.com',
    description='Sentinel satellite data downloader with steroids',
    packages=find_packages(),
    install_requires=['uuid >= 1.3.0', 'gdal >= 2.2.2',
                      'requests >= 2.21.0', 'pandas >= 0.24.1', 
                      'geopandas >= 0.4.1', 'shapely >= 1.6.4', 
                      'sentinelsat >= 0.12.2'],
)
