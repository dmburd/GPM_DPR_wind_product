import base64
import io
from typing import Any

import numpy as np
import requests
import streamlit as st
from bokeh.events import MouseMove
from bokeh.models import ColorBar, ColumnDataSource, HoverTool, LinearColorMapper
from bokeh.models.callbacks import CustomJS
from bokeh.palettes import Turbo256
from bokeh.transform import transform
from omegaconf import DictConfig

from app.api.schemas.dates_coords_selection import DatesCoordsSelection
from app.utils.map_drawing_bokeh import prepare_bokeh_map


def fill_in_form(schema_fields: dict) -> dict:
    form_data = {}

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        form_data["date_start"] = st.text_input(
            schema_fields["date_start"]["description"]
        )
    with row1_col2:
        form_data["date_end"] = st.text_input(schema_fields["date_end"]["description"])

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        form_data["latitude_min"] = st.number_input(
            schema_fields["latitude_min"]["description"]
        )
    with row2_col2:
        form_data["latitude_max"] = st.number_input(
            schema_fields["latitude_max"]["description"]
        )

    row3_col1, row3_col2 = st.columns(2)
    with row3_col1:
        form_data["longitude_min"] = st.number_input(
            schema_fields["longitude_min"]["description"]
        )
    with row3_col2:
        form_data["longitude_max"] = st.number_input(
            schema_fields["longitude_max"]["description"]
        )

    return form_data


def visualize_single_track(
    form_data: dict[str, str],
    track_number: str,
    track_number_to_start_timestamp: dict[str, str],
    track_number_to_h5_data: dict[str, str],
    config: DictConfig,
    vis_settings: dict[str, Any],
):
    start_timestamp = track_number_to_start_timestamp[track_number].replace("T", " ")
    p = prepare_bokeh_map(
        f"Track number {track_number}\nTrack started {start_timestamp}",
        DatesCoordsSelection(**form_data),
    )

    h5_data_npz_base64 = track_number_to_h5_data[track_number]
    h5_data_npz_bytes = base64.b64decode(h5_data_npz_base64)
    npz_contents = np.load(io.BytesIO(h5_data_npz_bytes))
    observable = npz_contents["observable"].flatten()

    source = ColumnDataSource(
        data=dict(
            latitude=npz_contents["latitude"].flatten(),
            longitude=npz_contents["longitude"].flatten(),
            observable=observable,
            marker_sizes=np.full_like(observable, 3),
        )
    )

    draw_points_colorbar(
        p,
        source,
        observable,
        config,
        vis_settings,
    )


def visualize_multiple_tracks(
    form_data: dict[str, str],
    track_number_to_h5_data: dict[str, str],
    config: DictConfig,
    vis_settings: dict[str, Any],
):
    p = prepare_bokeh_map(
        "All tracks",
        DatesCoordsSelection(**form_data),
    )

    observable_arrs = []
    latitude_arrs = []
    longitude_arrs = []

    for h5_data_npz_base64 in track_number_to_h5_data.values():
        h5_data_npz_bytes = base64.b64decode(h5_data_npz_base64)
        npz_contents = np.load(io.BytesIO(h5_data_npz_bytes))
        observable_arrs.append(npz_contents["observable"].flatten())
        latitude_arrs.append(npz_contents["latitude"].flatten())
        longitude_arrs.append(npz_contents["longitude"].flatten())

    observable = np.concatenate(observable_arrs)
    latitude = np.concatenate(latitude_arrs)
    longitude = np.concatenate(longitude_arrs)

    source = ColumnDataSource(
        data=dict(
            latitude=latitude,
            longitude=longitude,
            observable=observable,
            marker_sizes=np.full_like(observable, 3),
        )
    )

    draw_points_colorbar(
        p,
        source,
        observable,
        config,
        vis_settings,
    )


