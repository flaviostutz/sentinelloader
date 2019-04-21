from sentinelsat import SentinelAPI
from datetime import datetime
from datetime import timedelta
from shapely.geometry import Point, Polygon, mapping
from shapely.affinity import scale
import rasterio.features
import logging
from osgeo import ogr
from shapely.wkt import loads
import geopandas as gpd
import pandas as pd
import requests
import os
import re
import os.path
from osgeo import gdal
import hashlib
from PIL import Image
import uuid
import fiona
import numpy as np
import traceback
import pandas as pd
from .utils import *

logger = logging.getLogger('sentinelloader')

class Sentinel2Loader:

    def __init__(self, dataPath, user, password, apiUrl='https://scihub.copernicus.eu/apihub/', showProgressbars=True, dateToleranceDays=5, cloudCoverage=(0,80), deriveResolutions=True, cacheApiCalls=True, cacheTilesData=True, loglevel=logging.DEBUG, nirBand='B08'):
        logging.basicConfig(level=loglevel)
        self.api = SentinelAPI(user, password, apiUrl, show_progressbars=showProgressbars)
        self.dataPath = dataPath
        self.user = user
        self.password = password
        self.dateToleranceDays=dateToleranceDays
        self.cloudCoverage=cloudCoverage
        self.deriveResolutions=deriveResolutions
        self.cacheApiCalls=cacheApiCalls
        self.cacheTilesData=cacheTilesData
        self.nirBand=nirBand

    
    def getProductBandTiles(self, geoPolygon, bandName, resolution, dateReference):
        """Downloads and returns file names with Sentinel2 tiles that best fit the polygon area at the desired date reference. It will perform up/downsampling if deriveResolutions is True and the desired resolution is not available for the required band."""
        logger.debug("Getting contents. band=%s, resolution=%s, date=%s", bandName, resolution, dateReference)        
        
        #find tiles that intercepts geoPolygon within date-tolerance and date+dateTolerance
        dateTolerance = timedelta(days=self.dateToleranceDays)
        dateObj = datetime.now()
        if dateReference != 'now':
            dateObj = datetime.strptime(dateReference, '%Y-%m-%d')

        dateFrom = dateObj-dateTolerance
        dateTo = dateObj
        
        dateL2A = datetime.strptime('2018-12-18', '%Y-%m-%d')
        productLevel = '2A'
        if dateObj < dateL2A:
            logger.debug('Reference date %s before 2018-12-18. Will use Level1C tiles (no atmospheric correction)' % (dateObj))
            productLevel = '1C'
        
        resolutionDownload = resolution
        if self.deriveResolutions:
            if productLevel=='2A':
                if resolution=='10m':
                    if bandName in ['B01', 'B09']:
                        resolutionDownload = '60m'
                    elif bandName in ['B05', 'B06', 'B07', 'B11', 'B12', 'B8A', 'SCL']:
                        resolutionDownload = '20m'
                elif resolution=='20m':
                    if bandName in ['B08']:
                        resolutionDownload = '10m'
                    elif bandName in ['B01', 'B09']:
                        resolutionDownload = '60m'
                elif resolution=='60m':
                    if bandName in ['B08']:
                        resolutionDownload = '10m'
            elif productLevel=='1C':
                resolutionDownload = '10m'

        logger.debug("Querying API for candidate tiles")

        bbox = rasterio.features.bounds(geoPolygon)
        geoPolygon = [(bbox[0], bbox[3]), (bbox[0], bbox[1]),
            (bbox[2], bbox[1]), (bbox[2], bbox[3])]

        area = Polygon(geoPolygon).wkt
        
        #query cache key
        area_hash = hashlib.md5(area.encode()).hexdigest()
        apicache_file = self.dataPath + "/apiquery/Sentinel-2-S2MSI%s-%s-%s-%s-%s-%s.csv" % (productLevel, area_hash, dateFrom.strftime("%Y%m%d"), dateTo.strftime("%Y%m%d"), self.cloudCoverage[0], self.cloudCoverage[1])
        products_df = None
        if self.cacheApiCalls:
            if os.path.isfile(apicache_file):
                logger.debug("Using cached API query contents")
                products_df = pd.read_csv(apicache_file)
                os.system("touch -c %s" % apicache_file)
            else:
                logger.debug("Querying remote API")
                productType = 'S2MSI%s' % productLevel
                products = self.api.query(area, 
                                               date=(dateFrom.strftime("%Y%m%d"), dateTo.strftime("%Y%m%d")),
                                               platformname='Sentinel-2', producttype=productType, cloudcoverpercentage=self.cloudCoverage)
                products_df = self.api.to_dataframe(products)
                logger.debug("Caching API query results for later usage")
                saveFile(apicache_file, products_df.to_csv(index=True))

        logger.debug("Found %d products", len(products_df))

        if len(products_df)==0:
            raise Exception('Could not find any tiles for the specified parameters')
        
        products_df_sorted = products_df.sort_values(['ingestiondate','cloudcoverpercentage'], ascending=[False, False])

        #select the best product. if geoPolygon() spans multiple tiles, select the best of them
        missing = Polygon(geoPolygon)
        desiredRegion = Polygon(geoPolygon)
        selectedTiles = []
        footprints = [desiredRegion]

        for index, pf in products_df_sorted.iterrows():
            #osgeo.ogr.Geometry
            footprint = gmlToPolygon(pf['gmlfootprint'])
            
            if missing.area>0:
                if missing.intersects(footprint)==True:
                    missing = (missing.symmetric_difference(footprint)).difference(footprint)
                    selectedTiles.append(index)
                    footprints.append(footprint)                

        if missing.area>0:
            raise Exception('Could not find tiles for the whole selected area at date range')

        logger.debug("Tiles selected for covering the entire desired area: %s", selectedTiles)

