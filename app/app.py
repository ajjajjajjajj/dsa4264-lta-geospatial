import pandas as pd
import folium
import streamlit as st
import frontend
from streamlit_folium import st_folium
import backend
import json
import os
import altair as alt

st.set_page_config(layout="wide")

DATA_COLLECTION = backend.get_data_collection("app/appdata")
CENTER_START = [1.3521, 103.8198]
ZOOM_START = 12


## General functions


def init_session():
    if st.session_state.get("is_initialised"):
        print("Reusing session state")
        return
    print("Initialising session state")
    st.session_state.global_data = DATA_COLLECTION
    st.session_state.filters = {}
    st.session_state.filtered_data = {}
    st.session_state.is_initialised = True
    st.session_state.mrtlines = None


def create_filter_selectbox(dataset, filter_name, label=None):
    print(f"Creating filter selectbox for {dataset} - {filter_name}")
    filter_values = ["Not selected"] + backend.get_unique_values(
        DATA_COLLECTION[dataset], filter_name
    )
    filter_val = st.selectbox(
        label or filter_name,
        filter_values,
        index=0,
        on_change=update_filters,
        args=(dataset, filter_name, "selectbox"),
        key=f"{os.path.basename(__file__)}_{dataset}_{filter_name}_selectbox",
    )
    if dataset not in st.session_state.filters:
        st.session_state.filters[dataset] = {}
    return filter_val


def create_filter_multiselect_list(dataset, filter_name, label=None):
    print(f"Creating filter checkbox list for {dataset} - {filter_name}")
    filter_values = backend.get_unique_values(DATA_COLLECTION[dataset], filter_name)
    filter_val = st.multiselect(
        label or filter_name,
        filter_values,
        default=[],
        on_change=update_filters,
        args=(dataset, filter_name, "multiselect"),
        key=f"{os.path.basename(__file__)}_{dataset}_{filter_name}_multiselect",
    )
    if dataset not in st.session_state.filters:
        st.session_state.filters[dataset] = {}
    return filter_val


def create_filter_selectbox_with_data(data, filter_name, label=None):
    print(f"Creating filter selectbox with custom data - {filter_name}")
    filter_values = ["Not selected"] + backend.get_unique_values(data, filter_name)
    filtered_val = st.selectbox(
        label or filter_name,
        filter_values,
        index=0,
        on_change=update_filters,
        args=(data, filter_name, "selectbox"),
        key=f"{os.path.basename(__file__)}_{data}_{filter_name}_selectbox",
    )
    if data not in st.session_state.filters:
        st.session_state.filters[data] = {}
    return filtered_val


def update_filters(dataset, filter_name, filter_type):

    filter_value = st.session_state[
        f"{os.path.basename(__file__)}_{dataset}_{filter_name}_{filter_type}"
    ]
    previous_value = st.session_state.filters[dataset].get(filter_name)
    print(f"Filter {filter_name} changed from {previous_value} to {filter_value}")

    # Remove filter if not selected
    if filter_value == "Not selected" or filter_value == []:
        if filter_name in st.session_state.filters[dataset]:
            del st.session_state.filters[dataset][filter_name]
    else:
        st.session_state.filters[dataset][filter_name] = filter_value

    print(f"Filters: {json.dumps(st.session_state.filters, indent=2)}")

    # only update filtered data if the filter value has changed
    if (st.session_state.filtered_data.get(dataset) is None) or (
        filter_value != previous_value
    ):
        print("Filter value changed, updating filtered data")
        filter_kv = st.session_state.filters[dataset]

        # this might need fixing if filtering over multiple columns is needed
        for filter_col, filter_value in filter_kv.items():
            # value may be a string or list
            st.session_state.filtered_data[dataset] = backend.filter_single_dataset(
                DATA_COLLECTION[dataset], filter_col, filter_value
            )

    print("Filtered data:" f"{st.session_state.filtered_data[dataset].shape[0]} rows")
    return


## Plot 1: MRT-Bus Visualisation