def draw_points_colorbar_hover_experiments(
    config: DictConfig,
    p: Any,
    source: ColumnDataSource,
    observable: np.ndarray,
):
    color_mapper = LinearColorMapper(
        palette=Turbo256,
        low=min(observable),
        high=max(observable),
    )

    p.scatter(
        "longitude",
        "latitude",
        source=source,
        marker="circle",
        size=3,
        fill_color=transform("observable", color_mapper),
        fill_alpha=0.5,
        line_color=None,
    )

    hover_source = ColumnDataSource(data=dict(x=[0], y=[0]))

    tooltips = [("(lat, lon)", "(@y{0.000}, @x{0.000})"), ("U10", "@observable{0.00}")]
    hover = HoverTool(
        tooltips=tooltips,
        mode="mouse",
        point_policy="snap_to_data",
        renderers=[p.renderers[1]],
    )
    p.add_tools(hover)

    # Custom JavaScript callback for finding the nearest point
    custom_js_code = """
        // Get the current mouse position in data coordinates
        const x_mouse = cb_obj.x;
        const y_mouse = cb_obj.y;

        // Get the data points from the source
        const data = source.data;
        const x_data = data['longitude'];
        const y_data = data['latitude'];

        // Initialize variables to track the closest point
        let min_dist = Infinity;
        let closest_x = 0;
        let closest_y = 0;

        // Compute the distance from the mouse to each data point
        for (let i = 0; i < x_data.length; i++) {
            const dx = x_data[i] - x_mouse;
            const dy = y_data[i] - y_mouse;
            const dist = Math.sqrt(dx * dx + dy * dy);  // Euclidean distance

            if (dist < min_dist) {
                min_dist = dist;
                closest_x = x_data[i];
                closest_y = y_data[i];
            }
        }

        // Update the hover_source with the closest point's coordinates
        hover_source.data = { x: [closest_x], y: [closest_y] };
        hover_source.change.emit();
    """

    # Attach the callback to the HoverTool
    callback = CustomJS(
        args=dict(source=source, hover_source=hover_source),
        code=custom_js_code,
    )
    p.js_on_event(MouseMove, callback)

    color_bar = ColorBar(
        color_mapper=color_mapper,
        label_standoff=12,
        width=8,
        location=(0, 0),
        title="U10, m/s",
        title_text_font_size="16pt",
        title_text_font_style="normal",
        major_label_text_font_size="14pt",
    )
    p.add_layout(color_bar, "right")

    st.bokeh_chart(
        p,
        use_container_width=False,
    )


def draw_points_colorbar_marker_sizes(
    config: DictConfig,
    p: Any,
    source: ColumnDataSource,
    observable: np.ndarray,
):
    color_mapper = LinearColorMapper(
        palette=Turbo256,
        low=min(observable),
        high=max(observable),
    )

    p.scatter(
        "longitude",
        "latitude",
        source=source,
        marker="circle",
        fill_color=transform("observable", color_mapper),
        fill_alpha=0.5,
        line_color=None,
    )

    # Custom JavaScript callback for finding the nearest point
    custom_js_code = """
        // Get the current range of the plot
        const x_start = x_range.start;
        const x_end = x_range.end;
        const y_start = y_range.start;
        const y_end = y_range.end;

        // Compute the width and height of the current view in data units
        const x_range_width = x_end - x_start;
        const y_range_height = y_end - y_start;

        // Use the smaller of the two dimensions to ensure uniform scaling
        const range_scale = Math.min(x_range_width, y_range_height);

        // Base size (adjust this to control the overall marker size)
        const base_size = 10;

        // Scale factor: marker size is inversely proportional to the range
        // (smaller range = zoomed in = larger markers; larger range = zoomed out = smaller markers)
        const scale_factor = 100 / range_scale;  // Adjust the 100 to control sensitivity

        // Compute new marker sizes
        const data = source.data;
        const sizes = data['sizes'];
        for (let i = 0; i < sizes.length; i++) {
            sizes[i] = base_size * scale_factor;
        }

        // Update the data source and trigger a change event
        source.change.emit();
    """

    # Attach the callback to the HoverTool
    callback = CustomJS(
        args=dict(source=source, x_range=p.x_range, y_range=p.y_range),
        code=custom_js_code,
    )
    p.x_range.js_on_change("start", callback)  # Trigger on x-range changes
    p.x_range.js_on_change("end", callback)
    p.y_range.js_on_change("start", callback)  # Trigger on y-range changes
    p.y_range.js_on_change("end", callback)

    color_bar = ColorBar(
        color_mapper=color_mapper,
        label_standoff=12,
        width=8,
        location=(0, 0),
        title="U10, m/s",
        title_text_font_size="16pt",
        title_text_font_style="normal",
        major_label_text_font_size="14pt",
    )
    p.add_layout(color_bar, "right")

    st.bokeh_chart(
        p,
        use_container_width=False,
    )