#         g = gpd.GeoSeries(footprints)
#         g.plot(cmap=plt.get_cmap('jet'), alpha=0.5)

        #download tiles data
        tileFiles = []
        for index, sp in products_df.loc[selectedTiles].iterrows():
            url = "https://scihub.copernicus.eu/dhus/odata/v1/Products('%s')/Nodes('%s.SAFE')/Nodes('MTD_MSIL%s.xml')/$value" % (sp['uuid'], sp['title'], productLevel)
            meta_cache_file = self.dataPath + "/products/%s-MTD_MSIL%s.xml" % (sp['uuid'], productLevel)
            mcontents = ''
            if self.cacheTilesData and os.path.isfile(meta_cache_file):
                logger.debug('Reusing cached metadata info for tile \'%s\'', sp['uuid'])
                mcontents = loadFile(meta_cache_file)
                os.system("touch -c %s" % meta_cache_file)
            else:
                logger.debug('Getting metadata info for tile \'%s\' remotelly', sp['uuid'])
                r = requests.get(url, auth=(self.user, self.password))
                if r.status_code!=200:
                    raise Exception("Could not get metadata info. status=%s" % r.status_code)
                mcontents = r.content.decode("utf-8")
                saveFile(meta_cache_file, mcontents)

            rexp = "<IMAGE_FILE>GRANULE\/([0-9A-Z_]+)\/IMG_DATA\/([0-9A-Z_]+_%s)<\/IMAGE_FILE>" % (bandName)
            if productLevel=='2A':
                rexp = "<IMAGE_FILE>GRANULE\/([0-9A-Z_]+)\/IMG_DATA\/R%s\/([0-9A-Z_]+_%s_%s)<\/IMAGE_FILE>" % (resolutionDownload, bandName, resolutionDownload)

            m = re.search(rexp, mcontents)
            if m==None:
                raise Exception("Could not find image metadata. uuid=%s, resolution=%s, band=%s" % (sp['uuid'], resolutionDownload, bandName))

            rexp1 = "<PRODUCT_START_TIME>([\-0-9]+)T[0-9\:\.]+Z<\/PRODUCT_START_TIME>"
            m1 = re.search(rexp1, mcontents)
            if m1==None:
                raise Exception("Could not find product date from metadata")
                
            date1 = m1.group(1)
            downloadFilename = self.dataPath + "/products/%s/%s/%s.tiff" % (date1, sp['uuid'], m.group(2))
            if not os.path.exists(os.path.dirname(downloadFilename)):
                os.makedirs(os.path.dirname(downloadFilename))

            if not self.cacheTilesData or not os.path.isfile(downloadFilename):
                tmp_tile_filejp2 = "%s/tmp/%s.jp2" % (self.dataPath, uuid.uuid4().hex)
                tmp_tile_filetiff = "%s/tmp/%s.tiff" % (self.dataPath, uuid.uuid4().hex)
                if not os.path.exists(os.path.dirname(tmp_tile_filejp2)):
                    os.makedirs(os.path.dirname(tmp_tile_filejp2))
                    
                if productLevel=='2A':
                    url = "https://scihub.copernicus.eu/dhus/odata/v1/Products('%s')/Nodes('%s.SAFE')/Nodes('GRANULE')/Nodes('%s')/Nodes('IMG_DATA')/Nodes('R%s')/Nodes('%s.jp2')/$value" % (sp['uuid'], sp['title'], m.group(1), resolutionDownload, m.group(2))
                elif productLevel=='1C':
                    url = "https://scihub.copernicus.eu/dhus/odata/v1/Products('%s')/Nodes('%s.SAFE')/Nodes('GRANULE')/Nodes('%s')/Nodes('IMG_DATA')/Nodes('%s.jp2')/$value" % (sp['uuid'], sp['title'], m.group(1), m.group(2))
                    
                logger.info('Downloading tile uuid=\'%s\', resolution=\'%s\', band=\'%s\', date=\'%s\'', sp['uuid'], resolutionDownload, bandName, date1)
                downloadFile(url, tmp_tile_filejp2, self.user, self.password)
                #remove near black features on image border due to compression artifacts. if not removed, some black pixels 
                #will be present on final image, specially when there is an inclined crop in source images
                if bandName=='TCI':
                    logger.debug('Removing near black compression artifacts')
                    os.system("nearblack -o %s %s" % (tmp_tile_filetiff, tmp_tile_filejp2))
                    os.system("gdal_translate %s %s" % (tmp_tile_filetiff, downloadFilename))
                    os.remove(tmp_tile_filetiff)
                else:
                    os.system("gdal_translate %s %s" % (tmp_tile_filejp2, downloadFilename))
                os.remove(tmp_tile_filejp2)
                    
            else:
                logger.debug('Reusing tile data from cache')

            os.system("touch -c %s" % downloadFilename)

            filename = downloadFilename
            if resolution!=resolutionDownload:
                filename = self.dataPath + "/products/%s/%s/%s-%s.tiff" % (m1.group(1), sp['uuid'], m.group(2), resolution)
                logger.debug("Resampling band %s originally in resolution %s to %s" % (bandName, resolutionDownload, resolution))
                rexp = "([0-9]+).*"
                rnumber = re.search(rexp, resolution)
                if not self.cacheTilesData or not os.path.isfile(filename):
                    os.system("gdalwarp -tr %s %s %s %s" % (rnumber.group(1), rnumber.group(1), downloadFilename, filename))

            tileFiles.append(filename)

        return tileFiles

    def cropRegion(self, geoPolygon, sourceGeoTiffs):
        """Returns an image file with contents from a bunch of GeoTiff files cropped to the specified geoPolygon.
           Pay attention to the fact that a new file is created at each request and you should delete it after using it"""
        logger.debug("Cropping polygon from %d files" % (len(sourceGeoTiffs)))
        desiredRegion = Polygon(geoPolygon)

