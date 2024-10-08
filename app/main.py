import logging

import backend
import frontend
import streamlit as st
from streamlit_folium import st_folium

logging.basicConfig(level=logging.INFO)

st.set_page_config(layout="wide")


def initialise_session():
    st.session_state.data = backend.load_data_sources()
    st.session_state.filters = {}
    st.session_state.filtered_data = None


def get_map():
    logging.info("Reloading map...")
    map_obj = frontend.get_base_map()

    if "RailStationsMerged" in st.session_state.filtered_data:
        logging.debug("Adding rail layer with filtered data.")
        map_obj = frontend.add_rail_layer(
            map_obj, st.session_state.filtered_data["RailStationsMerged"]
        )
    else:
        logging.debug("Adding rail layer with unfiltered data.")
        map_obj = frontend.add_rail_layer(
            map_obj, st.session_state.data["RailStationsMerged"]
        )

    # if "BusRoutes" in st.session_state.filtered_data:
    #     logging.debug("Adding bus layer with filtered data.")
    #     map_obj = frontend.add_bus_layer(
    #         map_obj, st.session_state.filtered_data["BusRoutes"]
    #     )

    return map_obj


def show_map():
    map_obj = get_map()
    st_folium(map_obj, width=1200, height=600)


def show_controls():
    rail_lines = backend.get_rail_lines(st.session_state.data["RailStationsMerged"])
    chosen_rail_line = st.selectbox("Station Line", rail_lines)
    add_filter("RailStationsMerged", "StationLine", chosen_rail_line)

    bus_routes = backend.get_bus_routes(st.session_state.data["BusRoutes"])
    chosen_bus_route = st.selectbox("Bus Route", bus_routes)
    add_filter("BusRoutes", "ServiceNo", chosen_bus_route)


def add_filter(dataset, filter_name, filter_value):
    if "filters" not in st.session_state:
        logging.warning(
            f"Filters should've been initialised at this point."
            f"Initialising filters now."
        )
        st.session_state.filters = {}

    logging.info(f"Adding filter: {dataset}, {filter_name}, {filter_value}")

    if not filter_value:
        if filter_name in st.session_state.filters:
            del st.session_state.filters[dataset][filter_name]

    if dataset not in st.session_state.filters:
        st.session_state.filters[dataset] = {}

    st.session_state.filters[dataset][filter_name] = filter_value
    return


def apply_filters():
    data = st.session_state.data
    filters = st.session_state.filters

    if not filters:
        print("No filters applied.")
        return

    print(f"Applying filters: {filters}")
    filtered = backend.get_filtered_data(data, filters)
    st.session_state.filtered_data = filtered


st.title("Visualise")

if "is_initialised" not in st.session_state:
    initialise_session()
    st.session_state.is_initialised = True


show_controls()
apply_filters()
show_map()
