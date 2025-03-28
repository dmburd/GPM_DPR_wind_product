from pathlib import Path

import h5py
import numpy as np
from omegaconf import DictConfig
from sklearn.metrics.pairwise import haversine_distances

from app.api.schemas.dates_coords_selection import DatesCoordsSelection
from app.api.schemas.h5_extracted_ndarrays import H5ExtractedNdarrays


def print_hdf5_schema(file, indent=0):
    """
    Recursively prints the schema of an HDF5 file.

    Args:
        file: An HDF5 file or group object.
        indent: Indentation level for pretty-printing.
    """
    for key in file.keys():
        item = file[key]
        print(" " * indent + f"Key: {key}")  # Print the key
        if isinstance(item, h5py.Group):
            print(" " * indent + "  Type: Group")
            print_hdf5_schema(item, indent + 4)  # Recurse into the group
        elif isinstance(item, h5py.Dataset):
            print(" " * indent + "  Type: Dataset")
            print(" " * indent + f"  Shape: {item.shape}")
            print(" " * indent + f"  Dtype: {item.dtype}")
            # Print dataset attributes if any
            if item.attrs:
                print(" " * indent + "  Attributes:")
                for attr_name, attr_value in item.attrs.items():
                    print(" " * indent + f"    {attr_name}: {attr_value}")
        print()


def extract_segment_from_h5_file(
    h5_fpath: Path,
    selection: DatesCoordsSelection,
    config: DictConfig,
) -> H5ExtractedNdarrays:
    h5 = h5py.File(h5_fpath, "r")
    # print_hdf5_schema(h5)

    latitude = h5["Latitude"][:]
    longitude = h5["Longitude"][:]
    observable = h5[config.hdf_observable.value_name][:]

    coords_mask_latitude = np.logical_and(
        selection.latitude_min <= latitude,
        latitude <= selection.latitude_max,
    )
    coords_mask_longitude = np.logical_and(
        selection.longitude_min <= longitude,
        longitude <= selection.longitude_max,
    )
    coords_mask = np.logical_and(coords_mask_latitude, coords_mask_longitude)
    idxs_pairs = np.argwhere(coords_mask)
    if idxs_pairs.size == 0:
        return H5ExtractedNdarrays()

    distinct_lengthwise_idxs = set(idxs_pairs[:, 0])
    idx_lengthwise_min = min(distinct_lengthwise_idxs)
    idx_lengthwise_max = max(distinct_lengthwise_idxs)

    filtered_by_coords = H5ExtractedNdarrays(
        latitude=latitude[idx_lengthwise_min : idx_lengthwise_max + 1],
        longitude=longitude[idx_lengthwise_min : idx_lengthwise_max + 1],
        observable=observable[idx_lengthwise_min : idx_lengthwise_max + 1],
    )
    thresholded_observable_mask = filtered_by_coords.observable < min(
        config.hdf_observable.value_invalid,
        config.hdf_observable.upper_threshold,
    )
    valid_filtered = H5ExtractedNdarrays(
        latitude=filtered_by_coords.latitude[thresholded_observable_mask],
        longitude=filtered_by_coords.longitude[thresholded_observable_mask],
        observable=filtered_by_coords.observable[thresholded_observable_mask],
    )
    return valid_filtered


def downsample_swath_points(
    h5_fpath: Path,
    selection: DatesCoordsSelection,
) -> H5ExtractedNdarrays:
    h5 = h5py.File(h5_fpath, "r")
    # print_hdf5_schema(h5)

    latitude = h5["Latitude"][:]
    longitude = h5["Longitude"][:]
    assert latitude.ndim == 2
    num_points_along, num_points_across = latitude.shape

    latitude_radians = np.radians(latitude)
    longitude_radians = np.radians(longitude)
    points_left_bound = np.stack(
        [
            latitude_radians[:, 0],
            longitude_radians[:, 0],
        ],
        axis=1,
    )
    points_right_bound = np.stack(
        [
            latitude_radians[:, -1],
            longitude_radians[:, -1],
        ],
        axis=1,
    )

    haversine_distances_swath_width = haversine_distances(
        [
            points_left_bound[num_points_along // 2],
            points_right_bound[num_points_along // 2],
        ]
    )
    swath_width_radians = haversine_distances_swath_width[0, 1]

    haversine_distances_steps_along = haversine_distances(
        [
            points_left_bound[num_points_along // 2],
            points_left_bound[num_points_along // 2 + 1],
        ]
    )
    step_along_radians = haversine_distances_steps_along[0, 1]

    downsampling_idxs_diff = int(np.ceil(swath_width_radians / step_along_radians))

    downsampled_latitude = np.stack(
        [
            latitude[::downsampling_idxs_diff, 0],
            latitude[::downsampling_idxs_diff, -1],
        ],
        axis=1,
    )
    downsampled_longitude = np.stack(
        [
            longitude[::downsampling_idxs_diff, 0],
            longitude[::downsampling_idxs_diff, -1],
        ],
        axis=1,
    )

    side_indicator = np.ones_like(downsampled_latitude)
    side_indicator[:, 1] = 2.0

    coords_mask_latitude = np.logical_and(
        selection.latitude_min <= downsampled_latitude,
        downsampled_latitude <= selection.latitude_max,
    )
    coords_mask_longitude = np.logical_and(
        selection.longitude_min <= downsampled_longitude,
        downsampled_longitude <= selection.longitude_max,
    )
    coords_mask = np.logical_and(coords_mask_latitude, coords_mask_longitude)
    idxs_pairs = np.argwhere(coords_mask)
    if idxs_pairs.size == 0:
        return H5ExtractedNdarrays()

    distinct_lengthwise_idxs = set(idxs_pairs[:, 0])
    idx_lengthwise_min = min(distinct_lengthwise_idxs)
    idx_lengthwise_max = max(distinct_lengthwise_idxs)

    downsampled_swath_bounds = H5ExtractedNdarrays(
        latitude=downsampled_latitude[idx_lengthwise_min : idx_lengthwise_max + 1],
        longitude=downsampled_longitude[idx_lengthwise_min : idx_lengthwise_max + 1],
        observable=side_indicator[idx_lengthwise_min : idx_lengthwise_max + 1],
    )

    return downsampled_swath_bounds
