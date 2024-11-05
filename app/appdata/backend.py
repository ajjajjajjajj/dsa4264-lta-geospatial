import json
import logging
import os
import ast
import geopandas as gpd
import pandas as pd
import streamlit as st

DATA_FOLDER = os.path.join("data", "cleaned")
DTYPE_FOLDER = os.path.join("data", "cleaned", "dtypes")
DATA_FNAMES = [
    "RailStationsMerged.geojson",
    "BusRoutes.json",
    "BusStops.geojson",
    "RailLineStrings.geojson",
    "aggregated_ridership.csv",
    "ridership_percentiles.csv",
    "bus_route_trips_single_direction.csv",
]


@st.cache_data
def get_data_collection(folder=DATA_FOLDER):
    """
    Load all the data sources in the given folder.
    """
    data_collection = {}

    for file in DATA_FNAMES:
        if "dtypes" in file:
            continue

        print(f"Loading data ({file})...")
        file_path = os.path.join(folder, file)
        file_name, file_ext = os.path.splitext(file)

        dtype_file_path = os.path.join(DTYPE_FOLDER, f"{file_name}.json")
        dtypes = None
        if os.path.exists(dtype_file_path):
            with open(dtype_file_path, "r") as f:
                dtypes = json.load(f)

        if file_ext == ".csv":
            if dtypes:
                data_collection[file_name] = pd.read_csv(file_path, dtype=dtypes)
            else:
                data_collection[file_name] = pd.read_csv(file_path)
        elif file_ext == ".geojson":
            data_collection[file_name] = gpd.read_file(file_path)

            if file == "RailLineStrings.geojson":
                data_collection[file_name] = data_collection[file_name].to_crs(3857)
                data_collection[file_name]["StationNames"] = data_collection[file_name][
                    "StationNames"
                ].apply(ast.literal_eval)
                data_collection[file_name]["StationCodes"] = data_collection[file_name][
                    "StationCodes"
                ].apply(ast.literal_eval)
                data_collection[file_name].set_geometry("geometry", inplace=True)

        elif file_ext == ".json":
            json_readers = [
                lambda: pd.read_json(file_path),
                lambda: pd.read_json(file_path, lines=True),
            ]
            for reader in json_readers:
                try:
                    if dtypes:
                        data_collection[file_name] = reader().astype(dtypes)
                    else:
                        data_collection[file_name] = reader()
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"File type not supported: {file}")
        else:
            raise ValueError(f"File type not supported: {file}")
    return data_collection


@st.cache_data
def get_unique_values(_data: pd.DataFrame, column_name: str) -> list:
    """
    Get the unique values from the given column in the data.
    """
    return _data[column_name].sort_values().unique().tolist()


def left_join_datasets(
    left: pd.DataFrame,
    right: pd.DataFrame,
    left_on: str,
    right_on: str,
) -> pd.DataFrame:
    """
    Join two datasets on the given columns.
    """
    return left.merge(right, left_on=left_on, right_on=right_on)


def filter_single_dataset(
    _dataset: pd.DataFrame, filter_name: str, _filter_value
) -> pd.DataFrame:
    """
    Apply a single filter to a dataset.
    """
    print(f"Applying filter: {filter_name} == {_filter_value}")
    if isinstance(_filter_value, list):
        return _dataset[_dataset[filter_name].isin(_filter_value)]
    else:
        return _dataset[_dataset[filter_name] == _filter_value]


@st.cache_data
def filter_data(_data_collection: dict, filters: dict) -> dict:
    """
    Filter the data based on the given filters.
    """
    filtered_data = {}
    for dataset_name, dataset in _data_collection.items():
        print(f"Filtering {dataset_name}...")
        for filter_name, filter_value in filters.get(dataset_name, {}).items():
            dataset = filter_single_dataset(dataset, filter_name, filter_value)
        filtered_data[dataset_name] = dataset
    return filtered_data


def load_data(rail_stations, bus_stops):

    # Reproject both GeoDataFrames to the projected CRS for distance calculations
    rail_stations_projected = rail_stations.to_crs(3857)
    bus_stops_projected = bus_stops.to_crs(3857)

    return rail_stations_projected, bus_stops_projected, rail_stations, bus_stops


@st.cache_data
def find_bus_stops_within_radius(
    station_name, radius_meters, _rail_stations_gdf, _bus_stops_gdf
):
    """
    Find bus stops within the specified radius (in meters) from a given MRT station and return distances.
    """
    # Get the geometry for the given station
    station = _rail_stations_gdf[
        _rail_stations_gdf["StationName"].str.lower() == station_name.lower()
    ]

    if station.empty:
        return f"Station '{station_name}' not found.", None

    station_geom = station.geometry.iloc[0]

    # Compute the distance from the station to all bus stops (in meters)
    distances = _bus_stops_gdf.distance(station_geom)

    # Filter bus stops within the specified radius
    nearby_bus_stops = _bus_stops_gdf[distances <= radius_meters].copy()

    # Add the distance to the resulting bus stops DataFrame
    nearby_bus_stops["Distance (m)"] = distances[distances <= radius_meters]

    return None, nearby_bus_stops
