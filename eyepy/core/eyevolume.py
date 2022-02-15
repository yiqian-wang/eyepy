import numpy as np
from matplotlib import cm, colors, patches
from mpl_toolkits.axes_grid1 import make_axes_locatable
from skimage import transform

from eyepy.core.eyeenface import EyeEnface
from eyepy.core.eyebscan import EyeBscan
from eyepy.core.eyemeta import EyeMeta

from eyepy import config
from collections import defaultdict
from typing import Union, List
from skimage.transform._geometric import GeometricTransform

import matplotlib.pyplot as plt


class EyeLayer:
    def __init__(self, height_map, name, knots=None):
        self.height_map = height_map
        self.name = name
        if knots is None:
            self.knots = defaultdict(lambda: [])
        elif type(knots) is dict:
            self.knots = defaultdict(lambda: [], knots)

    def layer_indices(self):
        layer = self.height_map
        nan_indices = np.isnan(layer)
        col_indices = np.arange(len(layer))[~nan_indices]
        row_indices = np.rint(layer).astype(int)[~nan_indices]

        return (row_indices, col_indices)


class EyeVolumePixelAnnotation:
    def __init__(
        self,
        data,
        name,
        volume: "EyeVolume",
        radii=(1.5, 2.5),
        n_sectors=(1, 4),
        offsets=(0, 45),
        center=None,
    ):
        self.data = data
        self.name = name
        self.volume = volume

        self.radii = radii
        self.n_sectors = n_sectors
        self.offsets = offsets
        self.center = center

        self._masks = None
        self._quantification = None

    @property
    def projection(self):
        return np.flip(np.nansum(self.data, axis=1), axis=0)

    @property
    def enface(self):
        return transform.warp(
            self.projection,
            self.volume.localizer_transform.inverse,
            output_shape=(
                self.volume.localizer.size_y,
                self.volume.localizer.size_x,
            ),
            order=0,
        )

    def plot(
        self,
        ax=None,
        region=np.s_[...],
        cmap="Reds",
        vmin=None,
        vmax=None,
        cbar=True,
        alpha=1,
    ):
        enface_projection = self.enface

        if ax is None:
            ax = plt.gca()

        if vmin is None:
            vmin = 1
        if vmax is None:
            vmax = max([enface_projection.max(), vmin])

        visible = np.zeros(enface_projection[region].shape)
        visible[
            np.logical_and(
                vmin <= enface_projection[region], enface_projection[region] <= vmax
            )
        ] = 1

        if cbar:
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.05)
            plt.colorbar(
                cm.ScalarMappable(colors.Normalize(vmin=vmin, vmax=vmax), cmap=cmap),
                cax=cax,
            )

        ax.imshow(
            enface_projection[region],
            alpha=visible[region] * alpha,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
        )

    @property
    def masks(self):
        from eyepy.quantification.utils.grids import grid

        if self._masks is None:
            self._masks = grid(
                mask_shape=self.volume.localizer.shape,
                radii=self.radii,
                laterality=self.volume.laterality,
                n_sectors=self.n_sectors,
                offsets=self.offsets,
                radii_scale=self.volume.scale_x,
                center=self.center,
            )

        return self._masks

    @property
    def quantification(self):
        if self._quantification is None:
            self._quantification = self._quantify()

        return self._quantification

    def _quantify(self):
        enface_voxel_size_ym3 = (
            self.volume.localizer.scale_x
            * 1e3
            * self.volume.localizer.scale_y
            * 1e3
            * self.volume.scale_y
            * 1e3
        )
        oct_voxel_size_ym3 = (
            self.volume.scale_x
            * 1e3
            * self.volume.scale_z
            * 1e3
            * self.volume.scale_y
            * 1e3
        )

        enface_projection = self.enface

        results = {}
        for name, mask in self.masks.items():
            results[f"{name}"] = (
                (enface_projection * mask).sum() * enface_voxel_size_ym3 / 1e9
            )

        results["Total [mm³]"] = enface_projection.sum() * enface_voxel_size_ym3 / 1e9
        results["Total [OCT voxels]"] = self.projection.sum()
        results["OCT Voxel Size [µm³]"] = oct_voxel_size_ym3
        results["Laterality"] = self.volume.laterality
        return results

    def plot_quantification(
        self,
        ax=None,
        region=np.s_[...],
        alpha=0.5,
        vmin=None,
        vmax=None,
        cbar=True,
        cmap="YlOrRd",
    ):

        if ax is None:
            ax = plt.gca()

        mask_img = np.zeros(self.volume.localizer.shape, dtype=float)[region]
        visible = np.zeros_like(mask_img)
        for mask_name in self.masks.keys():
            mask_img += self.masks[mask_name][region] * self.quantification[mask_name]
            visible += self.masks[mask_name][region]

        if vmin is None:
            vmin = mask_img[visible.astype(int)].min()
        if vmax is None:
            vmax = max([mask_img.max(), vmin])

        if cbar:
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.05)
            plt.colorbar(
                cm.ScalarMappable(colors.Normalize(vmin=vmin, vmax=vmax), cmap=cmap),
                cax=cax,
            )

        ax.imshow(
            mask_img,
            alpha=visible * alpha,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
        )


