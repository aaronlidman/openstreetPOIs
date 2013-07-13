# the keys and values you want to keep
# '*' is a wildcard, will accept anything
# in order of prevalence, http://taginfo.openstreetmap.org/keys
    # at my own (huh, is this interesting?) discretion
wantedTags = {
    'highway': {
        'bus_stop', 'rest_area'},
    'name': '*',
    'addr:housenumber': '*',
    'addr:street': '*',
    'addr:city': '*',
    'addr:postcode': '*',
    'addr:state': '*',
    'natural': {
        'water', 'wetland', 'peak',
        'beach', 'spring', 'bay',
        'land', 'glacier', 'cave_entrance',
        'reef', 'volcano', 'stone',
        'waterfall'},
    'landuse': {
        'forest', 'residential', 'meadow',
        'farm', 'reservior', 'orchard',
        'cemetery', 'vineyard', 'allotments',
        'quarry', 'basin', 'retail',
        'village_green', 'recreation_ground', 'conservation',
        'military', 'landfill'},
    'amenity': '*',
    'place': {
        'island', 'islet'},
    'barrier': {
        'toll_booth'},
    'railway': {
        'station', 'platform', 'tram_stop',
        'subway', 'halt', 'subway_entrance',
        'stop'},
    'leisure': {
        'pitch', 'park', 'swimming_pool',
        'playground', 'garden', 'sports_centre',
        'nature_reserve', 'track', 'common',
        'stadium', 'recreation_ground', 'golf_course',
        'slipway', 'marina', 'water_park',
        'miniature_golf', 'horse_riding', 'fishing',
        'dog_park', 'ice_rink', 'sauna',
        'fitness_station', 'bird_hide', 'beach_resort'},
    'shop': '*',
    'man_made': {
        'pier', 'mine', 'lighthouse'},
    'tourism': '*',
    'sport': '*',
    'religion': '*',
    'wheelchair': {'yes'},
    'parking': {
        'multi-storey', 'park_and_ride'},
    'alt_name': '*',
    'public_transport': '*',
    'website': '*',
    'wikipedia': '*',
    'water': '*',
    'historic': '*',
    'denomination': '*',
    'url': '*',
    'phone': '*',
    'cuisine': '*',
    'aeroway': {
        'aerodrome', 'gate', 'helipad', 'terminal'},
    'opening_hours': '*',
    'emergency': {
        'yes', 'phone'},
    'information': {
        'guidepost', 'board', 'map', 'office'},
    'site': {
        'stop_area'},
    'atm': {
        'yes'},
    'golf': {
        'tee', 'hole', 'driving_range'},
    'brand': '*',
    'aerialway': {
        'station', 'chair_lift'}
}
