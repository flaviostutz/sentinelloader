# sentinelloader
Sentinel-2 satellite tiles images downloader from Copernicus. 

With this utility you can specify the desired polygon, image resolution, band name and aproximate dates and it will do the best effort to find all tiles needed to satisfy your requirement, will download minimal data for this task, combine all tiles, crop to the polygon and cache the results, returning an GeoTIFF image with raster for the selected area.

Basically the library provides:


# Background

Granules are packages containing data taken from Sentinel-2 satellite for a region on the globe in a specific time. They contain a lot of data for that area (13 bands in different resolutions and other derived bands and quality data). Level-2A products, for example, have ~1GB of data for a single tile (100km2 x 100km2). 

With this utility you can select which bands/resolutions to download. For example, if you need only the TCI band (true color) tile at 60m resolution, you will can use the utility to download just ~3MB of data (instead of 1GB!). For max resolution(10m), each band will have ~120MB. Some caching will be applied to avoid re-downloading of data that is already present in disk.

* For more information on Sentinel-2 satellite product data, go to https://sentinel.esa.int/documents/247904/685211/Sentinel-2-Products-Specification-Document

* If you want to download whole Granules (instead of only some files inside Granules), you can go to https://github.com/sentinelsat/sentinelsat or https://scihub.copernicus.eu/twiki/do/view/SciHubUserGuide/BatchScripting?redirectedfrom=SciHubUserGuide.8BatchScripting


## Usage

```shell
pip install git+https://github.com/flaviostutz/sentinelloader
```

```python
import logging
import os
from osgeo import gdal
import matplotlib.pyplot as plt
from sentinelloader import SentinelLoader

sl = SentinelLoader('/notebooks/data/output/sentinelcache', 
                    'mycopernicususername', 'mycopernicuspassword',
                    apiUrl='https://scihub.copernicus.eu/apihub/', showProgressbars=True, loglevel=logging.DEBUG)

area = [(-47.873796, -16.044801), (-47.933796, -16.044801),
        (-47.933796, -15.924801), (-47.873796, -15.924801)]

geoTiffs = sl.getRegionHistory(area, 'TCI', '60m', '2019-01-06', '2019-01-30', daysStep=5,dateToleranceDays=5)
for geoTiff in geoTiffs:
    print('Desired image was prepared at')
    print(geoTiff)
    os.remove(geoTiff)
)
```

For a Jupyter example, [click here](example.ipynb)