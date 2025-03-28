import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
from cartopy.mpl.geoaxes import GeoAxes
from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER

from app.api.schemas.dates_coords_selection import DatesCoordsSelection

LAND = cfeature.NaturalEarthFeature(
    "physical", "land", "50m", edgecolor="face", facecolor=cfeature.COLORS["land"]
)


def prepare_map(
    plot_title: str,
    selection: DatesCoordsSelection,
    projection=ccrs.PlateCarree(),
) -> tuple[plt.Figure, GeoAxes]:
    fig, ax = plt.subplots(figsize=(12, 10), subplot_kw=dict(projection=projection))
    bbox = [
        selection.longitude_min,
        selection.longitude_max,
        selection.latitude_min,
        selection.latitude_max,
    ]
    ax.set_title(plot_title)
    ax.set_extent(bbox)
    # ax.add_feature(LAND, facecolor='0.75')
    ax.coastlines(resolution="50m")
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels = False
    gl.right_labels = False
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER

    gl.xlabel_style = {"size": 16}
    gl.ylabel_style = {"size": 16}
    return fig, ax


def draw_points(
    fig: plt.Figure,
    ax: GeoAxes,
    latitude: np.ndarray,
    longitude: np.ndarray,
) -> None:
    ax.scatter(
        longitude.flatten(),
        latitude.flatten(),
        s=7,
        c="r",
    )
