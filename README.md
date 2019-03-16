# sentinel2-tiles-download
Sentinel-2 satellite tiles images downloader from Copernicus. With this utility you can specify image resolution/bands to minimize download size.

Granules are packages containing data taken from Sentinel-2 satellite for a region on the globe in a specific time. They contain a lot of data for that area (13 bands in different resolutions and other derived bands and quality data). Level-2A products, for example, have ~1GB of data for a single tile (100km2 x 100km2). 

With this utility you can select which bands/resolutions to download. For example, if you need only the TCI band (true color) tile at 60m resolution, you will can use the utility to download just ~3MB of data (instead of 1GB!). For max resolution(10m), each band will have ~120MB. Some caching will be applied to avoid re-downloading of data that is already present in disk.

* For more information on Sentinel-2 satellite product data, go to https://sentinel.esa.int/documents/247904/685211/Sentinel-2-Products-Specification-Document

* If you want to download whole Granules (instead of only some files inside Granules), you can go to https://github.com/sentinelsat/sentinelsat or https://scihub.copernicus.eu/twiki/do/view/SciHubUserGuide/BatchScripting?redirectedfrom=SciHubUserGuide.8BatchScripting


## Usage

```shell
pip install git+https://github.com/flaviostutz/sentinel2-tiles-download
```

```python
import sentinelloader
#download true color image that contains lat/long point (-15,45) at 10m resolution
tiles = sentinelloader.download("/downloads", [(-15,45)], ('2019-01-01','2019-02-01'), ["10m"], ["tci"])
```

