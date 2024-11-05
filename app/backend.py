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


@st.cache_data
def get_hour_count_below_25th_percentile_each_stop(
    _data_collection,
    bus_service: str,
) -> tuple[pd.DataFrame, int]:
    """
    Same function taken from ridership analysis: ridership_final.ipynb
    resultant df has these columns:
    - Destination_StopSequence
    - DAY_TYPE
    - Total_Hour_Count
    """
    print(f"Doing analysis for bus service: {bus_service}")

    bus_routes_trips = _data_collection["bus_route_trips_single_direction"]
    ridership = _data_collection["aggregated_ridership"]
    ridership_percentiles = _data_collection["ridership_percentiles"]

    # filter bus_routes_trips to only include the chosen bus service
    chosen_bus_route_trips = bus_routes_trips[
        bus_routes_trips["ServiceNo"] == bus_service
    ]
    total_num_stops = len(chosen_bus_route_trips["Destination_Stop"].unique())

    # merge chosen_bus_route_trips with ridership to get the estimated tap in and tap out
    chosen_route_ridership = chosen_bus_route_trips.merge(
        ridership,
        on=["Destination_Stop", "PT_TYPE", "TIME_PER_HOUR", "DAY_TYPE"],
        how="left",
    )

    # calculate the estimated tap in and tap out based on estimated number of trips for the bus route
    chosen_route_ridership["Estimated_Tap_In"] = chosen_route_ridership[
        "Adj_Estimated_Trips"
    ] * (
        chosen_route_ridership["TOTAL_TAP_IN_VOLUME"]
        / chosen_route_ridership["TOTAL_TRIPS"]
    )
    chosen_route_ridership["Estimated_Tap_Out"] = chosen_route_ridership[
        "Adj_Estimated_Trips"
    ] * (
        chosen_route_ridership["TOTAL_TAP_OUT_VOLUME"]
        / chosen_route_ridership["TOTAL_TRIPS"]
    )

    # merge chosen_route_ridership with overall ridership_percentiles to get the 25th percentile tap in and tap out
    service_ridership_and_global_ridership = chosen_route_ridership.merge(
        ridership_percentiles, on=["TIME_PER_HOUR", "DAY_TYPE"]
    )

    # filter the bus stops to only include those with estimated tap in and tap out below the 25th percentile
    filtered_busstops = service_ridership_and_global_ridership[
        (
            service_ridership_and_global_ridership["Estimated_Tap_In"]
            < service_ridership_and_global_ridership["TAP_IN_25"]
        )
        & (
            service_ridership_and_global_ridership["Estimated_Tap_Out"]
            < service_ridership_and_global_ridership["TAP_OUT_25"]
        )
        & (service_ridership_and_global_ridership["TIME_PER_HOUR"] > 5)
        & (service_ridership_and_global_ridership["TIME_PER_HOUR"] < 23)
    ]

    # count the number of hours below the 25th percentile for each service stop
    num_hours_below_25th_by_service_stop = (
        filtered_busstops.groupby(["Destination_StopSequence", "DAY_TYPE"])
        .size()
        .reset_index(name="Total_Hour_Count")
    )

    # create full index of all possible combinations of Destination_StopSequence and DAY_TYPE
    # this is because some bus stops may not have any hours below the 25th percentile and won't be included in the previous step
    max_sequence = filtered_busstops["Max_StopSequence"].max()
    day_types = filtered_busstops["DAY_TYPE"].unique()
    full_index = pd.MultiIndex.from_product(
        [range(1, int(max_sequence) + 1), day_types],
        names=["Destination_StopSequence", "DAY_TYPE"],
    )

    # filling missing values with 0
    num_hours_below_25th_by_service_stop = (
        num_hours_below_25th_by_service_stop.set_index(
            ["Destination_StopSequence", "DAY_TYPE"]
        )
        .reindex(full_index, fill_value=0)
        .reset_index()
    )

    num_hours_below_25th_by_service_stop["Destination_StopSequence"] = (
        num_hours_below_25th_by_service_stop["Destination_StopSequence"].astype(int)
    )

    return num_hours_below_25th_by_service_stop, total_num_stops
