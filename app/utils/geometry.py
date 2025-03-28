import numpy as np
from shapely.geometry import Polygon

from app.api.schemas.dates_coords_selection import DatesCoordsSelection


def check_swath_intersects_roi(
    swath_edges_coords: tuple[np.ndarray, np.ndarray],
    selection: DatesCoordsSelection,
) -> bool:
    latitude, longitude = swath_edges_coords

    latitude_min_radians = np.radians(selection.latitude_min)
    latitude_max_radians = np.radians(selection.latitude_max)
    longitude_min_radians = np.radians(selection.longitude_min)
    longitude_max_radians = np.radians(selection.longitude_max)

    polygon_roi = Polygon(
        [
            (latitude_min_radians, longitude_min_radians),
            (latitude_min_radians, longitude_max_radians),
            (latitude_max_radians, longitude_max_radians),
            (latitude_max_radians, longitude_min_radians),
        ]
    )

    # points on the 'left' and 'right' edges of the swath:
    left_points_radians = np.stack(
        [
            np.radians(latitude[:, 0]),
            np.radians(longitude[:, 0]),
        ],
        axis=1,
    )
    right_points_radians = np.stack(
        [
            np.radians(latitude[:, 1]),
            np.radians(longitude[:, 1]),
        ],
        axis=1,
    )

    for left_point_radians in left_points_radians:
        if (
            latitude_min_radians <= left_point_radians[0] <= latitude_max_radians
            and longitude_min_radians <= left_point_radians[1] <= longitude_max_radians
        ):
            return True

    for right_point_radians in right_points_radians:
        if (
            latitude_min_radians <= right_point_radians[0] <= latitude_max_radians
            and longitude_min_radians <= right_point_radians[1] <= longitude_max_radians
        ):
            return True

    num_points_along, _ = left_points_radians.shape

    for idx in range(num_points_along - 1):
        polygon_swath_fragment = Polygon(
            [
                left_points_radians[idx],
                left_points_radians[idx + 1],
                right_points_radians[idx + 1],
                right_points_radians[idx],
            ]
        )
        if polygon_roi.overlaps(polygon_swath_fragment):
            return True

    return False
