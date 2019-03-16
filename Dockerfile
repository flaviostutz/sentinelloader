FROM flaviostutz/datascience-tools:2.0.0

ENV COPERNICUS_USER ''
ENV COPERNICUS_PASSWORD ''

RUN pip install sentinelsat

