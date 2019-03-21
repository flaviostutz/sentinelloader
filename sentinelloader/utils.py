import sys
import os
from osgeo import ogr
from shapely.geometry import Point, Polygon, mapping
import requests
import subprocess

def gmlToPolygon(gmlStr):
    footprint1 = ogr.CreateGeometryFromGML(gmlStr)
    coords = []
    if footprint1.GetGeometryCount() == 1:
        g0 = footprint1.GetGeometryRef(0)
        for i in range(0, g0.GetPointCount()):
            pt = g0.GetPoint(i)
            coords.append((pt[1], pt[0]))
    return Polygon(coords)


def downloadFile(url, filepath, user, password):
    if not os.path.exists(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath))

    with open(filepath, "wb") as f:
        print("Downloading %s to %s" % (url, filepath))
        response = requests.get(url, auth=(user, password), stream=True)
        if response.status_code != 200:
            raise Exception("Could not download file. status=%s" %
                            response.status_code)
        total_length = response.headers.get('content-length')

        if total_length is None:  # no content length header
            f.write(response.content)
        else:
            dl = 0
            total_length = int(total_length)
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                f.write(data)
                done = int(50 * dl / total_length)
                sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)))
                sys.stdout.flush()


def saveFile(filename, contents):
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    with open(filename, 'w') as fw:
        fw.write(contents)
        fw.flush()


def loadFile(filename):
    with open(filename, 'r') as fr:
        return fr.read()


def convertWGS84To3857(x, y):
    s1 = subprocess.check_output(["echo \"%s %s\" | cs2cs +init=epsg:4326 +to +init=epsg:3857" % (x,y)], shell=True)
    # s1 = !echo "{x} {y}" | cs2cs + init = epsg: 4326 + to + init = epsg: 3857
    s = s1.decode("utf-8").replace(" 0.00", "").split('\t')
    return (float(s[0]), float(s[1]))


def convertGeoJSONFromWGS84To3857(geojson):
    coords = []
    c = geojson['coordinates'][0]
    for co in list(c):
        coords.append(convertWGS84To3857(co[0], co[1]))
    geo = {
        'coordinates': ((tuple(coords)),),
        'type': geojson['type']
    }
    return geo

def saveGeoTiff(imageDataFloat, outputFile, geoTransform, projection):
    x_pixels = imageDataFloat.shape[0] # number of pixels in x
    y_pixels = imageDataFloat.shape[1] # number of pixels in y
    driver = gdal.GetDriverByName('GTiff')
    image_data = driver.Create(outputFile, x_pixels, y_pixels, 1, gdal.GDT_Float32)
    image_data.GetRasterBand(1).WriteArray(imageDataFloat)
    image_data.SetGeoTransform(geoTransform) 
    image_data.SetProjection(projection)
    image_data.FlushCache()
    image_data=None
