openstreetPOIs extracts and builds points of interest from OpenStreetMap data. It extracts nodes with tags but also builds areas (buildings, lakes, parks, etc..) and uses the centroid as the point for that feature. The aim is to have a scalable way of parsing any osm file for points, quickly and without the need of setting up a database like PostGIS.

settings.py contains a list of all the features to be extracted. It's made up of a sensible default of what I consider useful features but it is also easily edittable to your liking. example-dc.geojson is an example of the default output from a 55mb .osm file of an area of Washington DC.

### Usage
Get your desired OSM data ([good starting point]( http://wiki.openstreetmap.org/wiki/Planet.osm#Downloading)) in .pbf, .osm.bz2 or just .osm. With all the dependencies installed and python setup, run: `python osmpois.py YOUR_OSM_FILE.EXT` and add options (below).

### Options
- `-h, --help` - show the help message and exit
- `-o OUT, --out OUT` - Destination filename to create (no extension, .extension gets added on) (default: output)
- `--overwrite` - Overwrite any conflicting files.
- `--require-name` - Only output items that have the 'name' tag defined.
