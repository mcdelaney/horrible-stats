# Krasondar LL: 45.0335° N, 39.1393° E
# Krymsk LL:    44.9599° N, 37.9918° E
# https://leafletjs.com/
# https://pypi.org/project/folium/

# mapbox_token = "pk.eyJ1IjoibW9uZ29vc2U1NTYiLCJhIjoiY2thOW1iazRxMG85cTM2cXc4enNpZWFyMCJ9.JwDXWU1JSjO5iPAiVfmrgA"
# 
# MAPBOX_ACCESS_TOKEN = mapbox_token python -m pytest --doctest-glob='*.md' docs/*.md
 

# get position and types of enemy Air Defence units
# place on map
# tooltip with unit type
# click for coords
# threat and detection circles
# refresh every x seconds
# create map centered on krymsk
#import pydcs # provides lists of DCS ASSETS?
import folium
from pathlib import Path
import os
from logging import log
from horrible.config import get_logger
from fastapi import File, UploadFile

log = get_logger('statreader')

map_centre = ["44.9599", "37.9918"]
map_zoom = 8

#async def create_file(file: bytes = File(...)):
#    return {"file_size": len(file)}
#
#async def create_upload_file(file: UploadFile = File(...)):
#    return {"filename": file.filename}

def get_all_values(nested_dictionary):
    """ Recursive function to loop through nested dict """
    for key, value in nested_dictionary.items():
        if type(value) is dict:
            get_all_values(value)
        else:
            print(key, ":", value)

#def map_overview(coordinates, zoom):
async def create_map():
    """ Display a map of area """

    log.info('Creating map...')

    m = folium.Map(map_centre, tiles="Stamen Terrain", zoom_start = map_zoom) # folium map object
    folium.Marker(location=map_centre, popup="Krymsk", tooltip=map_centre).add_to(m) # add marker
    
    local_path = Path('horrible').joinpath('/maps')
    local_path.parent.mkdir(exist_ok=True, parents=True) # create a directory on the app server
    log.info(f"Created folder: {local_path}") # should make a "maps" folder

    m.save(local_path + "map.html") # create file

async def SAM_locations():
    pass


def create_markers(map_object): # TO DO make so it accepts JSON or data? or a separate funcs

    m = map_object
    # Airports
    # Import from DCS or CSV

    # centre coords
    map_centre = [45.0463, 38.8000] #Yelizavetinskaya lat long

    # "key: value" is item?

    # Airports
    # TO DO Import from DCS, TacView, CSV or JSON

    airports = {
        "Krymsk" : {
            "position" : [44.9599, 37.9918],
            "side" : "blue"
            },
            "Krasnodar" : {
            "position" : [45.0335, 39.1393],
            "side" : "red"
            },
            "Anapa" : {
            "position" : [45.0030, 37.3408],
            "side" : "blue"
            },
            "Gelendzhik" : {
            "position": [44.5938, 38.0251],
            "side": "red"
        }
    }

    for keys in airports:

    # "key(reference): value(data)" is item
    # data["London"]["latitude"]

    #    "Krymsk" : {
    #        "position" : [44.9599, 37.9918],
    #        "side" : "red"
    #        },

        tooltip = keys

        #get names
        names = keys
        #get position
        lat_long = airports[keys]["position"]
        #get colour
        side = airports[keys]["side"]

        print(keys)
        print(lat_long)
        print(side)

        folium.Marker(lat_long,
        popup=f'<i>{names}</i>', 
        tooltip=tooltip, 
        icon=folium.Icon(color=side, icon='plane')).add_to(m)

    return m # return map object