#!/bin/sh
echo "upload worldpop data"

GHS_POP_E2015_GLOBE_R2019A_54009_250_V1_0
raster2pgsql -Y -c -C -I -M -t 250x250 -s 4326 /data/pop/wpop_unconstrained_global.tif public.wpop | psql -U iso_access