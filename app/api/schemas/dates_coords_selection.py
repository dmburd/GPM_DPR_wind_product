from datetime import date, timedelta

from pydantic import BaseModel, Field, model_validator


class DatesCoordsSelection(BaseModel):
    """
    The user request contains the date range,
    the latitude range and the longitude range.
    """

    date_start: date = Field(..., description="Start date (yyyy-mm-dd)")
    date_end: date = Field(..., description="End date (yyyy-mm-dd)")
    latitude_min: float = Field(-90.0, ge=-90.0, description="Minimum latitude")
    latitude_max: float = Field(+90.0, le=+90.0, description="Maximum latitude")
    longitude_min: float = Field(-180.0, ge=-180.0, description="Minimum longitude")
    longitude_max: float = Field(+180.0, le=+180.0, description="Maximum longitude")

    @model_validator(mode="after")
    def check_date_start_end(self) -> "DatesCoordsSelection":
        if self.date_end < self.date_start:
            raise ValueError("date_end must be greater or equal to date_start")
        return self

    @model_validator(mode="after")
    def check_date_range(self) -> "DatesCoordsSelection":
        if (self.date_end - self.date_start) > timedelta(days=31):
            raise ValueError("date_end must be within 31 days of date_start")
        return self

    @model_validator(mode="after")
    def check_latitude_min_max(self) -> "DatesCoordsSelection":
        if self.latitude_max < self.latitude_min:
            raise ValueError("latitude_max must be greater or equal to latitude_min")
        return self

    @model_validator(mode="after")
    def check_longitude_min_max(self) -> "DatesCoordsSelection":
        if self.longitude_max < self.longitude_min:
            raise ValueError("longitude_max must be greater or equal to longitude_min")
        return self
