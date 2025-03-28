from hydra import compose, initialize

from app.frontend.streamlit import streamlit_app

if __name__ == "__main__":
    with initialize(version_base=None, config_path="./"):
        config = compose(config_name="config.yaml")

    streamlit_app(
        config=config,
        submit_url="http://localhost:8000/dates_coords_selection/",
    )
