import numpy as np
from eyepy import config
import matplotlib.pyplot as plt


class EyeBscan:
    def __init__(self, volume: "EyeVolume", index: int):
        self.index = index
        self._volume = volume

    @property
    def meta(self):
        return self._volume.meta["bscan_meta"][self.index]

    @property
    def name(self):
        return self.meta["name"]

    @property
    def data(self):
        return self._volume.data[self.index]

    @property
    def layers(self):
        return {
            key: val.height_map[-(self.index + 1)]
            for key, val in self._volume.layers.items()
        }

    @property
    def ascan_maps(self):
        return self._volume.ascan_maps[self.index]

    @property
    def area_maps(self):
        return {
            name: self._volume.volume_maps[name].data[self.index]
            for name in self._volume.volume_maps.keys()
        }

    @property
    def shape(self):
        return self.data.shape

    def plot(
        self,
        ax=None,
        layers=None,
        areas=None,
        ascans=None,
        layer_kwargs=None,
        area_kwargs=None,
        ascan_kwargs=None,
        annotation_only=False,
        region=np.s_[:, :],
    ):
        """Plot B-Scan with segmented Layers."""
        if ax is None:
            ax = plt.gca()

        # Complete region index expression
        if region[0].start is None:
            r0_start = 0
        else:
            r0_start = region[0].start
        if region[1].start is None:
            r1_start = 0
        else:
            r1_start = region[1].start
        if region[0].stop is None:
            r0_stop = self.shape[0]
        else:
            r0_stop = region[0].stop
        if region[1].stop is None:
            r1_stop = self.shape[1]
        else:
            r1_stop = region[1].stop
        region = np.s_[r0_start:r0_stop, r1_start:r1_stop]

        if layers is None:
            layers = []
        elif layers is True:
            layers = self.layers.keys()

        if areas is None:
            areas = []
        elif areas is True:
            areas = self.area_maps.keys()

        if ascans is None:
            ascans = []
        elif ascans is True:
            ascans = self.ascan_maps.keys()

        if layer_kwargs is None:
            layer_kwargs = config.layer_kwargs
        else:
            layer_kwargs = {**config.layer_kwargs, **layer_kwargs}

        if area_kwargs is None:
            area_kwargs = config.area_kwargs
        else:
            area_kwargs = {**config.area_kwargs, **area_kwargs}

        if ascan_kwargs is None:
            ascan_kwargs = config.area_kwargs
        else:
            ascan_kwargs = {**config.ascan_kwargs, **ascan_kwargs}

        if not annotation_only:
            ax.imshow(self.data[region], cmap="gray")

        for ascan_annotation in ascans:
            data = self.ascan_maps[ascan_annotation]
            data = np.repeat(np.reshape(data, (1, -1)), self.shape[0], axis=0)
            visible = np.zeros(data.shape)
            visible[data] = 1.0
            ax.imshow(
                data[region], alpha=visible[region] * ascan_kwargs["alpha"], cmap="Reds"
            )

        for area in areas:
            data = self.area_maps[area]
            visible = np.zeros(data.shape)
            visible[data] = 1.0
            ax.imshow(
                data[region],
                alpha=visible[region] * area_kwargs["alpha"],
                cmap="Reds",
                interpolation="none",
            )

        for layer in layers:
            color = config.layer_colors[layer]

            layer_data = self.layers[layer]
            # Adjust layer height to plotted region
            layer_data = layer_data - region[0].start
            # Remove layer if outside of region
            layer_data = layer_data[region[1].start : region[1].stop]
            layer_data[layer_data < 0] = 0
            region_height = region[0].stop - region[0].start
            layer_data[layer_data > region_height] = region_height

            ax.plot(
                layer_data,
                color=color,
                label=layer,
                **layer_kwargs,
            )
