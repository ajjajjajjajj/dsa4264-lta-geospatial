import json
import logging
import os

import geopandas as gpd
import pandas as pd
import streamlit as st

DATA_FOLDER = os.path.join("data", "cleaned")
DTYPE_FOLDER = os.path.join("data", "cleaned", "dtypes")


@st.cache_data
def get_data_collection(folder=DATA_FOLDER):
    """
    Load all the data sources in the given folder.
    """
    data_collection = {}

    for file in os.listdir(folder):
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


def get_rail_station_line_color(stn_code):
    """
    Map stations to line colours for plotting.
    Currently does not support stations that are served by multiple lines.
    """
    if pd.isna(stn_code):  # Handle NaN cases
        return "gray"  # Default color for missing station code
    if "NS" in stn_code:
        return "lightred"
    elif "EW" in stn_code or "CG" in stn_code:
        return "green"
    elif "NE" in stn_code:
        return "purple"
    elif "CC" in stn_code or "CE" in stn_code:
        return "orange"
    elif "DT" in stn_code:
        return "blue"
    elif "TE" in stn_code:
        return "darkred"
    else:
        return "gray"  # Default color if the line is not recognized


def get_rail_lines(data: pd.DataFrame) -> list:
    """
    Get the unique rail lines from the rail station data.
    """
    return data["StationLine"].sort_values().unique().tolist()


def get_bus_routes(data: pd.DataFrame) -> list:
    """
    Get the unique bus routes from the bus route data.
    """
    return data["ServiceNo"].sort_values().unique().tolist()


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


@st.cache_data
def filter_single_dataset(
    _dataset: pd.DataFrame, filter_name: str, filter_value
) -> pd.DataFrame:
    """
    Apply a single filter to a dataset.
    """
    logging.debug(f"Applying filter: {filter_name} == {filter_value}")
    return _dataset[_dataset[filter_name] == filter_value]


@st.cache_data
def filter_data(_data_collection: dict, filters: dict) -> dict:
    """
    Filter the data based on the given filters.
    """
    filtered_data = {}
    for dataset_name, dataset in _data_collection.items():
        logging.debug(f"Filtering {dataset_name}...")
        for filter_name, filter_value in filters.get(dataset_name, {}).items():
            dataset = filter_single_dataset(dataset, filter_name, filter_value)
        filtered_data[dataset_name] = dataset
    return filtered_data
