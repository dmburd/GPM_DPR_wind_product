import os
from collections import deque
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import requests
from dotenv import load_dotenv
from hydra import compose, initialize

from app.api.schemas.dates_coords_selection import DatesCoordsSelection
from app.utils.map_drawing_matplotlib import draw_points, prepare_map
from app.utils.track_file_contents import extract_segment_from_h5_file
from app.utils.track_file_names import (
    download_missing_h5_files,
    extract_track_number_from_h5_url_or_fpath,
)


def draw_points_matplotlib():
    print(f"{os.getcwd()}")
    with initialize(version_base=None, config_path="../"):
        config = compose(config_name="config.yaml")

    selected_h5_urls = [
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803020045_0217_022766_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803020217_0350_022767_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803020350_0522_022768_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803020522_0655_022769_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803020655_0828_022770_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803020828_1000_022771_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803021000_1133_022772_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803021133_1305_022773_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803021305_1438_022774_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803021438_1610_022775_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803021610_1743_022776_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803021743_1915_022777_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803021915_2048_022778_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803022048_2221_022779_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803022221_2353_022780_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803022353_0126_022781_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803030126_0258_022782_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803030258_0431_022783_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803030431_0603_022784_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803030603_0736_022785_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803030736_0908_022786_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803030908_1041_022787_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803031041_1213_022788_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803031213_1346_022789_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803031346_1519_022790_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803031519_1651_022791_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803031651_1824_022792_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803031824_1956_022793_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803031956_2129_022794_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803032129_2301_022795_L2S_DD2_06A.h5",
        "https://sat.ipfran.ru/GPM_Ku_mss_U10/mss_U10_NGPMCOR_DPR_1803032301_0034_022796_L2S_DD2_06A.h5",
    ]

    h5_fpaths = download_missing_h5_files(selected_h5_urls, config, deque())

    if False:
        selection = DatesCoordsSelection(
            date_start=date(year=2018, month=3, day=2),
            date_end=date(year=2018, month=3, day=2),
            latitude_min=38.0,
            latitude_max=38.001,
            longitude_min=-36.0,
            longitude_max=-35.999,
        )
    else:
        selection = DatesCoordsSelection(
            date_start=date(year=2018, month=3, day=2),
            date_end=date(year=2018, month=3, day=2),
            latitude_min=30,
            latitude_max=70,
            longitude_min=-20,
            longitude_max=+10,
        )

    for h5_fpath in h5_fpaths:
        h5_data = extract_segment_from_h5_file(h5_fpath, selection, config)
        if (h5_data.latitude is not None) and (h5_data.latitude.size > 0):
            track_number = extract_track_number_from_h5_url_or_fpath(h5_fpath, config)
            fig, ax = prepare_map(f"Track number {track_number}", selection)
            draw_points(fig, ax, h5_data.latitude, h5_data.longitude)
            output_figure_fpath = f"track_number_{track_number}.jpg"
            plt.savefig(output_figure_fpath)
            plt.close()


def load_downsampled_swaths():
    with initialize(version_base=None, config_path="../"):
        config = compose(config_name="config.yaml")

    response = requests.get(config.url_npz_track_to_downsampled_swath_points)
    if response.status_code == 200:
        with open("fname_to_downsampled_points.npz", "wb") as fd:
            fd.write(response.content)

    fname_to_downsampled_points = np.load("fname_to_downsampled_points.npz")

    for fname, (latitude, longitude) in fname_to_downsampled_points.items():
        print(f"{fname=} {latitude.shape=} {longitude.shape=}")


if __name__ == "__main__":
    load_dotenv()
    load_downsampled_swaths()
