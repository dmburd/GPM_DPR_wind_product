import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
from bokeh.models import ColumnDataSource, LabelSet, Range1d
from bokeh.plotting import figure
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon

from app.api.schemas.dates_coords_selection import DatesCoordsSelection


def get_land_polygons():
    """Extract land polygons from Natural Earth features"""
    land_geoms = cfeature.NaturalEarthFeature("physical", "land", "50m")
    polygons = []

    for geom in land_geoms.geometries():
        if isinstance(geom, Polygon):
            polygons.append(geom)
        elif isinstance(geom, MultiPolygon):
            polygons.extend(geom.geoms)

    return polygons


def get_polygon_source(polygons, projection):
    """Convert polygons to Bokeh ColumnDataSource"""
    xs, ys = [], []

    for polygon in polygons:
        # Extract exterior coordinates
        x, y = polygon.exterior.xy
        # Project coordinates if needed
        if projection:
            x, y = projection.transform_points(
                ccrs.PlateCarree(), np.array(x), np.array(y)
            )[:, :2].T
        xs.append(x.tolist())
        ys.append(y.tolist())

    return ColumnDataSource(data=dict(xs=xs, ys=ys))


def prepare_bokeh_map(
    plot_title: str,
    selection: DatesCoordsSelection,
) -> figure:
    # Extract bounding box coordinates
    lon_min, lon_max = selection.longitude_min, selection.longitude_max
    lat_min, lat_max = selection.latitude_min, selection.latitude_max

    try:
        height_to_width_ratio = (lat_max - lat_min) / (lon_max - lon_min)
    except ZeroDivisionError:
        height_to_width_ratio = 1.0

    max_size_any = 600
    if height_to_width_ratio > 1.0:
        fig_height = max_size_any
        fig_width = int(fig_height / height_to_width_ratio)
    else:
        fig_width = max_size_any
        fig_height = int(fig_width * height_to_width_ratio)

    # Create Bokeh figure
    p = figure(
        title=plot_title,
        x_range=Range1d(lon_min, lon_max, bounds=(lon_min, lon_max)),
        y_range=Range1d(lat_min, lat_max, bounds=(lat_min, lat_max)),
        width=fig_width,
        height=fig_height,
        tools="pan,wheel_zoom,box_zoom,reset,save",
        toolbar_location="left",
    )

    # Configure plot appearance
    p.title.text_font_size = "16pt"

    # Add coastlines (50m resolution)
    coast_geoms = cfeature.NaturalEarthFeature("physical", "coastline", "50m")
    coastline_source = get_geojson_source(coast_geoms)
    p.multi_line(
        xs="xs", ys="ys", source=coastline_source, line_color="black", line_width=1
    )

    land_polygons = get_land_polygons()
    land_source = get_polygon_source(land_polygons, projection=None)
    p.patches(
        xs="xs",
        ys="ys",
        source=land_source,
        fill_color="#E0E0E0",  # Light gray
        fill_alpha=0.75,  # Slightly transparent
        line_color="black",  # Outline color
        line_width=0.5,  # Outline thickness
    )

    return p


def get_geojson_source(feature):
    """Convert cartopy feature to Bokeh ColumnDataSource"""
    geoms = list(feature.geometries())
    xs, ys = [], []

    for geom in geoms:
        if geom.is_empty:
            continue

        # Handle different geometry types
        if isinstance(geom, LineString):
            x, y = geom.xy
            xs.append(x.tolist())
            ys.append(y.tolist())
        elif isinstance(geom, MultiLineString):
            for line in geom.geoms:
                x, y = line.xy
                xs.append(x.tolist())
                ys.append(y.tolist())

    return ColumnDataSource(data=dict(xs=xs, ys=ys))


def add_geo_grid(p, lon_min, lon_max, lat_min, lat_max):
    """Add geographic gridlines and labels"""
    # Generate grid positions
    lon_ticks = np.linspace(lon_min, lon_max, 5)
    lat_ticks = np.linspace(lat_min, lat_max, 5)

    # Gridline style
    grid_opts = {"color": "#666666", "alpha": 0.4, "line_width": 1}

    # Add longitude lines
    for lon in lon_ticks:
        p.line([lon, lon], [lat_min, lat_max], **grid_opts)

    # Add latitude lines
    for lat in lat_ticks:
        p.line([lon_min, lon_max], [lat, lat], **grid_opts)

    # Configure labels
    label_opts = {
        "text_font_size": "12pt",
        "text_baseline": "top",
        "text_align": "center",
    }

    # Format labels like Cartopy's formatters
    def lon_formatter(lon):
        return f"{abs(lon):.1f}°{'W' if lon < 0 else 'E'}"

    def lat_formatter(lat):
        return f"{abs(lat):.1f}°{'S' if lat < 0 else 'N'}"

    # Longitude labels (bottom)
    lon_labels = ColumnDataSource(
        data={
            "x": lon_ticks,
            "y": [lat_min] * len(lon_ticks),
            "text": [lon_formatter(lon) for lon in lon_ticks],
        }
    )
    p.add_layout(LabelSet(x="x", y="y", text="text", source=lon_labels, **label_opts))

    # Latitude labels (left)
    lat_labels = ColumnDataSource(
        data={
            "x": [lon_min] * len(lat_ticks),
            "y": lat_ticks,
            "text": [lat_formatter(lat) for lat in lat_ticks],
        }
    )
    p.add_layout(LabelSet(x="x", y="y", text="text", source=lat_labels, **label_opts))
