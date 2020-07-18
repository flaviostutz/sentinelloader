FROM flaviostutz/datascience-tools:2.5.0

ENV COPERNICUS_USER ''
ENV COPERNICUS_PASSWORD ''

ADD setup.py /opt/setup.py

#just for caching purposes
RUN mkdir /opt/sentinelloader
RUN cd /opt && python setup.py install
RUN pip uninstall -y sentinelloader

ADD /notebooks /

ADD sentinelloader /opt/sentinelloader
RUN cd /opt && python setup.py install

