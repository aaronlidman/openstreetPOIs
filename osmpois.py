import cProfile
import pstats

import multiprocessing as mp
from os import path, remove
from shutil import rmtree
from sys import exit
from time import time, sleep
import argparse
import plyvel
import ujson as json
from imposm.parser import OSMParser
from shapely.geometry import Polygon
import shapely.speedups
from settings import wantedTags


def prep_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'source',
        help='Source file to parse (.pbf, .osm.bz2, or .osm)')
    parser.add_argument(
        '--output',
        help='Destination filename to create (no extension, .geojson gets added on) (default: output)',
        default='output')
    parser.add_argument(
        '--overwrite',
        help='Overwrite any conflicting files.',
        action='store_true')
    parser.add_argument(
        '--require-key',
        help='Only output items that have a defined key. '
        'ex. --require-key name, only outputs items that have a name',
        type=str,
        default=False)
    parser.add_argument(
        '--profile',
        action='store_true')
    parser.add_argument(
        '--groupsize',
        help='How large of a group to use for coordinate lookup. (default: 20) '
        'lower = more RAM, higher = more disk',
        type=int,
        default=20)
    parser.add_argument(
        '--precache',
        help='Precache all coordinates. Removes the coordinate lookup process which uses lots of RAM.',
        action='store_true'),
    parser.add_argument(
        '--max-nodes',
        help='Maximum number of nodes in a way to consider for simplification. '
        'Anything over max is skipped. (default: 250)',
        type=int,
        default=250)
    return parser

args = vars(prep_args().parse_args())
args['output'] = args['output'] + '.geojson'

if args['profile']:
    print args


def file_prep(db_only=False):
    if not db_only:
        if path.isfile(args['output']):
            if args['overwrite']:
                remove(args['output'])
            else:
                print 'overwrite conflict with file: ' + args['output']
                print ('remove or rename ' + args['output'] +
                       ', name a different output file with --output, or add the --overwrite option')
                exit()

    if path.isdir('coords.ldb'):
        rmtree('coords.ldb')
    if path.isdir('ways.ldb'):
        rmtree('ways.ldb')


class Ways():
    groups = set()

    def __init__(self, db):
        self.db = db

    def way(self, ways):
        for id, tags, refs in ways:
            if len(tags) and args['max_nodes'] > len(refs) > 1 and refs[0] == refs[-1]:
                # circular ways only
                id = str(id)
                tags['OSM_ID'] = 'way/' + id
                self.db.put(id, json.dumps([refs, tags]))

                if not args['precache']:
                    self.put_refs(refs)

    def put_refs(self, refs):
        for ref in refs:
            self.groups.add(round_down(ref, args['groupsize']))


class Nodes():
    batch = []
    first = True

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

                self.batch.append(json.dumps(feature))

        if len(self.batch) > 10000:
            self.batch_write()

    def batch_write(self):
        if self.first:
            self.file.write(',\n'.join(self.batch))
            self.first = False
        else:
            self.file.write(',\n' + ',\n'.join(self.batch))

        self.batch = []


class Coords():
    def __init__(self, db, needed):
        self.db = db
        self.needed = needed

    def coord(self, coords):
        for id, lat, lon in coords:
            if round_down(id, args['groupsize']) in self.needed:
                self.db.put(str(id), str(lat) + ',' + str(lon))

    def coord_precache(self, coords):
        for id, lat, lon in coords:
            self.db.put(str(id), str(lat) + ',' + str(lon))


def tag_filter(tags):
    if args['require_key'] and args['require_key'] not in tags:
        for key in tags.keys():
            del tags[key]
            # "functions should modify the dictionary in-place"
    else:
        for key in tags.keys():
            if key not in wantedTags:
                del tags[key]
            else:
                if wantedTags[key] == '*' or tags[key] in wantedTags[key]:
                    a = 1
                    # placeholder, more to do here, combine keys, normalize values, etc...
                else:
                    del tags[key]


