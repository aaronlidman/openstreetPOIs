# just the keys we want
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
# ex. a building without a name or address or anything, pretty much useless to most
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