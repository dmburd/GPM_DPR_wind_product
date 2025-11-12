from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from hydra import compose, initialize

from app.api.endpoints.dates_coords_selection import dates_coords_selection_router
from app.utils.track_file_names import (
    get_all_links_to_hdf5,
    map_h5_urls_to_start_timestamps,
    map_start_timestamps_to_h5_urls,
)

load_dotenv()


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # Code to run on startup
    # (1) read the config
    with initialize(version_base=None, config_path="./"):
        config = compose(config_name="config.yaml")

    app.state.config = config

    # (2) get the downsampled swath points for each track:
    fpath = "fname_to_downsampled_points.npz"
    if not Path(fpath).is_file():
        response = requests.get(config.url_npz_track_to_downsampled_swath_points)
        if response.status_code == 200:
            with open(fpath, "wb") as fd:
                fd.write(response.content)

    app.state.fname_to_downsampled_points = np.load(fpath)

    # (3) get the full list of links (or file paths) from the source
    h5_urls = get_all_links_to_hdf5(
        config.url_webpage_all_tracks,
        config.use_gcs_bucket,
        config.hdf_fname_extension,
    )
    # (4) extract the start date for each track
    h5_urls_to_start_timestamps = map_h5_urls_to_start_timestamps(config, h5_urls)

    # (5) get the list of tracks for each start date
    app.state.start_timestamps_to_h5_urls = map_start_timestamps_to_h5_urls(
        h5_urls_to_start_timestamps
    )

    # (6) initialize a queue for the cached hdf5 files
    app.state.cached_h5_fpaths = deque()

    yield
    # Code to run on shutdown (optional)


app = FastAPI(lifespan=app_lifespan)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})


app.include_router(dates_coords_selection_router)
