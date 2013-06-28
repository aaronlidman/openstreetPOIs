import resource
import cProfile
import pstats

import multiprocessing
import os
import shutil
import sys
import time
import argparse
import plyvel
import ujson as json
from imposm.parser import OSMParser
from shapely.geometry import Polygon, Point, mapping
import shapely.speedups


def prep_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'source',
        help='Source file to parse (.pbf, .osm.bz2, or .osm)')
    parser.add_argument(
        '-o',
        '--out',
        help='Destination filename to create (no extension, .geojson gets added on) (default: output)',
        default='output')
    parser.add_argument(
        '--overwrite',
        help='Overwrite any conflicting files.',
        action='store_true')

    return parser

args = vars(prep_args().parse_args())
args['out'] = args['out'] + '.geojson'
print args


def file_prep(db_only=False):
    if not db_only:
        if os.path.isfile(args['out']):
            if args['overwrite']:
                os.remove(args['out'])
            else:
                print 'overwrite conflict with file: ' + args['out']
                print 'remove/rename ' + args['out']
                + ', name a different output file with --out, or add the --overwrite option'
                sys.exit()

    if os.path.isdir('coords.ldb'):
        shutil.rmtree('coords.ldb')
    if os.path.isdir('ways.ldb'):
        shutil.rmtree('ways.ldb')


class Ways():
    count = 0
    refs = set()

    def __init__(self, db):
        self.db = db.write_batch()

    def way(self, ways):
        for id, tags, refs in ways:
            # circular ways only
            if len(tags) and refs[0] == refs[-1]:
                id = str(id)
                tags['OSM_ID'] = 'way/' + id
                self.db.put(id, json.dumps([refs, tags]))
                self.refs.update(refs)
                self.count = self.count + 1

        if self.count > 200000:
            self.batch_write()

    def batch_write(self):
        self.db.write()
        self.count = 0


class Nodes():
    batch = []

    def __init__(self, file):
        self.file = file

    def node(self, nodes):
        for id, tags, coords in nodes:
            if len(tags):
                lat, lon = coords
                lat = "%.5f" % lat
                lon = "%.5f" % lon
                tags['OSM_ID'] = 'node/' + str(id)

                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [float(lat), float(lon)]},
                    'properties': tags
                }

                self.batch.append(json.dumps(feature) + '\n,\n')

        if len(self.batch) > 10000:
            self.batch_write()

    def batch_write(self):
        self.file.write(''.join(self.batch))
        self.batch = []


class Coords():
    count = 0
    needed = set()

    def __init__(self, db):
        self.db = db.write_batch()

    def coord(self, coords):
        for id, lat, lon in coords:
            if id in self.needed:
                lat = "%.5f" % lat
                lon = "%.5f" % lon
                self.db.put(str(id), str(lat) + ',' + str(lon))
                self.count = self.count + 1

        if self.count > 3000000:
            # ~30MB per million in mem
            self.batch_write()

    def batch_write(self):
        self.db.write()
        self.count = 0


def tag_filter(tags):
    for key in tags.keys():
        if key not in wantedKeys:
            del tags[key]
        else:
            if key in dropTags and tags[key] in dropTags[key]:
                del tags[key]
            elif '*' in dropTags and tags[key] in dropTags['*']:
                del tags[key]

            # we could go nuts here, properly format things, combine common values, etc...

    # remove lonely key
    if len(tags) == 1 and tags.keys()[0] in lonelyKeys:
        del tags[tags.keys()[0]]


def process(output):
    process.writeDone = False

    queue = multiprocessing.Queue()
    pool = multiprocessing.Pool(None, include_queue, [queue], 100000)
    go = pool.map_async(build_POIs, waysDB.iterator(), callback=all_done)

    # let the processes get started and queues fill up a bit
    time.sleep(1)

    while True:
        print 'round and'
        if write(output, queue):
            break

    go.wait()
    pool.close()
    pool.join()


def include_queue(queue):
    build_POIs.queue = queue


def all_done(necessary_arg):
    process.writeDone = True


