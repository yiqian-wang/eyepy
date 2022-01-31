from collections.abc import MutableMapping

import numpy as np


class Annotation(MutableMapping):
    def __init__(self, *args, **kwargs):
        self._store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys
        self._bscan = None

    def __getitem__(self, key):
        value = self._store[key]
        if callable(value):
            self[key] = value(self.bscan)
        return self._store[key]

    def __setitem__(self, key, value):
        self._store[key] = value

    def __delitem__(self, key):
        del self._store[key]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    # TODO: Make the annotation printable to get an overview
    # def __str__(self):
    #     return f"{os.linesep}".join(
    #         [f"{f}: {self[f]}" for f in self if f != "__empty"])

    # def __repr__(self):
    #     return self.__str__()

    @property
    def bscan(self):
        if self._bscan is None:
            raise AttributeError("bscan is not set for this Annotation.")
        return self._bscan

    @bscan.setter
    def bscan(self, value: "Bscan"):
        self._bscan = value


class LayerAnnotation(MutableMapping):
    def __init__(self, data, layername_mapping=None, max_height=2000):
        self._data = data
        self.max_height = max_height
        if layername_mapping is None:
            self.mapping = config.SEG_MAPPING
        else:
            self.mapping = layername_mapping

    @property
    def data(self):
        if callable(self._data):
            self._data = self._data()
        return self._data

    def __getitem__(self, key):
        data = self.data[self.mapping[key]]
        nans = np.isnan(data)
        empty = np.nonzero(
            np.logical_or(
                np.less(data, 0, where=~nans),
                np.greater(data, self.max_height, where=~nans),
            )
        )
        data = np.copy(data)
        data[empty] = np.nan
        if np.nansum(data) > 0:
            return data
        else:
            raise KeyError(f"There is no data given for the {key} layer")

    def __setitem__(self, key, value):
        self.data[self.mapping[key]] = value

    def __delitem__(self, key):
        self.data[self.mapping[key], :] = np.nan

    def __iter__(self):
        inv_map = {v: k for k, v in self.mapping.items()}
        return iter(inv_map.values())

    def __len__(self):
        return len(self.data.shape[0])

    def layer_indices(self, key):
        layer = self[key]
        nan_indices = np.isnan(layer)
        col_indices = np.arange(len(layer))[~nan_indices]
        row_indices = np.rint(layer).astype(int)[~nan_indices]

        return (row_indices, col_indices)
