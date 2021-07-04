echo "upload worldpop data"

# GHS_POP_E2015_GLOBE_R2019A_54009_250_V1_0,

psql -h postgres -U yasd -c "CREATE EXTENSION IF NOT EXISTS postgis_raster;"

raster2pgsql \
    -Y \           # use COPY instead of INSERT statements
    -c \           # creates new table and populates it
    -C \           # constraints to the raster
    -I \           # Index the table
    -M \           # run VACUUM ANALYZE
    -t 250x250 \   # set tile size WIDTH x HEIGHT
    /data/pop/GHS_POP_E2015_GLOBE_R2019A_54009_250_V1_0.tif \ # File to reference
    wpop \
    # public.wpop \  # table name to use
    | psql -h postgres -U yasd