def init_plot1_vars():
    if st.session_state.get("plot1_initialized"):
        print("Reusing plot1 state")
        return
    st.session_state.plot1_initialized = True
    st.session_state.plot1_bus_markers = {}
    st.session_state.plot1_rail_markers = {}


def plot1_get_bus_markers(service_no: str) -> list[folium.Marker]:

    if service_no in st.session_state.plot1_bus_markers:
        return st.session_state.plot1_bus_markers[service_no]

    if service_no:
        bus_route_data = st.session_state.filtered_data["BusRoutes"]
    else:
        return []
    print(f"Creating markers for bus service {service_no}")
    bus_route_data = backend.left_join_datasets(
        bus_route_data, DATA_COLLECTION["BusStops"], "BusStopCode", "BUS_STOP_N"
    )

    markers = []

    for _, row in bus_route_data.iterrows():
        service_no = row["ServiceNo"]
        direction = row["Direction"]
        bus_stop_code = row["BusStopCode"]

        popup = frontend.create_popup_text(
            ServiceNo=service_no,
            Direction=direction,
            BusStopCode=bus_stop_code,
        )

        loc = frontend.get_location_from_row(row)
        markers.append(
            folium.CircleMarker(
                location=loc,
                radius=6,
                fill_color="gray",
                fill_opacity=0.8,
                color="black",
                weight=1,
                popup=popup,
            )
        )

    st.session_state.plot1_bus_markers[service_no] = markers
    return markers


def plot1_get_rail_polylines() -> list[folium.PolyLine]:

    print(f"Creating rail lines")

    layer = folium.GeoJson(
        DATA_COLLECTION["RailLineStrings"],
        name="geojson",
        style_function=lambda x: {
            "color": frontend.get_rail_line_color_by_line_name(
                x["properties"]["StationLine"]
            ),
            "weight": 4,
            "opacity": 0.8,
            "smoothFactor": 5,
        },
    )

    # st.session_state.mrtlines = layer
    return layer


def plot1_get_rail_layer(all_rail_names: list[str]) -> list[folium.Marker]:

    if not all_rail_names:
        return []

    all_markers = []
    print(f"Creating markers for rail lines {all_rail_names}")
    print(f"Session state: {st.session_state.plot1_rail_markers.keys()}")
    for rail_name in all_rail_names:
        if rail_name in st.session_state.plot1_rail_markers:
            print(f"Reusing markers for rail line {rail_name}")
            all_markers += st.session_state.plot1_rail_markers[rail_name]
            continue

        if rail_name:
            rail_station_data = st.session_state.filtered_data["RailStationsMerged"]
        else:
            return []

        print(f"Creating markers for rail line {rail_name}")
        markers = []

        for _, row in rail_station_data.iterrows():

            line_color = frontend.get_rail_line_color(row["StationCode"])

            popup = frontend.create_popup_text(
                StationCode=row["StationCode"],
                StationName=row["StationName"],
                StationLine=row["StationLine"],
            )
            loc = frontend.get_location_from_row(row)
            if loc is None:
                continue

            markers.append(
                folium.CircleMarker(
                    location=loc,
                    radius=8,
                    fill_color=line_color,
                    fill_opacity=0.8,
                    color="black",
                    weight=2,
                    # popup=popup,
                )
            )

        all_markers += markers
        st.session_state.plot1_rail_markers[rail_name] = markers
    return all_markers


## Plot 2: Bus Stop Low Ridership Count


def plot2_get_bus_stop_hourly_count(service_no: str):
    print(f"Getting bus stop hourly count for service {service_no}")
    if service_no:
        df, total_num_stops = backend.get_hour_count_below_25th_percentile_each_stop(
            DATA_COLLECTION, service_no
        )
    else:
        return (
            pd.DataFrame(
                columns=["Destination_StopSequence", "DAY_TYPE", "Total_Hour_Count"]
            ),
            0,
        )
    print(f"Got hourly count for {total_num_stops} stops")
    return df, total_num_stops


