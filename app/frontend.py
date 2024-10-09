import folium
import geopandas as gpd
import pandas as pd
from backend import get_rail_station_line_color


def get_base_map():
    """Map centred in Singapore."""
    return folium.Map(location=[1.3521, 103.8198], zoom_start=12)


def add_rail_layer(map_obj, rail_station_data: gpd.GeoDataFrame):
    """
    Add the rail station layer to the map object.
    """
    rail_layer = folium.FeatureGroup(name="Rail Stations")
    for idx, row in rail_station_data.iterrows():
        station_code = row["StationCode"]
        line_color = get_rail_station_line_color(station_code)
        station_type = row["StationType"]
        station_name = row["StationName"]

        # Create a popup message
        popup = create_popup_text(
            StationName=station_name, StationCode=station_code, StationType=station_type
        )

        loc = get_location_from_row(row)
        if loc is None:
            continue

        folium.Marker(
            location=loc,
            popup=popup,
            icon=folium.Icon(color=line_color),
        ).add_to(rail_layer)
    rail_layer.add_to(map_obj)
    return map_obj


def add_bus_layer(map_obj, bus_route_data: pd.DataFrame):
    """
    Add the bus route layer to the map object.
    """
    bus_layer = folium.FeatureGroup(name="Bus Routes")
    for idx, row in bus_route_data.iterrows():
        service_no = row["ServiceNo"]
        direction = row["Direction"]
        bus_stop_code = row["BusStopCode"]

        # Create a popup message
        popup = create_popup_text(
            ServiceNo=service_no,
            Direction=direction,
            BusStopCode=bus_stop_code,
        )

        loc = get_location_from_row(row)
        folium.Marker(
            location=loc,
            popup=popup,
            icon=folium.Icon(color="blue"),
        ).add_to(bus_layer)
    bus_layer.add_to(map_obj)
    return map_obj


def create_popup_text(**kwargs):
    """
    Create a popup message for the rail station markers.
    """
    popup_text = """
    <div style="padding: 10px;">
    <table style="border:1px solid black;">
    """
    for key, value in kwargs.items():
        popup_text += f"<tr><th>{key}</th><td>{value}</td></tr>"

    popup_text += """
    </table>
    </div>
    """
    return popup_text


def get_location_from_row(row):
    """
    Extract the geometry (assuming it's a Point geometry, for polygons, use centroids or bounds)
    """
    if row["geometry"].geom_type == "Point":
        location = [row["geometry"].y, row["geometry"].x]
    elif row["geometry"].geom_type == "Polygon":
        location = [row["geometry"].centroid.y, row["geometry"].centroid.x]
    else:
        location = None
    return location