def draw_points_colorbar(
    p: Any,
    source: ColumnDataSource,
    observable: np.ndarray,
    config: DictConfig,
    vis_settings: dict[str, Any],
):
    color_mapper = LinearColorMapper(
        palette=Turbo256,
        low=min(observable),
        high=max(observable),
    )

    p.scatter(
        "longitude",
        "latitude",
        source=source,
        marker="circle",
        size=3,
        fill_color=transform("observable", color_mapper),
        fill_alpha=0.5,
        line_color=None,
    )

    if vis_settings["add_hover_tool"]:
        tooltips = [
            ("(lat, lon)", "(@latitude{0.000}, @longitude{0.000})"),
            ("U10", "@observable{0.00}"),
        ]
        hover = HoverTool(tooltips=tooltips)
        p.add_tools(hover)

    color_bar = ColorBar(
        color_mapper=color_mapper,
        label_standoff=12,
        width=8,
        location=(0, 0),
        title="U10, m/s",
        title_text_font_size="16pt",
        title_text_font_style="normal",
        major_label_text_font_size="14pt",
    )
    p.add_layout(color_bar, "right")

    st.bokeh_chart(
        p,
        use_container_width=False,
    )


def get_response_and_visualize(
    config: DictConfig,
    submit_url: str,
    form_data: dict,
    vis_settings: dict[str, Any],
) -> None:
    response = requests.get(
        submit_url,
        json=form_data,
    )
    if response.status_code == 200:
        st.success("Data submitted successfully!")

        track_number_to_h5_data = response.json()["track_number_to_h5_data"]
        track_number_to_start_timestamp = response.json()[
            "track_number_to_start_timestamp"
        ]

        track_numbers = sorted(track_number_to_h5_data)
        selected_track_numbers_text = f"**Selected track numbers**: {track_numbers}"
        st.write(f"**There are {len(track_numbers)} selected tracks**.")
        st.write(selected_track_numbers_text)

        if vis_settings["separate_plots"]:
            for track_number in track_numbers:
                visualize_single_track(
                    form_data,
                    track_number,
                    track_number_to_start_timestamp,
                    track_number_to_h5_data,
                    config,
                    vis_settings,
                )
        else:
            visualize_multiple_tracks(
                form_data,
                track_number_to_h5_data,
                config,
                vis_settings,
            )
    else:
        message_part1 = "Error submitting data to backend"
        try:
            message_part2 = ": " + response.json()["detail"][0]["msg"]
        except (KeyError, IndexError):
            message_part2 = ""

        st.error(message_part1 + message_part2)


def streamlit_app(
    config: DictConfig,
    submit_url: str,
):
    st.title("Extracting and visualizing selected track segments")

    with st.form(key="pydantic_form"):
        schema_fields = DatesCoordsSelection.model_json_schema()["properties"]
        form_data = fill_in_form(schema_fields)

        vis_settings = {}
        vis_settings["separate_plots"] = st.checkbox(
            "Visualize each track separately",
            value=False,
        )
        vis_settings["add_hover_tool"] = st.checkbox(
            "Add hover tool (usable only for a narrow range of zoom level, but can be turned off)",
            value=False,
        )

        submit_button = st.form_submit_button(label="Submit")

        if submit_button:
            get_response_and_visualize(
                config,
                submit_url,
                form_data,
                vis_settings,
            )