#         #show tile images
#         for fn in tilesData:
#             ds = gdal.Open(fn).ReadAsArray()
#             plt.figure(figsize=(10,10))
#             plt.imshow(ds[0])

        source_tiles = ' '.join(sourceGeoTiffs)
        tmp_file = "%s/tmp/%s.tiff" % (self.dataPath, uuid.uuid4().hex)
        if not os.path.exists(os.path.dirname(tmp_file)):
            os.makedirs(os.path.dirname(tmp_file))
        
        #define output bounds in destination srs reference
        bounds = desiredRegion.bounds
        s1 = convertWGS84To3857(bounds[0], bounds[1])
        s2 = convertWGS84To3857(bounds[2], bounds[3])

        logger.debug('Combining tiles into a single image. tmpfile=%s' % tmp_file)
        os.system("gdalwarp -multi -srcnodata 0 -t_srs EPSG:3857 -te %s %s %s %s %s %s" % (s1[0],s1[1],s2[0],s2[1],source_tiles,tmp_file))
        
        return tmp_file


    def getRegionHistory(self, geoPolygon, bandOrIndexName, resolution, dateFrom, dateTo, daysStep=5, ignoreMissing=True, minVisibleLand=0, keepVisibleWithCirrus=False, interpolateMissingDates=False):
        """Gets a series of GeoTIFF files for a region for a specific band and resolution in a date range"""
        logger.info("Getting region history for band %s from %s to %s at %s" % (bandOrIndexName, dateFrom, dateTo, resolution))
        dateFromObj = datetime.strptime(dateFrom, '%Y-%m-%d')
        dateToObj = datetime.strptime(dateTo, '%Y-%m-%d')
        dateRef = dateFromObj
        regionHistoryFiles = []
        
        lastSuccessfulFile = None
        pendingInterpolations = 0
        
        while dateRef <= dateToObj:
            logger.debug(dateRef)
            dateRefStr = dateRef.strftime("%Y-%m-%d")
            regionFile = None
            try:

                cirrus = 0
                if keepVisibleWithCirrus:
                    cirrus = 1

                if minVisibleLand > 0:
                    labelsFile = self.getRegionBand(geoPolygon, "SCL", resolution, dateRefStr)
                    ldata = gdal.Open(labelsFile).ReadAsArray()
                    ldata[ldata==1] = 0
                    ldata[ldata==2] = 0
                    ldata[ldata==3] = 0
                    ldata[ldata==4] = 1
                    ldata[ldata==5] = 1
                    ldata[ldata==6] = 1
                    ldata[ldata==7] = 0
                    ldata[ldata==8] = 0
                    ldata[ldata==9] = 0
                    ldata[ldata==10] = cirrus
                    ldata[ldata==11] = 1
                    os.remove(labelsFile)
                    
                    s = np.shape(ldata)
                    visibleLandRatio = np.sum(ldata)/(s[0]*s[1])

                    if visibleLandRatio<minVisibleLand:
                        raise Exception("Too few land shown in image. visible ratio=%s" % visibleLandRatio)
                    else:
                        logger.debug('Minimum visible land detected. visible ratio=%s' % visibleLandRatio)
                
                if bandOrIndexName in ['NDVI', 'NDWI', 'NDMI']:
                    regionFile = self.getRegionIndex(geoPolygon, bandOrIndexName, resolution, dateRefStr)
                else:
                    regionFile = self.getRegionBand(geoPolygon, bandOrIndexName, resolution, dateRefStr)
                tmp_tile_file = "%s/tmp/%s-%s-%s-%s.tiff" % (self.dataPath, dateRefStr, bandOrIndexName, resolution, uuid.uuid4().hex)

                useImage = True

                if pendingInterpolations>0:
                    previousData = gdal.Open(lastSuccessfulFile).ReadAsArray()
                    nextData = gdal.Open(regionFile).ReadAsArray()