def plot2_get_percent_exceeding(hour_counts, total_num_stops, threshold):

    if total_num_stops == 0:
        return ""

    weekday_data = hour_counts[hour_counts["DAY_TYPE"] == "WEEKDAY"]
    num_hours_low_ridership_weekday = weekday_data.shape[0]
    exceeding_sequences_weekday = weekday_data[
        weekday_data["Total_Hour_Count"] > threshold
    ].shape[0]
    percentage_exceed_weekday = (
        (exceeding_sequences_weekday / total_num_stops) * 100
        if num_hours_low_ridership_weekday
        else 0
    )
    # weekday_out = f"Percentage of stop sequences exceeding {threshold} (weekday): {percentage_exceed_weekday:.2f}%"

    weekend_data = hour_counts[hour_counts["DAY_TYPE"] == "WEEKENDS/HOLIDAY"]
    num_hours_low_ridership_weekend = weekend_data.shape[0]
    exceeding_sequences_weekend = weekend_data[
        weekend_data["Total_Hour_Count"] > threshold
    ].shape[0]
    percentage_exceed_weekend = (
        (exceeding_sequences_weekend / total_num_stops) * 100
        if num_hours_low_ridership_weekend
        else 0
    )
    # weekend_out = f"Percentage of stop sequences exceeding {threshold} (weekend): {percentage_exceed_weekend:.2f}%"

    output = (
        f"% of bus stops with over {threshold} hours of low ridership, out of {total_num_stops} stops:  \n"
        f"{percentage_exceed_weekday:.2f}% (weekday)  \n"
        f"{percentage_exceed_weekend:.2f}% (weekend)  \n"
    )

    return output


# for whole app
init_session()

# first plot
init_plot1_vars()

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        rail_line_filter = create_filter_multiselect_list(
            "RailStationsMerged", "StationLine", label="Station Line"
        )
        bus_route_filter = create_filter_selectbox(
            "BusRoutes", "ServiceNo", label="Bus Route"
        )

        st.markdown("### Number of low-ridership hours for each bus stop")

        plot2_df, total_num_stops = plot2_get_bus_stop_hourly_count(
            st.session_state.filters["BusRoutes"].get("ServiceNo")
        )

        # Create Altair scatter plot
        scatter_plot = (
            alt.Chart(plot2_df)
            .mark_circle(size=60)
            .encode(
                x=alt.X(
                    "Destination_StopSequence", title="Bus Stop Sequence along Route"
                ),
                y=alt.Y("Total_Hour_Count", title="Number of Low Ridership Hours"),
                color="DAY_TYPE",
                tooltip=["Destination_StopSequence", "Total_Hour_Count", "DAY_TYPE"],
            )
            .properties(width=800, height=600)
        )

        # add threshold line if there are stops
        if total_num_stops:
            hline = (
                alt.Chart(pd.DataFrame({"y": [8]})).mark_rule(color="red").encode(y="y")
            )
            scatter_plot = scatter_plot + hline

        st.altair_chart(scatter_plot)

        text_display = plot2_get_percent_exceeding(plot2_df, total_num_stops, 8)

        st.markdown(text_display)

    with col2:
        st.markdown("### Map Overview")
        plot1 = folium.Map(location=CENTER_START, zoom_start=ZOOM_START)

        plot1_rail_polylines = folium.FeatureGroup(name="MRT Lines")
        plot1_get_rail_polylines().add_to(plot1_rail_polylines)

        plot1_bus_layer = folium.FeatureGroup(name="Bus Routes")
        for marker in plot1_get_bus_markers(
            st.session_state.filters["BusRoutes"].get("ServiceNo")
        ):
            marker.add_to(plot1_bus_layer)

        plot1_rail_layer = folium.FeatureGroup(name="Rail Stations")
        for marker in plot1_get_rail_layer(
            st.session_state.filters["RailStationsMerged"].get("StationLine")
        ):
            marker.add_to(plot1_rail_layer)
        st.markdown(
            "<small>LRT and Cross Island Line are excluded. </small>",
            unsafe_allow_html=True,
        )
        plot1_data = st_folium(
            plot1,
            use_container_width=True,
            height=800,
            feature_group_to_add=[
                plot1_rail_polylines,
                plot1_rail_layer,
                plot1_bus_layer,
            ],
        )
