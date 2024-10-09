import logging

import backend
import frontend
import streamlit as st
from streamlit_folium import st_folium

logging.basicConfig(level=logging.INFO)

st.set_page_config(layout="wide")


def get_data():
    return backend.get_data_collection("data/cleaned")


def initialise_session():
    get_data()
    st.session_state.filters = {}
    st.session_state.filtered_data = None
    st.session_state.is_filter_used = False
    st.session_state.is_initialised = True


def get_map():
    """Normal map with no filters applied, only plots rail stations."""
    map_obj = frontend.get_base_map()

    logging.info("Adding rail layer with unfiltered data.")
    map_obj = frontend.add_rail_layer(map_obj, get_data()["RailStationsMerged"])

    return map_obj


def get_map_with_filtered_data():
    if not st.session_state.filtered_data:
        logging.warning("Filtered data not found. Loading unfiltered data.")
        return get_map()

    map_obj = frontend.get_base_map()
    data = st.session_state.filtered_data
    filters = st.session_state.filters

    if "RailStationsMerged" in filters:
        logging.debug("Adding rail layer with filtered data.")
        map_obj = frontend.add_rail_layer(map_obj, data["RailStationsMerged"])

    if "BusRoutes" in filters:
        logging.debug("Adding bus layer with filtered data.")

        bus_routes = data["BusRoutes"]
        bus_route_stops = backend.left_join_datasets(
            bus_routes,
            get_data()["BusStops"],
            "BusStopCode",
            "BUS_STOP_N",
        )

        map_obj = frontend.add_bus_layer(map_obj, bus_route_stops)

    return map_obj


def show_map():
    if st.session_state.is_filter_used:
        logging.info("Reloading map with filtered data...")
        map_obj = get_map_with_filtered_data()
    else:
        logging.info("Reloading map with unfiltered data...")
        map_obj = get_map()
    st_folium(map_obj, width=1200, height=600)


def show_controls():
    rail_lines = ["Not selected"] + backend.get_rail_lines(
        get_data()["RailStationsMerged"]
    )
    chosen_rail_line = st.selectbox(
        "Station Line",
        rail_lines,
        index=0,
        on_change=update_filters,
        args=("RailStationsMerged", "StationLine"),
        key="RailStationsMerged_StationLine_selectbox",
    )

    bus_routes = ["Not selected"] + backend.get_bus_routes(get_data()["BusRoutes"])
    chosen_bus_route = st.selectbox(
        "Bus Route",
        bus_routes,
        index=0,
        on_change=update_filters,
        args=("BusRoutes", "ServiceNo"),
        key="BusRoutes_ServiceNo_selectbox",
    )


def update_filters(dataset, filter_name):
    filter_value = st.session_state[f"{dataset}_{filter_name}_selectbox"]
    if dataset not in st.session_state.filters:
        st.session_state.filters[dataset] = {}

    if filter_value == "Not selected":
        if filter_name in st.session_state.filters[dataset]:
            del st.session_state.filters[dataset][filter_name]
    else:
        st.session_state.filters[dataset][filter_name] = filter_value

    if not st.session_state.filters[dataset]:
        del st.session_state.filters[dataset]

    # Check if all filters are "Not selected"
    all_not_selected = all(
        value == "Not selected"
        for dataset_filters in st.session_state.filters.values()
        for value in dataset_filters.values()
    )

    if all_not_selected:
        st.session_state.is_filter_used = False
        st.session_state.filtered_data = None
        st.session_state.filters = {}
    else:
        st.session_state.is_filter_used = True
        st.session_state.filtered_data = backend.filter_data(
            get_data(), st.session_state.filters
        )
    logging.info(f"Filters: {st.session_state.filters}")


st.title("Visualise")

if "is_initialised" not in st.session_state:
    logging.info("Initialising session state.")
    initialise_session()
    st.session_state.is_initialised = True


show_controls()
show_map()