def round_down(num, divisor):
    if divisor == 0:
        divisor = 1

    if divisor == 1:
        return num

    return num - (num % divisor)


def include_queue(queue):
    build_POIs.queue = queue


def process(output):
    process.writeDone = False
    queue = mp.Queue()
    pool = mp.Pool(None, include_queue, [queue], 1000000)
    go = pool.map_async(build_POIs, waysDB.iterator(), callback=all_done)
    sleep(1)  # let the processes start and queues fill up a bit

    while True:
        if write(output, queue):
            break

    go.wait()
    pool.terminate()
    pool.join()


def all_done(necessary_arg):
    process.writeDone = True


def build_POIs((id, string)):
    queue = build_POIs.queue
    refs, tags = json.loads(string)
    polygon = build_polygon(refs)

    if polygon and polygon.is_valid:
        tags['POI_AREA'] = polygon.area * 1000000
            # just for ease of use

        if tags['POI_AREA'] > 0.0:
            centroid = polygon.centroid

            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [
                        float("%.5f" % centroid.x),
                        float("%.5f" % centroid.y)]},
                'properties': tags
            }

            queue.put(json.dumps(feature))
            # return id
            # that id would be a good way to count for a progress indicator


def build_polygon(refs):
    coords = []

    for ref in refs:
        coord = coordsDB.get(str(ref))
        if coord:
            coord = map(float, coord.split(','))
            coords.append(coord)
        else:
            # for some reason coordinates are missing
            # this is usually because an extract cuts coordinates out
            return False

    if len(coords) > 2:
        # 3 point minimum for polygon
        # avoids common osm problems
        polygon = Polygon(coords)

        if polygon.is_valid:
            return polygon
        else:
            # 0.0 buffer cleans invalid polygons
            # they're invalid for many reasons, people prone problems
            return polygon.buffer(0.0)
    else:
        return False


def write(file, queue):
    toFile = []

    while not queue.empty():
        toFile.append(queue.get_nowait())

    if len(toFile):
        file.write(',\n' + ',\n'.join(toFile))
        # improvement: batch this

    if process.writeDone:
        if queue.empty():
            return True
        # else it returns and runs again immediately
        # this is to clear out any last items in the queue
    else:
        sleep(0.05)


if __name__ == '__main__':
    if args['profile']:
        prW = cProfile.Profile()
        prW.enable()

    start = time()
    shapely.speedups.enable()
    file_prep()

    waysDB = plyvel.DB(
        'ways.ldb',
        create_if_missing=True,
        error_if_exists=True,
        write_buffer_size=1048576*1024)

    coordsDB = plyvel.DB(
        'coords.ldb',
        create_if_missing=True,
        error_if_exists=True,
        write_buffer_size=1048576*1024)

    output = open(args['output'], 'a')
    output.write('{"type": "FeatureCollection", "features": [\n')

    ways = Ways(waysDB)
    nodes = Nodes(output)
    coords = Coords(coordsDB, ways.groups)

    if args['precache']:
        p = OSMParser(coords_callback=coords.coord_precache)
        print 'caching all coordinates'
        p.parse(args['source'])
        coords = None
        del coords

    p = OSMParser(
        ways_callback=ways.way,
        ways_tag_filter=tag_filter,
        nodes_callback=nodes.node,
        nodes_tag_filter=tag_filter)
    print 'parsing ways and nodes'
    p.parse(args['source'])

    nodes.batch_write()

    if not args['precache']:
        p = OSMParser(coords_callback=coords.coord)
        print 'parsing coordinates'
        p.parse(args['source'])
        coords = None
        del coords

    del p, ways, nodes

    print 'processing...'
    process(output)
    output.write('\n]}')
    file_prep(True)

    print 'saved as: ' + str(args['output'])
    print 'took ' + str(round(time() - start, 2)) + ' seconds'

    if args['profile']:
        prW.disable()
        ps = pstats.Stats(prW)
        ps.sort_stats('time')
        a = ps.print_stats(30)
