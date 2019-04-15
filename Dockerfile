FROM flaviostutz/datascience-tools:2.5.0

ENV COPERNICUS_USER ''
ENV COPERNICUS_PASSWORD ''

ADD setup.py /opt/setup.py

#just for caching purposes
RUN mkdir /opt/sentinelloader
RUN cd /opt && python setup.py install
RUN pip uninstall -y sentinelloader

ADD sentinelloader /opt/sentinelloader
RUN cd /opt && python setup.py install

ADD example.ipynb /notebooks/src/

ADD /test /notebooks/src/test