#                     print(np.shape(previousData))
#                     print(np.shape(nextData))
                    na = np.empty(np.shape(previousData))
#                     print("INT")
#                     print(np.shape(na))
                    
                    logger.info("Calculating %s interpolated images" % pendingInterpolations)
                    series = pd.Series([previousData])
                    for i in range (0, pendingInterpolations):
                        series.add([na])
                    series.add([nextData])
                    idata = series.interpolate()
                    #FIXME NOT WORKING. PERFORM 2D TIME INTERPOLATION
                    raise Exception('Interpolation not yet implemented')
                    print(np.shape(idata))
                    
                    pendingInterpolations = 0

                #add good image
                os.system("mv %s %s" % (regionFile,tmp_tile_file))
                regionHistoryFiles.append(tmp_tile_file)
                lastSuccessfulFile = tmp_tile_file

            except Exception as e:
                if ignoreMissing:
                    logger.info("Couldn't get data for %s using the specified filter. err=%s" % (dateRefStr, e))
                else:
                    if interpolateMissingDates:
                        if lastSuccessfulFile!=None:
                            pendingInterpolations = pendingInterpolations + 1
                    else:
                        raise e

            dateRef = dateRef + timedelta(days=daysStep)
            
        return regionHistoryFiles
    
    def getRegionBand(self, geoPolygon, bandName, resolution, dateReference):
        regionTileFiles = self.getProductBandTiles(geoPolygon, bandName, resolution, dateReference)
        return self.cropRegion(geoPolygon, regionTileFiles)
    
    def _getBandDataFloat(self, geoPolygon, bandName, resolution, dateReference):
        bandFile = self.getRegionBand(geoPolygon, bandName, resolution, dateReference)
        
        gdalBand = gdal.Open(bandFile)
        geoTransform = gdalBand.GetGeoTransform()
        projection = gdalBand.GetProjection()
        
        data = gdalBand.ReadAsArray().astype(np.float)
        os.remove(bandFile)
        return data, geoTransform, projection
        
    def getRegionIndex(self, geoPolygon, indexName, resolution, dateReference):
        if indexName=='NDVI':
            #get band 04
            red,geoTransform,projection = self._getBandDataFloat(geoPolygon, 'B04', resolution, dateReference)
            #get band 08
            nir,_,_ = self._getBandDataFloat(geoPolygon, self.nirBand, resolution, dateReference)
            #calculate ndvi
            ndvi = ((nir - red)/(nir + red))
            #save file
            tmp_file = "%s/tmp/ndvi-%s.tiff" % (self.dataPath, uuid.uuid4().hex)
            saveGeoTiff(ndvi, tmp_file, geoTransform, projection)
            return tmp_file

        elif indexName=='NDWI':
            #get band 08
            b08,geoTransform,projection = self._getBandDataFloat(geoPolygon, self.nirBand, resolution, dateReference)
            #get band 11
            b11,_,_ = self._getBandDataFloat(geoPolygon, 'B11', resolution, dateReference)
            #calculate
            ndwi = ((b08 - b11)/(b08 + b11))
            #save file
            tmp_file = "%s/tmp/ndwi-%s.tiff" % (self.dataPath, uuid.uuid4().hex)
            saveGeoTiff(ndwi, tmp_file, geoTransform, projection)
            return tmp_file

        elif indexName=='NDMI':
            #get band 03
            nir,geoTransform,projection = self._getBandDataFloat(geoPolygon, 'B03', resolution, dateReference)
            #get band 08
            swir,_,_ = self._getBandDataFloat(geoPolygon, 'B10', resolution, dateReference)
            #calculate
            ndmi = ((nir - swir)/(nir + swir))
            #save file
            tmp_file = "%s/tmp/ndmi-%s.tiff" % (self.dataPath, uuid.uuid4().hex)
            saveGeoTiff(ndwi, tmp_file, geoTransform, projection)
            return tmp_file
        
        elif indexName=='EVI':
            #https://github.com/sentinel-hub/custom-scripts/tree/master/sentinel-2
            index = 2.5 * (B08 - B04) / ((B08 + 6.0 * B04 - 7.5 * B02) + 1.0)
            
            #get band 04
            b04,geoTransform,projection = self._getBandDataFloat(geoPolygon, 'B04', resolution, dateReference)
            #get band 08
            b08,_,_ = self._getBandDataFloat(geoPolygon, self.nirBand, resolution, dateReference)
            #get band 02
            b02,_,_ = self._getBandDataFloat(geoPolygon, 'B02', resolution, dateReference)
            #calculate
            evi = 2.5 * (b08 - b04) / ((b08 + (6.0 * b04) - (7.5 * b02)) + 1.0)
            #save file
            tmp_file = "%s/tmp/ndmi-%s.tiff" % (self.dataPath, uuid.uuid4().hex)
            saveGeoTiff(evi, tmp_file, geoTransform, projection)
            return tmp_file

        else:
            raise Exception('\'indexName\' must be NDVI or NDWI')
        
    def cleanupCache(self, filesNotUsedDays):
        os.system("find %s -type f -name '*' -mtime +%s -exec rm {} \;" % (self.dataPath, filesNotUsedDays))
        
