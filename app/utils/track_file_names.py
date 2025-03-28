import os
from collections import OrderedDict, defaultdict, deque
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import numpy as np
import requests
from bs4 import BeautifulSoup
from google.cloud import storage
from omegaconf import DictConfig
from tqdm import tqdm

from app.api.schemas.dates_coords_selection import DatesCoordsSelection
from app.utils.geometry import check_swath_intersects_roi


def get_all_links_to_hdf5(
    webpage_root_url: str,
    use_gcs_bucket: bool,
    hdf_fname_extension: str,
) -> list[str]:
    response = requests.get(webpage_root_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.find_all("a", href=True)
    all_urls = [urljoin(webpage_root_url, link["href"]) for link in links]
    webpage_h5_urls = [url for url in all_urls if url.endswith(hdf_fname_extension)]

    if use_gcs_bucket:
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        try:
            storage_client = storage.Client()
            bucket = storage_client.get_bucket(
                bucket_name
            )  # Raises NotFound if the bucket doesn't exist.
            blob_fnames = {blob.name for blob in bucket.list_blobs()}
        except Exception:
            blob_fnames = set()

    final_h5_urls = []
    for webpage_h5_url in webpage_h5_urls:
        fname = webpage_h5_url.split("/")[-1]
        if use_gcs_bucket and (fname in blob_fnames):
            final_h5_urls.append(f"gs://{bucket_name}/{fname}")
        else:
            final_h5_urls.append(webpage_h5_url)

    return final_h5_urls


def extract_start_timestamp_from_h5_url(
    h5_url: str,
    config: DictConfig,
) -> datetime:
    if isinstance(h5_url, Path):
        fname = h5_url.name
    else:
        fname = h5_url.split("/")[-1]

    bname = os.path.splitext(fname)[0]
    parts = bname.split(config.hdf_fnames_parsing.delimiter)
    start_timestamp_part = parts[config.hdf_fnames_parsing.start_timestamp_part_idx]
    assert len(start_timestamp_part) == 10
    # ^ yy, mm, dd, hh, mm
    start_timestamp = datetime(
        year=(2000 + int(start_timestamp_part[0:2])),
        month=int(start_timestamp_part[2:4]),
        day=int(start_timestamp_part[4:6]),
        hour=int(start_timestamp_part[6:8]),
        minute=int(start_timestamp_part[8:10]),
        second=0,
    )

    return start_timestamp


def extract_track_number_from_h5_url_or_fpath(
    h5_url_or_fpath: str | Path,
    config: DictConfig,
) -> str:
    if isinstance(h5_url_or_fpath, Path):
        fname = h5_url_or_fpath.name
    else:
        fname = h5_url_or_fpath.split("/")[-1]

    bname = os.path.splitext(fname)[0]
    parts = bname.split(config.hdf_fnames_parsing.delimiter)
    track_number = parts[config.hdf_fnames_parsing.track_number_part_idx]
    return track_number


def map_h5_urls_to_start_timestamps(
    config: DictConfig,
    h5_urls: list[str],
) -> dict[str, str]:
    mapping = OrderedDict()

    for h5_url in h5_urls:
        start_datetime = extract_start_timestamp_from_h5_url(h5_url, config)
        mapping[h5_url] = start_datetime.isoformat()
        # ^ deserialize: parsed_date = date.fromisoformat(mapping[h5_url])

    return mapping


def map_start_timestamps_to_h5_urls(
    h5_urls_to_start_timestamps: dict[str, str],
) -> dict[str, list[str]]:
    mapping = defaultdict(list[str])
    for url, timestamp in h5_urls_to_start_timestamps.items():
        mapping[timestamp].append(url)

    return mapping


def select_h5_urls_by_date(
    date_start: date,
    date_end: date,
    start_timestamps_to_h5_urls: dict[str, list[str]],
) -> list[str]:
    h5_urls_output = []
    for timestamp, h5_urls in start_timestamps_to_h5_urls.items():
        if (
            date_start
            <= datetime.date(datetime.fromisoformat(timestamp))
            <= date_end + timedelta(days=1)
        ):
            h5_urls_output.extend(h5_urls)

    return h5_urls_output


def select_h5_urls_by_coords(
    h5_urls: list[str],
    selection: DatesCoordsSelection,
    fname_to_downsampled_points: dict[str, np.ndarray],
) -> list[str]:
    if len(h5_urls) == 0:
        return []

    input_fpaths_prefix = "/".join(h5_urls[0].split("/")[:-1])
    input_fnames = [h5_url.split("/")[-1] for h5_url in h5_urls]
    output_fnames = [
        fname
        for fname in input_fnames
        if check_swath_intersects_roi(
            fname_to_downsampled_points[fname],
            selection,
        )
    ]

    output_h5_urls = [
        input_fpaths_prefix + "/" + output_fname for output_fname in output_fnames
    ]
    return output_h5_urls


def download_missing_h5_files(
    h5_urls: list[str],
    config: DictConfig,
    cached_h5_fpaths: deque,
) -> list[Path]:
    h5_fpaths = []

    for h5_url in tqdm(h5_urls):
        fname = h5_url.split("/")[-1]
        fpath = Path(config.hdf_caching.dir) / fname

        if not Path.is_file(fpath):
            os.makedirs(config.hdf_caching.dir, exist_ok=True)

            if h5_url.startswith("gs://"):
                try:
                    bucket_name, blob_name = h5_url.replace("gs://", "").split("/", 1)
                    storage_client = storage.Client()
                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(blob_name)
                    blob.download_to_filename(fpath)
                except Exception:
                    pass
                else:
                    cached_h5_fpaths.append(fpath)
            else:
                response = requests.get(h5_url)
                if response.status_code == 200:
                    with open(fpath, "wb") as fd:
                        fd.write(response.content)
                    cached_h5_fpaths.append(fpath)

            if len(cached_h5_fpaths) > config.hdf_caching.max_num_cached_files:
                old_h5_fpath = cached_h5_fpaths.popleft()
                old_h5_fpath.unlink()

        h5_fpaths.append(fpath)

    h5_fpaths = [fpath for fpath in h5_fpaths if Path.is_file(fpath)]

    return h5_fpaths