class EyeVolume:
    def __init__(
        self,
        data,
        meta,
        layers=None,
        ascan_maps=None,
        localizer: "EyeEnface" = None,
        transformation: GeometricTransform = None,
    ):
        self.data = data
        self.meta = meta
        if layers is None:
            self.layers = {}
        else:
            self.layers = layers

        self.volume_maps = {}

        if ascan_maps is None:
            self.ascan_maps = {}
        else:
            self.ascan_maps = ascan_maps

        if transformation is None:
            self.localizer_transform = self._estimate_transform()
        else:
            self.localizer_transform = transformation

        if localizer is None:
            projection = np.flip(np.nanmean(data, axis=1), axis=0)
            image = transform.warp(
                projection,
                self.localizer_transform.inverse,
                output_shape=(self.size_x, self.size_x),
                order=1,
            )
            self.localizer = EyeEnface(
                image,
                meta=EyeMeta(
                    size_x=self.size_x,
                    size_y=self.size_x,
                    scale_x=self.scale_x,
                    scale_y=self.scale_x,
                ),
            )
        else:
            self.localizer = localizer

    def _estimate_transform(self):
        """Compute a transform to map a 2D projection of the volume to a square"""
        # Points in oct space
        src = np.array(
            [
                [0, 0],  # Top left
                [0, self.size_x - 1],  # Top right
                [self.size_z - 1, 0],  # Bottom left
                [self.size_z - 1, self.size_x - 1],
            ]
        )  # Bottom right

        # Respective points in enface space
        dst = np.array(
            [
                (0, 0),  # Top left
                (0, self.size_x - 1),  # Top right
                (self.size_x - 1, 0),  # Bottom left
                (self.size_x - 1, self.size_x - 1),
            ]
        )  # Bottom right

        # Switch from x/y coordinates to row/column coordinates
        src = src[:, [1, 0]]
        dst = dst[:, [1, 0]]
        return transform.estimate_transform("affine", src, dst)

    def __getitem__(self, index) -> Union[EyeBscan, List[EyeBscan]]:
        """The B-Scan at the given index."""
        if type(index) == slice:
            return [self[i] for i in range(*index.indices(len(self)))]
        else:
            if index <= len(self):
                return EyeBscan(self, index)
            else:
                raise IndexError()

    def __len__(self):
        """The number of B-Scans."""
        return self.shape[0]

    @property
    def shape(self):
        return self.data.shape

    @property
    def size_z(self):
        return self.shape[0]

    @property
    def size_y(self):
        return self.shape[1]

    @property
    def size_x(self):
        return self.shape[2]

    @property
    def scale_z(self):
        return self.meta["scale_z"]

    @property
    def scale_y(self):
        return self.meta["scale_y"]

    @property
    def scale_x(self):
        return self.meta["scale_x"]

    @property
    def laterality(self):
        return self.meta["laterality"]

    def set_volume_map(self, name, value):
        self.volume_maps[name] = EyeVolumePixelAnnotation(value, name, self)

    def plot(
        self,
        ax=None,
        localizer=True,
        projections=False,
        bscan_region=False,
        bscan_positions=None,
        quantification=None,
        region=np.s_[...],
        projection_kwargs=None,
        line_kwargs=None,
    ):
        """

        Args:
            ax:
            localizer:
            projections:
            bscan_region:
            bscan_positions:
            masks:
            region:
            projection_kwargs:

        Returns:

        """

        if ax is None:
            ax = plt.gca()

        if localizer:
            self.localizer.plot(ax=ax, region=region)

        if projections is True:
            projections = list(self.volume_maps.keys())
        elif not projections:
            projections = []

        if projection_kwargs is None:
            projection_kwargs = defaultdict(lambda: {})
        for name in projections:
            if not name in projection_kwargs.keys():
                projection_kwargs[name] = {}
            self.volume_maps[name].plot(ax=ax, region=region, **projection_kwargs[name])

        if line_kwargs is None:
            line_kwargs = config.line_kwargs
        else:
            line_kwargs = {**config.line_kwargs, **line_kwargs}

        if bscan_positions is not None:
            self._plot_bscan_positions(
                ax=ax,
                bscan_positions=bscan_positions,
                region=region,
                line_kwargs=line_kwargs,
            )
        if bscan_region:
            self._plot_bscan_region(region=region, ax=ax, line_kwargs=line_kwargs)

        if quantification:
            self.volume_maps[quantification].plot_quantification(region=region, ax=ax)

    def plot_bscan_ticks(self, ax=None):
        if ax is None:
            ax = plt.gca()
        ax.yticks()

    def _plot_bscan_positions(
        self, bscan_positions="all", ax=None, region=np.s_[...], line_kwargs=None
    ):
        if not bscan_positions:
            bscan_positions = []
        elif bscan_positions == "all" or bscan_positions is True:
            bscan_positions = range(0, len(self))

        for i in bscan_positions:
            scale = np.array([self.localizer.scale_x, self.localizer.scale_y])

            start = self[i].meta["start_pos"] / scale
            end = self[i].meta["end_pos"] / scale

            # x = [start[0], end[0]]
            # y = [start[1], end[1]]
            # ax.plot(x, y, **line_kwargs)
            polygon = patches.Polygon(
                np.array([start, end]),
                closed=False,
                fill=False,
                alpha=1,
                antialiased=False,
                rasterized=False,
                snap=False,
                **line_kwargs,
            )
            ax.add_patch(polygon)

    def _plot_bscan_region(self, region=np.s_[...], ax=None, line_kwargs=None):
        if ax is None:
            ax = plt.gca()

        scale = np.array([self.localizer.scale_x, self.localizer.scale_y])

        upper_left = self[-1].meta["start_pos"] / scale
        lower_left = self[0].meta["start_pos"] / scale
        lower_right = self[0].meta["end_pos"] / scale
        upper_right = self[-1].meta["end_pos"] / scale

        polygon = patches.Polygon(
            np.array([upper_left, lower_left, lower_right, upper_right]),
            closed=True,
            fill=False,
            alpha=1,
            antialiased=False,
            rasterized=False,
            snap=False,
            **line_kwargs,
        )
        ax.add_patch(polygon)

    # ToDo: Add more plotting functionality
    # def plot_localizer_bscan(self, ax=None, n_bscan=0):
    #     """Plot Slo with one selected B-Scan."""
    #     raise NotImplementedError()
    #
    # def plot_bscans(
    #         self, bs_range=range(0, 8), cols=4, layers=None, layer_kwargs=None
    # ):
    #     """Plot a grid with B-Scans."""
    #     rows = int(np.ceil(len(bs_range) / cols))
    #     if layers is None:
    #         layers = []
    #
    #     fig, axes = plt.subplots(cols, rows, figsize=(rows * 4, cols * 4))
    #
    #     with np.errstate(invalid="ignore"):
    #         for i in bs_range:
    #             bscan = self[i]
    #             ax = axes.flatten()[i]
    #             bscan.plot(ax=ax, layers=layers, layer_kwargs=layer_kwargs)
    #
    # def plot_masks(self, region=np.s_[...], ax=None, color="r", linewidth=0.5):
    #     """
    #
    #     Parameters
    #     ----------
    #     region :
    #     ax :
    #     color :
    #     linewidth :
    #
    #     Returns
    #     -------
    #
    #     """
    #     primitives = self._eyequantifier.plot_primitives(self)
    #     if ax is None:
    #         ax = plt.gca()
    #
    #     for circle in primitives["circles"]:
    #         c = patches.Circle(
    #             circle["center"],
    #             circle["radius"],
    #             facecolor="none",
    #             edgecolor=color,
    #             linewidth=linewidth,
    #         )
    #         ax.add_patch(c)
    #
    #     for line in primitives["lines"]:
    #         x = [line["start"][0], line["end"][0]]
    #         y = [line["start"][1], line["end"][1]]
    #         ax.plot(x, y, color=color, linewidth=linewidth)
