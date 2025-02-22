# -*- coding: utf-8 -*-

import logging

from typing import Tuple, List, Dict, Union, Optional, Iterable
from datetime import datetime

import pandas as pd

from gordo_components.data_provider.providers import RandomDataProvider
from gordo_components.dataset.base import GordoBaseDataset
from gordo_components.data_provider.base import GordoBaseDataProvider
from gordo_components.dataset.filter_rows import pandas_filter_rows
from gordo_components.dataset.sensor_tag import SensorTag
from gordo_components.dataset.sensor_tag import normalize_sensor_tags

logger = logging.getLogger(__name__)


class TimeSeriesDataset(GordoBaseDataset):
    def __init__(
        self,
        data_provider: GordoBaseDataProvider,
        from_ts: datetime,
        to_ts: datetime,
        tag_list: List[Union[str, Dict, SensorTag]],
        target_tag_list: Optional[List[Union[str, Dict, SensorTag]]] = None,
        resolution: str = "10T",
        row_filter: str = "",
        **_kwargs,
    ):
        """
        Creates a TimeSeriesDataset backed by a provided dataprovider.

        A TimeSeriesDataset is a dataset backed by timeseries, but resampled,
        aligned, and (optionally) filtered.

        Parameters
        ----------
        data_provider: GordoBaseDataProvider
            A dataprovider which can provide dataframes for tags from from_ts to to_ts
        from_ts: datetime
            Earliest possible point in the dataset (inclusive)
        to_ts: datetime
            Earliest possible point in the dataset (exclusive)
        tag_list: List[Union[str, Dict, sensor_tag.SensorTag]]
            List of tags to include in the dataset. The elements can be strings,
            dictionaries or SensorTag namedtuples.
        target_tag_list: Optional[List[Union[str, Dict, sensor_tag.SensorTag]]]
            List of tags to set as the dataset y. These will be treated the same as
            tag_list when fetching and pre-processing (resampling) but will be split
            into the y return from ``.get_data()``
        resolution: str
            The bucket size for grouping all incoming time data (e.g. "10T").
        row_filter: str
            Filter on the rows. Only rows satisfying the filter will be in the dataset.
            See :func:`gordo_components.dataset.filter_rows.pandas_filter_rows` for
            further documentation of the filter format.
        _kwargs
        """
        self.from_ts = from_ts
        self.to_ts = to_ts
        self.tag_list = normalize_sensor_tags(tag_list)
        self.target_tag_list = (
            normalize_sensor_tags(target_tag_list) if target_tag_list else []
        )
        self.resolution = resolution
        self.data_provider = data_provider
        self.row_filter = row_filter

        if not self.from_ts.tzinfo or not self.to_ts.tzinfo:
            raise ValueError(
                f"Timestamps ({self.from_ts}, {self.to_ts}) need to include timezone "
                f"information"
            )

    def get_data(self) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:

        series_iter: Iterable[pd.Series] = self.data_provider.load_series(
            from_ts=self.from_ts,
            to_ts=self.to_ts,
            tag_list=list(set(self.tag_list + self.target_tag_list)),
        )
        data: pd.DataFrame = self.join_timeseries(
            series_iter, self.from_ts, self.to_ts, self.resolution
        )
        if self.row_filter:
            data = pandas_filter_rows(data, self.row_filter)

        x_tag_names = [tag.name for tag in self.tag_list]
        y_tag_names = [tag.name for tag in self.target_tag_list]

        X = data[x_tag_names]
        y = data[y_tag_names] if self.target_tag_list else None

        return X, y

    def get_metadata(self):
        metadata = {
            "tag_list": self.tag_list,
            "target_tag_list": self.target_tag_list,
            "train_start_date": self.from_ts,
            "train_end_date": self.to_ts,
            "resolution": self.resolution,
            "filter": self.row_filter,
        }
        return metadata


class RandomDataset(TimeSeriesDataset):
    """
    Get a TimeSeriesDataset backed by
    gordo_components.data_provider.providers.RandomDataProvider
    """

    def __init__(self, from_ts: datetime, to_ts: datetime, tag_list: list, **kwargs):
        kwargs.pop("data_provider", None)  # Dont care what you ask for, you get random!
        super().__init__(
            data_provider=RandomDataProvider(),
            from_ts=from_ts,
            to_ts=to_ts,
            tag_list=tag_list,
            **kwargs,
        )