def build_POIs((id, string)):
    queue = build_POIs.queue

    # try/except because errors tend to disappear in multiprocessing
    try:
        refs, tags = json.loads(string)
        polygon = build_polygon(refs)

        if polygon.is_valid:
            tags['POI_AREA'] = polygon.area
            centroid = polygon.centroid

            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [float(centroid.x), float(centroid.y)]},
                'properties': tags
            }

            queue.put_nowait(json.dumps(feature) + '\n,\n')
        else:
            print 'false'

    except Exception as e:
        print e


def build_polygon(refs):
    coords = []

    for ref in refs:
        coord = coordsDB.get(str(ref))
        if coord:
            coord = map(float, coord.split(','))
            coords.append(coord)

    if coords[0] == coords[-1]:
        return Polygon(coords)
    else:
        return False


def write(file, queue):
    # no .qsize on OS X means we use sleep(), lame
    toFile = ''

    while True:
        try:
            toFile += queue.get_nowait()
        except:
            file.write(toFile)
            break

    if process.writeDone:
        return True
    else:
        time.sleep(5)


if __name__ == '__main__':
    prW = cProfile.Profile()
    prW.enable()
    shapely.speedups.enable()

    # in order of prevalence, http://taginfo.openstreetmap.org/keys
    # I went through the first 25 pages (500 keys)
    wantedKeys = frozenset((
        'building', 'name', 'addr:housenumber', 'addr:street', 'addr:city',
        'addr:postcode', 'addr:state', 'natural', 'landuse', 'amenity', 'railway',
        'leisure', 'shop', 'man_made', 'sport', 'religion', 'wheelchair', 'parking',
        'alt_name', 'public_transport', 'website', 'wikipedia', 'water', 'historic',
        'denomination', 'url', 'phone', 'cuisine', 'aeroway', 'opening_hours',
        'bus', 'emergency', 'information', 'site', 'bench', 'wetland', 'toll',
        'atm', 'golf', 'brand', 'aerialway'
    ))


    # keys from wantedKeys that are useless by themselves, they need some context
    # basically if that was the only tag, there would no useful way to render it
    lonelyKeys = frozenset((
        'building', 'name', 'addr:street', 'addr:city', 'addr:postcode', 'addr:state',
        'natural', 'landuse', 'wheelchair', 'alt_name', 'website', 'water', 'url',
        'phone', 'opening_hours', 'wetland', 'brand'
    ))

    # tag values that aren't really worth bothering over, mostly because they're very common
    # maybe I should be making a whilelist rather than this blacklist?
        # only include tags with values x, y, z with a few exceptions like 'name' key
    dropTags = {
        '*': {'no'},
        'aeroway': {'taxiway'},
        'railway': {'rail', 'abandoned', 'disused', 'switch', 'level_crossing',
        'buffer_stop'},
        'man_made': {'pipeline'},
        'amenity': {'parking'}
    }

    file_prep()
    waysDB = plyvel.DB('ways.ldb', create_if_missing=True, error_if_exists=True)
    coordsDB = plyvel.DB('coords.ldb', create_if_missing=True, error_if_exists=True)

    output = open(args['out'], 'a')
    output.write('{"type": "FeatureCollection", "features": [\n')

    ways = Ways(waysDB)
    nodes = Nodes(output)
    coords = Coords(coordsDB)

    p = OSMParser(
        ways_callback=ways.way,
        ways_tag_filter=tag_filter,
        nodes_callback=nodes.node,
        nodes_tag_filter=tag_filter)
    print 'parsing ways and passing through nodes'
    p.parse(args['source'])

    ways.batch_write()
    nodes.batch_write()
    coords.needed = ways.refs

    p = OSMParser(coords_callback=coords.coord)
    print 'parsing coordinates'
    p.parse(args['source'])

    coords.batch_write()
    del p, ways, nodes

    print 'processing...'
    process(output)
    file_prep(True)
    output.write(']}')

    prW.disable()
    print round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 9.53674e-7, 2)

    ps = pstats.Stats(prW)
    ps.sort_stats('time')
    a = ps.print_stats(30)