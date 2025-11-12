import base64
import io
from collections import deque

import matplotlib.pyplot as plt
import numpy as np
from fastapi import APIRouter, Depends, Request
from omegaconf import DictConfig

from app.api.schemas.dates_coords_selection import DatesCoordsSelection
from app.utils.map_drawing_matplotlib import draw_points, prepare_map
from app.utils.track_file_contents import extract_segment_from_h5_file
from app.utils.track_file_names import (
    download_missing_h5_files,
    extract_start_timestamp_from_h5_url,
    extract_track_number_from_h5_url_or_fpath,
    select_h5_urls_by_coords,
    select_h5_urls_by_date,
)

dates_coords_selection_router = APIRouter(
    prefix="/dates_coords_selection", tags=["dates_coords_selection"]
)


async def get_config(request: Request) -> dict:
    return request.app.state.config


async def get_fname_to_downsampled_points(request: Request) -> dict:
    return request.app.state.fname_to_downsampled_points


async def get_start_timestamps_to_h5_urls(request: Request) -> dict:
    return request.app.state.start_timestamps_to_h5_urls


async def get_cached_h5_fpaths(request: Request) -> deque:
    return request.app.state.cached_h5_fpaths


@dates_coords_selection_router.get("/")
async def get_dates_coords_selection(
    selection: DatesCoordsSelection,
    config: DictConfig = Depends(get_config),
    fname_to_downsampled_points=Depends(get_fname_to_downsampled_points),
    start_timestamps_to_h5_urls: dict = Depends(get_start_timestamps_to_h5_urls),
    cached_h5_fpaths: deque = Depends(get_cached_h5_fpaths),
):
    h5_urls_selected_by_date = select_h5_urls_by_date(
        selection.date_start,
        selection.date_end,
        start_timestamps_to_h5_urls,
    )
    h5_urls_selected_by_coords = select_h5_urls_by_coords(
        h5_urls_selected_by_date,
        selection,
        fname_to_downsampled_points,
    )
    h5_fpaths = download_missing_h5_files(
        h5_urls_selected_by_coords, config, cached_h5_fpaths
    )

    track_number_to_image = {}
    track_number_to_start_timestamp = {}
    track_number_to_h5_data = {}

    for h5_fpath in h5_fpaths:
        h5_data = extract_segment_from_h5_file(h5_fpath, selection, config)

        if (h5_data.latitude is not None) and (h5_data.latitude.size > 0):
            track_number = extract_track_number_from_h5_url_or_fpath(h5_fpath, config)
            start_timestamp = extract_start_timestamp_from_h5_url(h5_fpath, config)
            track_number_to_start_timestamp[track_number] = start_timestamp

            with io.BytesIO() as buffer:
                np.savez(
                    buffer,
                    latitude=h5_data.latitude,
                    longitude=h5_data.longitude,
                    observable=h5_data.observable,
                )
                h5_data_npz_base64 = base64.b64encode(buffer.getvalue()).decode()

            track_number_to_h5_data[track_number] = h5_data_npz_base64

            fig, ax = prepare_map(f"Track number {track_number}", selection)
            draw_points(fig, ax, h5_data.latitude, h5_data.longitude)

            with io.BytesIO() as buffer:
                plt.savefig(buffer, format="jpg")
                image_base64 = base64.b64encode(buffer.getvalue()).decode()

            plt.close()
            track_number_to_image[track_number] = image_base64

    if config.hdf_caching.remove_cached_files:
        for h5_fpath in h5_fpaths:
            h5_fpath.unlink()
            cached_h5_fpaths.pop()

    return {
        "track_number_to_h5_data": track_number_to_h5_data,
        "track_number_to_start_timestamp": track_number_to_start_timestamp,
        "h5_urls_selected_by_date": h5_urls_selected_by_date,
        "h5_urls_selected_by_coords": h5_urls_selected_by_coords,
    }
