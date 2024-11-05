import folium
from folium.plugins import MarkerCluster
import geopandas as gpd
import pandas as pd
import frontend
import altair as alt


def get_base_map():
    """Map centred in Singapore."""
    return folium.Map(location=[1.3521, 103.8198], zoom_start=12)


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
    if row["geometry"] is None:
        print(f"Warning: No geometry found for row: {row}")
        return None

    if row["geometry"].geom_type == "Point":
        location = [row["geometry"].y, row["geometry"].x]
    elif row["geometry"].geom_type == "Polygon":
        location = [row["geometry"].centroid.y, row["geometry"].centroid.x]
    else:
        location = None
    return location


"""For MRT-BUS visualisation"""


def create_base_map():
    """Create a base Folium map centered at Singapore."""
    singapore_center = [1.3521, 103.8198]  # Coordinates for Singapore
    return folium.Map(location=singapore_center, zoom_start=12)


def get_rail_line_color(stn_code):
    """
    Map stations to line colours for plotting.
    Currently does not support stations that are served by multiple lines.
    """
    if pd.isna(stn_code):  # Handle NaN cases
        return "#808080"  # Default color for missing station code
    if "NS" in stn_code:
        return "#CC0000"  # red
    elif "EW" in stn_code or "CG" in stn_code:
        return "#008000"  # green
    elif "NE" in stn_code:
        return "#800080"  # purple
    elif "CC" in stn_code or "CE" in stn_code:
        return "#FFA500"  # orange
    elif "DT" in stn_code:
        return "#0000FF"  # blue
    elif "TE" in stn_code:
        return "#A52A2A"  # brown
    elif stn_code.startswith("J"):
        return "#40E0D0"  # turquoise
    elif "CR" in stn_code or "CP" in stn_code:
        return "#00FF00"  # light green
    else:
        return "#808080"  # Default color if the line is not recognized


def get_rail_line_color_by_line_name(line_name):
    if line_name == "North-South":
        return "#CC0000"  # red
    elif line_name == "East-West":
        return "#008000"  # green
    elif line_name == "Cross Island":
        return "#00FF00"
    elif line_name == "North-East":
        return "#800080"  # purple
    elif line_name == "Circle":
        return "#FFA500"  # orange
    elif line_name == "Downtown":
        return "#0000FF"  # blue
    elif line_name == "Thomson East Coast":
        return "#A52A2A"  # brown
    elif line_name == "Jurong Region":
        return "#40E0D0"
    else:
        return "#808080"  # gray
