import os

from hydra import compose, initialize

from app.frontend.streamlit import streamlit_app

BACKEND_URL = os.getenv(
    "BACKEND_API_URL", "http://backend:8000/dates_coords_selection/"
)

if __name__ == "__main__":
    with initialize(version_base=None, config_path="./"):
        config = compose(config_name="config.yaml")

    streamlit_app(
        config=config,
        submit_url=BACKEND_URL,
    )
