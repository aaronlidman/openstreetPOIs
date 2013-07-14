- RAM option
	- option to set larger write buffers
	- write buffer for leveldb and final output.geojson

- fiona for output
	- geojson first
	- csv second
	- shapefiles eventually

- area units option
	- how to convert degree units area?
	- mi, km, ft, meters

- limit area option (need units)

- progress indicator
	- count ways on input
	- count as their written
		- any way to count the queue? len(queue)?

- limit to bbox or polygon
	- geojson?
	- osmosis polygon?
		- http://wiki.openstreetmap.org/wiki/Osmosis/Polygon_Filter_File_Format

- key order of significance

- merge keys
	- least common identifier/ single category
	- maki + ? icons
		- fallback to osm default set for missing? mono tho
		- noun project?

- normalize fields
	- phone numbers
	- wikipedia
	- open hours, lost cause?

- dedupe
	- possibly, way in the future
	- output list of dupes to be fixed on OSM