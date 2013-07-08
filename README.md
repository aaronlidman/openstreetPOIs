Extracts and builds points of interest from OpenStreetMap data. It extracts nodes with tags but also builds areas (buildings, lakes, parks, etc..) and uses the centroid as the point for that feature. The aim is to have a scalable way of parsing any osm file for points, quickly and without the need of setting up a database like PostGIS.

settings.py contains a list of all the features to be extracted. It's made up of a sensible default of what I consider useful features but it is also easily edittable to your liking. example-dc.geojson is an example of the default output from a 55mb .osm file of an area of Washington DC.

###Installation
1. `git clone https://github.com/aaronlidman/openstreetPOIs.git && cd openstreetPOIs`
2. Mac or Ubuntu? (homebrew or apt required)
	- Mac
		- `brew update`
		- `brew install python geos leveldb protobuf`
	- Ubuntu
		- 12.10 minimum required, plyvel has a problem with 12.04. [details](https://github.com/wbolster/plyvel/commit/16880a9d2143d53662d0d57ca2b3c7dcc6d6334f)
		- `apt-get update`
		- `apt-get -y install python-dev python-pip build-essential libprotobuf-dev protobuf-compiler libleveldb-dev libgeos-dev`
3. Optional. Setup your python virtualenv.
4. `pip install --requirement requirements.txt`

### Dependencies
- [LevelDB](https://code.google.com/p/leveldb/)
- [Imposm Parser](http://imposm.org/docs/imposm.parser/latest/)
- [Shapely](http://toblerity.github.io/shapely/)
- [UltraJSON](https://github.com/esnme/ultrajson)
- [Plyvel](https://github.com/wbolster/plyvel)

### Usage
Get your desired OSM data ([good starting point](http://wiki.openstreetmap.org/wiki/Planet.osm#Downloading)) in .pbf, .osm.bz2 or just .osm. With all the dependencies installed and python setup, run: `python osmpois.py YOUR_OSM_FILE.EXT` and add options (below).

### Options
- `-h, --help` - show the help message and exit
- `-o OUT, --out OUT` - Destination filename to create (no extension, .extension gets added on) (default: output)
- `--overwrite` - Overwrite any conflicting files.
- `--require-name` - Only output items that have the 'name' tag defined.
- `--group-size` - How large of a group to use for coordinate lookup. (default: 20) A balance between RAM and disk usage to use for coordinate lookups. lower = more RAM, higher = more disk.

### BSD License
