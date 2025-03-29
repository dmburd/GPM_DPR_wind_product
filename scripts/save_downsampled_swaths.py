import os
from datetime import date
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google.cloud import storage
from hydra import compose, initialize
from tqdm import tqdm

from app.api.schemas.dates_coords_selection import DatesCoordsSelection
from app.utils.track_file_contents import downsample_swath_points
from app.utils.track_file_names import get_all_links_to_hdf5


def save_downsampled_swaths():
    with initialize(version_base=None, config_path="../"):
        config = compose(config_name="config.yaml")

    h5_urls = get_all_links_to_hdf5(
        config.url_webpage_all_tracks,
        use_gcs_bucket=True,
        hdf_fname_extension=config.hdf_fname_extension,
    )

    storage_client = storage.Client()
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    bucket = storage_client.bucket(bucket_name)

    Path(config.hdf_caching.dir).mkdir(parents=True, exist_ok=True)

    selection = DatesCoordsSelection(
        date_start=date(year=2018, month=3, day=2),
        date_end=date(year=2018, month=3, day=2),
        latitude_min=-90.0,
        latitude_max=+90.0,
        longitude_min=-180.0,
        longitude_max=+180.0,
    )

    num_h5_urls = len(h5_urls)

    fname_to_downsampled_points = {}

    for i in tqdm(range(num_h5_urls)):
        h5_url = h5_urls[i]
        fname = h5_url.split("/")[-1]

        blob = bucket.blob(fname)
        assert blob.exists()

        fpath = Path(config.hdf_caching.dir) / fname
        blob.download_to_filename(fpath.as_posix())

        downsampled_swath_bounds = downsample_swath_points(fpath, selection)

        fname_to_downsampled_points[fname] = (
            downsampled_swath_bounds.latitude,
            downsampled_swath_bounds.longitude,
        )

        os.unlink(fpath)

    np.savez(
        "fname_to_downsampled_points.npz",
        **fname_to_downsampled_points,
    )


if __name__ == "__main__":
    load_dotenv()
    save_downsampled_swaths()
