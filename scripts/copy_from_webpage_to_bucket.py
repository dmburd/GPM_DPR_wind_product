import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from google.cloud import storage
from hydra import compose, initialize
from tqdm import tqdm

from app.utils.track_file_names import get_all_links_to_hdf5


def copy_from_webpage_to_bucket():
    with initialize(version_base=None, config_path="../"):
        config = compose(config_name="config.yaml")

    h5_urls = get_all_links_to_hdf5(
        config.url_webpage_all_tracks,
        use_gcs_bucket=False,
        hdf_fname_extension=config.hdf_fname_extension,
    )

    storage_client = storage.Client()
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    bucket = storage_client.bucket(bucket_name)

    Path(config.hdf_caching.dir).mkdir(parents=True, exist_ok=True)

    num_h5_urls = len(h5_urls)
    for i in tqdm(range(num_h5_urls)):
        h5_url = h5_urls[i]
        fname = h5_url.split("/")[-1]

        blob = bucket.blob(fname)
        if blob.exists():
            print(f"File {fname} already exists in {bucket_name}. Skipping upload.")
            continue

        fpath = Path(config.hdf_caching.dir) / fname
        response = requests.get(h5_url)
        if response.status_code == 200:
            with open(fpath, "wb") as fd:
                fd.write(response.content)

        blob.upload_from_filename(fpath.as_posix())

        os.unlink(fpath)


if __name__ == "__main__":
    load_dotenv()
    copy_from_webpage_to_bucket()
