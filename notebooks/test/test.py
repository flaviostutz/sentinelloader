import logging
import os
from osgeo import gdal
import matplotlib.pyplot as plt
from sentinelloader import Sentinel2Loader
logging.basicConfig(level=logging.DEBUG)

sl = Sentinel2Loader('/notebooks/data/output/sentinelcache', 
                    os.environ['COPERNICUS_USER'], os.environ['COPERNICUS_PASSWORD'],
                    apiUrl='https://apihub.copernicus.eu/apihub/', showProgressbars=True)

# area = [(-51.15, -14),(-51.8,-14),(-51.8,-14.25),(-51.15,-14.25),(-51.15,-14)]# area = [(-51.15, -14),(-51.8,-14),(-51.8,-14.25),(-51.15,-14.25),(-51.15,-14)]
area = [(-47.873796, -16.044801), (-47.933796, -16.044801),
        (-47.933796, -15.924801), (-47.873796, -15.924801)]
# area = [(-51.15, -14),(-52.1,-14),(-52.1,-14.25),(-51.15,-14.25),(-51.15,-14)]# area = [(-51.15, -14),(-51.8,-14),(-51.8,-14.25),(-51.15,-14.25),(-51.15,-14)]
# area = [(-44.8, -15),(-46.2,-15),(-46.2,-15.2),(-44.8,-15.2)]# area = [(-51.15, -14),(-51.8,-14),(-51.8,-14.25),(-51.15,-14.25),(-51.15,-14)]
# area = [(-50.45, -15.25),(-50.65, -15.25),(-50.65, -15.45),(-50.65, -15.45),(-49.5, -16.5)]
# area = [(-44.8, -15),(-45.3,-15),(-45.3,-15.2),(-44.8,-15.2)]# area = [(-51.15, -14),(-51.8,-14),(-51.8,-14.25),(-51.15,-14.25),(-51.15,-14)]
# geoTiffs = sl.getProductBandTiles(area, 'TCI', '60m', dateReference='2019-01-01', dateToleranceDays=20, cloudCoverage=(0,40))
# geoTiff = sl.cropRegion(area, geoTiffs)
# ds = gdal.Open(geoTiff).ReadAsArray()
# plt.figure(figsize=(44,44))
# plt.imshow(ds[0])
# plt.show()
# os.remove(geoTiff)

geoTiffs = sl.getRegionHistory(
    area, 'TCI', '60m', '2019-01-06', '2019-01-30', daysStep=5)
for geoTiff in geoTiffs:
    ds = gdal.Open(geoTiff).ReadAsArray()
    plt.figure(figsize=(5, 5))
    plt.imshow(ds[0])
    plt.show()
    os.remove(geoTiff)

# img = plt.imread(geoTiff)
# plt.imshow(img[:, :, 0], cmap=plt.cm.coolwarm)
# sl.getContents(area, 'TCI', '10m', dateReference='2019-01-01', dateToleranceDays=20, cloudCoverage=(0,40), cloudless=False, cloudlessDays=20)
# area = [(-44.8, -15),(-45.1,-15),(-45.1,-15.2),(-44.8,-15.2)]# area = [(-51.15, -14),(-51.8,-14),(-51.8,-14.25),(-51.15,-14.25),(-51.15,-14)]
# sl.getContents(area, 'TCI', '60m', dateReference='now', dateToleranceDays=20, cloudCoverage=(0,40), cloudless=False, cloudlessDays=20)
