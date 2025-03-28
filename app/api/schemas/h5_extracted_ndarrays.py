from collections import namedtuple

H5ExtractedNdarrays = namedtuple(
    "H5ExtractedNdarrays", "latitude longitude observable", defaults=[None, None, None]
)
