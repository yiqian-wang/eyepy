import os
from typing import MutableMapping


class Meta(MutableMapping):
    def __init__(self, *args, **kwargs):
        """The Meta object is a dict with additional functionalities.

        The additional functionallities are:
        1. A string representation suitable for printing the meta information.

        2. Checking if a keys value is a callable before returning it. In case
        it is a callable, it sets the value to the return value of the callable.
        This is used for lazy loading OCT data. The meta information for the OCT
        and all B-Scans is only read from the file when accessed.

        An instance of the meta object can be created as you would create an
        ordinary dictionary.

        For example:

            + Meta({"SizeX": 512})
            + Meta(SizeX=512)
            + Meta([(SizeX, 512), (SizeY, 512)])
        """
        self._store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        value = self._store[key]
        if callable(value):
            self[key] = value()
        return self._store[key]

    def __setitem__(self, key, value):
        self._store[key] = value

    def __delitem__(self, key):
        del self._store[key]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def __str__(self):
        return f"{os.linesep}".join([f"{f}: {self[f]}" for f in self if f != "__empty"])

    def __repr__(self):
        return self.__str__()
