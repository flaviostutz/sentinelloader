FROM flaviostutz/datascience-tools:2.0.0

ENV COPERNICUS_USER ''
ENV COPERNICUS_PASSWORD ''

RUN apt-get install -y software-properties-common
RUN apt-add-repository -y ppa:ubuntugis/ubuntugis-unstable
RUN apt-get update
RUN apt-get install -y gdal-bin python-gdal python3-gdal

ADD setup.py /opt/setup.py

#just for caching purposes
RUN mkdir /opt/sentinelloader
RUN cd /opt && python setup.py install --record files.txt
# RUN cd /opt && cat files.txt | xargs rm -rf
RUN pip uninstall -y sentinelloader

ADD sentinelloader /opt/sentinelloader
RUN cd /opt && python setup.py install

ADD /test.py /