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
print args


def leveldb_prep():
    if os.path.isdir('nodes.ldb'):
        shutil.rmtree('nodes.ldb')
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
                self.db.put(str(id), json.dumps([refs, tags]))
                self.refs.update(refs)
                self.count = self.count + 1

        if self.count > 200000:
            self.batch_write()

    def batch_write(self):
        self.db.write()
        self.count = 0


class Nodes():
    count = 0
    needed = set()

    def __init__(self, db):
        self.db = db.write_batch()

    def node(self, nodes):
        for id, tags, coords in nodes:
            if id in self.needed:
                lat, lon = coords
                lat = "%.6f" % lat
                lon = "%.6f" % lon
                self.db.put(str(id), json.dumps([[lat, lon], tags]))
                self.count = self.count + 1

        if self.count > 500000:
            # ~30MB per million in mem
            self.batch_write()

    def batch_write(self):
        self.db.write()
        self.count = 0


class Coords():
    count = 0
    needed = set()

    def __init__(self, db):
        self.db = db.write_batch()

    def coord(self, coords):
        for id, lat, lon in coords:
            # coords
            if id in self.needed:
                lat = "%.6f" % lat
                lon = "%.6f" % lon
                self.db.put(str(id), json.dumps([[lat, lon]]))
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


if __name__ == '__main__':
    prW = cProfile.Profile()
    prW.enable()
    shapely.speedups.enable()

    # in order of prevalence, http://taginfo.openstreetmap.org/keys
    # I went through the first 25 pages (500 keys) and 1 page of name:* keys
        # not sure about those name tags, want 'name' to be enough
    wantedKeys = frozenset((
        'building', 'name', 'addr:housenumber', 'addr:street', 'addr:city',
        'addr:postcode', 'addr:state', 'natural', 'landuse', 'amenity', 'railway',
        'leisure', 'shop', 'man_made', 'name:en', 'sport', 'religion', 'wheelchair',
        'parking', 'alt_name', 'public_transport', 'website', 'wikipedia', 'name:ru',
        'water', 'historic', 'denomination', 'url', 'name:ja', 'phone', 'cuisine',
        'aeroway', 'name:fr', 'opening_hours', 'bus', 'name:de', 'emergency',
        'information', 'site', 'bench', 'wetland', 'toll', 'atm', 'golf', 'brand',
        'aerialway', 'name:ar', 'name:ar1', 'name:uk', 'name:zh', 'name:ko', 'name:be',
        'name:sv', 'name:he', 'name:fi', 'name:sr', 'name:ja_rm', 'name:sr-Latn'
    ))

    # keys from wantedKeys that are useless by themselves, they need some context
    # basically if that was the only tag, there would no useful way to render it
    lonelyKeys = frozenset((
        'building', 'name', 'addr:street', 'addr:city', 'addr:postcode', 'addr:state',
        'natural', 'landuse', 'name:en', 'wheelchair', 'alt_name', 'website', 'name:ru', 'water',
        'url', 'name:ja', 'phone', 'name:fr', 'opening_hours', 'name:de', 'wetland',
        'brand', 'name:ar', 'name:ar1', 'name:uk', 'name:zh', 'name:ko', 'name:be',
        'name:sv', 'name:he', 'name:fi', 'name:sr', 'name:ja_rm', 'name:sr_Latn'
    ))

    # tag values that aren't really worth bothering over, mostly because they're very common
    # maybe I should be making a whilelist rather than this blacklist?
        # only include tags with values x, y, z with a few exceptions like 'name' key
    dropTags = {
        '*': {'no'},
        'railway': {'level_crossing'},
        'aeroway': {'taxiway'},
        'railway': {'rail', 'abandoned', 'disused', 'switch'},
        'man_made': {'pipeline'},
        'amenity': {'parking'}
    }

    leveldb_prep()
    waysDB = plyvel.DB('ways.ldb', create_if_missing=True, error_if_exists=True)
    nodesDB = plyvel.DB('nodes.ldb', create_if_missing=True, error_if_exists=True)
    # nodes and coords are in nodesDB, just with and without tags

    ways = Ways(waysDB)
    nodes = Nodes(nodesDB)
    coords = Coords(nodesDB)

    p = OSMParser(
        ways_callback=ways.way,
        ways_tag_filter=tag_filter,
        nodes_callback=nodes.node,
        nodes_tag_filter=tag_filter)
    print 'parsing ways and nodes'
    p.parse(args['source'])

    ways.batch_write()
    nodes.needed = ways.refs

    p = OSMParser(coords_callback=coords.coord)
    print 'parsing coordinates'
    p.parse(args['source'])

    nodes.batch_write()
    del p, ways, nodes

    print 'processing...'
    leveldb_prep()

    prW.disable()
    print round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 9.53674e-7, 2)

    ps = pstats.Stats(prW)
    ps.sort_stats('time')
    a = ps.print_stats(30)