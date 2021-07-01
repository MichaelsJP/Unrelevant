FROM kartoza/postgis:latest 
# AS build?

RUN apt-get update && apt-get install -y \
    postgis \
    wget \
    unzip


RUN mkdir -p /data /data/pop
RUN chmod -R 777 /data


# get world pop raster layer
RUN wget https://cidportal.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_MT_GLOBE_R2019A/GHS_POP_E2015_GLOBE_R2019A_54009_250/V1-0/GHS_POP_E2015_GLOBE_R2019A_54009_250_V1_0.zip --output-document=/data/pop/GHS_POP_E2015_GLOBE_R2019A_54009_250_V1_0.zip
# better layer: https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/0_Mosaicked/ppp_2020_1km_Aggregated.tif but ~850mb

# unzip
RUN unzip /data/pop/GHS_POP_E2015_GLOBE_R2019A_54009_250_V1_0.zip -d /data/pop


# init files
# COPY 01_prep_data.sh docker-entrypoint-initdb.d/98_prep_data.sh
# COPY 02_initdb.sql docker-entrypoint-initdb.d/99_initdb.sql
