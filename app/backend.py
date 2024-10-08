import logging
import os

import geopandas as gpd
import pandas as pd

DATA_FOLDER = os.path.join("data", "cleaned")


def load_data_sources(folder=DATA_FOLDER):
    """
    Load all the data sources in the given folder.
    """
    data_sources = {}
    for file in os.listdir(folder):
        print(f"Loading data ({file})...")
        file_path = os.path.join(folder, file)
        file_name, file_ext = os.path.splitext(file)

        if file_ext == ".csv":
            data_sources[file_name] = pd.read_csv(file_path)
        elif file_ext == ".geojson":
            data_sources[file_name] = gpd.read_file(file_path)
        elif file_ext == ".json":
            json_readers = [
                lambda: pd.read_json(file_path),
                lambda: pd.read_json(file_path, lines=True),
            ]
            for reader in json_readers:
                try:
                    data_sources[file_name] = reader()
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"File type not supported: {file}")
        else:
            raise ValueError(f"File type not supported: {file}")
    return data_sources


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


def get_filtered_data(data, filters):
    """
    Apply filters to the data.
    """
    filtered_data = {}
    for dataset_name, filters in filters.items():
        dataset = data[dataset_name]
        logging.debug(f"Applying filters to {dataset_name}: {filters}")

        for filter_name, filter_value in filters.items():
            filtered_data[dataset_name] = dataset[dataset[filter_name] == filter_value]

    return filtered_data
