import numpy as np
import matplotlib.pyplot as plt


class EyeVolume:
    def __init__(self, data, annotations, meta):
        self.volume = data
        self.annotations = annotations
        self.meta = meta


class EyeEnface:
    def __init__(self, data, annotations, meta):
        self.data = data
        self.annotations = annotations
        self.meta = meta

    def register(self):
        pass


class EyeBscan:
    def __init__(self, volume: EyeVolume, index: int):
        self.index = index
        self._volume = volume

    @property
    def data(self):
        return self._volume[self.index]

    def plot(
        self,
        ax=None,
        layers=None,
        drusen=False,
        layers_kwargs=None,
        layers_color=None,
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
        elif layers == "all":
            layers = self.layers.keys()

        if layers_kwargs is None:
            layers_kwargs = config.layers_kwargs
        else:
            layers_kwargs = {**config.layers_kwargs, **layers_kwargs}

        if layers_color is None:
            layers_color = config.layers_color
        else:
            layers_color = {**config.layers_color, **layers_color}

        if not annotation_only:
            ax.imshow(self.scan[region], cmap="gray")
        if drusen:
            visible = np.zeros(self.drusen.shape)
            visible[self.drusen] = 1.0
            ax.imshow(self.drusen[region], alpha=visible[region], cmap="Reds")
        for layer in layers:
            color = layers_color[layer]
            try:
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
                    **layers_kwargs,
                )
            except KeyError:
                warnings.warn(f"Layer '{layer}' has no Segmentation", UserWarning)


class EyeData:
    def __init__(self, eye_volume, eye_enface, meta):
        self.volume = eye_volume
        self.enface = eye_enface
        self.meta = meta

    def add_enface(self):
        pass

    def remove_enface(self):
        pass

    def add_volume(self):
        pass

    def remove_volume(self):
        pass

    def save(self, path):
        pass

    def load(self, path):
        pass

    @property
    def drusen_projection(self):
        # Sum the all B-Scans along their first axis (B-Scan height)
        # Swap axis such that the volume depth becomes the projections height not width
        # We want the first B-Scan to be located at the bottom hence flip along axis 0
        return np.flip(np.swapaxes(np.sum(self.drusen, axis=0), 0, 1), axis=0)

    @property
    def drusen_enface(self):
        """Drusen projection warped into the localizer space."""
        return transform.warp(
            self.drusen_projection.astype(float),
            self.tform_oct_to_localizer,
            output_shape=self.localizer_shape,
            order=0,
        )

    @property
    def tform_localizer_to_oct(self):
        if self._tform_localizer_to_oct is None:
            self._tform_localizer_to_oct = self._estimate_localizer_to_oct_tform()
        return self._tform_localizer_to_oct

    @property
    def tform_oct_to_localizer(self):
        return self.tform_localizer_to_oct.inverse

    @property
    def localizer_shape(self):
        try:
            return self.localizer.shape
        except:
            return (self.SizeX, self.SizeX)

    def _estimate_localizer_to_oct_tform(self):
        oct_projection_shape = (self.NumBScans, self.SizeX)
        src = np.array(
            [
                oct_projection_shape[0] - 1,
                0,  # Top left
                oct_projection_shape[0] - 1,
                oct_projection_shape[1] - 1,  # Top right
                0,
                0,  # Bottom left
                0,
                oct_projection_shape[1] - 1,  # Bottom right
            ]
        ).reshape((-1, 2))
        src = np.array(
            [
                0,
                0,  # Top left
                0,
                oct_projection_shape[1] - 1,  # Top right
                oct_projection_shape[0] - 1,
                0,  # Bottom left
                oct_projection_shape[0] - 1,
                oct_projection_shape[1] - 1,  # Bottom right
            ]
        ).reshape((-1, 2))

        try:
            # Try to map the oct projection to the localizer image
            dst = np.array(
                [
                    self[-1].StartY / self.ScaleXSlo,
                    self[-1].StartX / self.ScaleYSlo,
                    self[-1].EndY / self.ScaleXSlo,
                    self[-1].EndX / self.ScaleYSlo,
                    self[0].StartY / self.ScaleXSlo,
                    self[0].StartX / self.ScaleYSlo,
                    self[0].EndY / self.ScaleXSlo,
                    self[0].EndX / self.ScaleYSlo,
                ]
            ).reshape((-1, 2))
        except AttributeError:
            # Map the oct projection to a square area of shape (bscan_width, bscan_width)
            warnings.warn(
                f"Bscan positions on localizer image or the scale of the "
                f"localizer image is missing. We assume that the B-Scans cover "
                f"a square area and are equally spaced.",
                UserWarning,
            )
            b_width = self[0].shape[1]
            dst = np.array(
                [
                    0,
                    0,  # Top left
                    0,
                    b_width - 1,  # Top right
                    b_width - 1,
                    0,  # Bottom left
                    b_width - 1,
                    b_width - 1,  # Bottom right
                ]
            ).reshape((-1, 2))

        src = src[:, [1, 0]]
        dst = dst[:, [1, 0]]
        tform = transform.estimate_transform("affine", src, dst)

        if not np.allclose(tform.inverse(tform(src)), src):
            msg = f"Problem with transformation of OCT Projection to the localizer image space."
            raise ValueError(msg)

        return tform

    def bscan(self, index):
        return EyeBscan(self.volume, index)

    # Data Access:
    # Bscans r
    # Projections r(w)
    # Shadows r(w)
    # Annotations rw
    # Registrations rw
    # Meta rw

    # Bscan View into the volume

    # Projection views of volume in enface space

    # Projection views of volume annotation in enface space

    # Save and load data

    # Export annotations only

    def plot(
        self,
        ax=None,
        localizer=True,
        drusen=False,
        bscan_region=False,
        bscan_positions=None,
        masks=False,
        region=np.s_[...],
        drusen_kwargs=None,
    ):
        """

        Parameters
        ----------
        ax :
        slo :
        drusen :
        bscan_region :
        bscan_positions :
        masks :
        region : slice object
        alpha :

        Returns
        -------

        """

        if ax is None:
            ax = plt.gca()

        if localizer:
            self.plot_localizer(ax=ax, region=region)
        if drusen:
            if drusen_kwargs is None:
                drusen_kwargs = {}
            self.plot_drusen(ax=ax, region=region, **drusen_kwargs)
        if bscan_positions is not None:
            self.plot_bscan_positions(
                ax=ax,
                bscan_positions=bscan_positions,
                region=region,
                line_kwargs={"linewidth": 0.5, "color": "green"},
            )
        if bscan_region:
            self.plot_bscan_region(region=region, ax=ax)

        if masks:
            self.plot_masks(region=region, ax=ax)
        # if quantification:
        #    self.plot_quantification(space=space, region=region, ax=ax,
        #    q_kwargs=q_kwargs)

    def plot_bscan_ticks(self, ax=None):
        if ax is None:
            ax = plt.gca()
        ax.yticks()

    def plot_layer_distance(
        self,
        region=np.s_[...],
        ax=None,
        bot_layer="BM",
        top_layer="RPE",
        vmin=None,
        vmax=None,
    ):
        if ax is None:
            ax = plt.gca()

        dist = self.layers["BM"] - self.layers["RPE"]
        img = transform.warp(
            dist.astype(float),
            self.tform_oct_to_localizer,
            output_shape=self.localizer_shape,
            order=0,
        )
        ax.imshow(img[region], cmap="gray", vmin=vmin, vmax=vmax)

    def plot_masks(self, region=np.s_[...], ax=None, color="r", linewidth=0.5):
        """

        Parameters
        ----------
        region :
        ax :
        color :
        linewidth :

        Returns
        -------

        """
        primitives = self._eyequantifier.plot_primitives(self)
        if ax is None:
            ax = plt.gca()

        for circle in primitives["circles"]:
            c = patches.Circle(
                circle["center"],
                circle["radius"],
                facecolor="none",
                edgecolor=color,
                linewidth=linewidth,
            )
            ax.add_patch(c)

        for line in primitives["lines"]:
            x = [line["start"][0], line["end"][0]]
            y = [line["start"][1], line["end"][1]]
            ax.plot(x, y, color=color, linewidth=linewidth)

    def plot_localizer(self, ax=None, region=np.s_[...]):
        if ax is None:
            ax = plt.gca()
        ax.imshow(self.localizer[region], cmap="gray")

    def plot_bscan_positions(
        self, bscan_positions="all", ax=None, region=np.s_[...], line_kwargs=None
    ):
        if bscan_positions is None:
            bscan_positions = []
        elif bscan_positions == "all" or bscan_positions is True:
            bscan_positions = range(0, len(self))

        if line_kwargs is None:
            line_kwargs = config.line_kwargs
        else:
            line_kwargs = {**config.line_kwargs, **line_kwargs}

        for i in bscan_positions:
            bscan = self[i]
            x = np.array([bscan.StartX, bscan.EndX]) / self.ScaleXSlo
            y = np.array([bscan.StartY, bscan.EndY]) / self.ScaleYSlo

            ax.plot(x, y, **line_kwargs)

    def plot_bscan_region(self, region=np.s_[...], ax=None):

        if ax is None:
            ax = plt.gca()

        up_right_corner = (
            self[-1].EndX / self.ScaleXSlo,
            self[-1].EndY / self.ScaleYSlo,
        )
        width = (self[0].StartX - self[0].EndX) / self.ScaleXSlo
        height = (self[0].StartY - self[-1].EndY) / self.ScaleYSlo
        # Create a Rectangle patch
        rect = patches.Rectangle(
            up_right_corner, width, height, linewidth=1, edgecolor="r", facecolor="none"
        )

        # Add the patch to the Axes
        ax.add_patch(rect)

    def plot_drusen(
        self,
        ax=None,
        region=np.s_[...],
        cmap="Reds",
        vmin=None,
        vmax=None,
        cbar=True,
        alpha=1,
    ):
        drusen = self.drusen_enface

        if ax is None:
            ax = plt.gca()

        if vmin is None:
            vmin = 1
        if vmax is None:
            vmax = max([drusen.max(), vmin])

        visible = np.zeros(drusen[region].shape)
        visible[np.logical_and(vmin < drusen[region], drusen[region] < vmax)] = 1

        if cbar:
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.05)
            plt.colorbar(
                cm.ScalarMappable(colors.Normalize(vmin=vmin, vmax=vmax), cmap=cmap),
                cax=cax,
            )

        ax.imshow(
            drusen[region],
            alpha=visible[region] * alpha,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
        )

    def plot_localizer_bscan(self, ax=None, n_bscan=0):
        """Plot Slo with one selected B-Scan."""
        raise NotImplementedError()

    def plot_bscans(
        self, bs_range=range(0, 8), cols=4, layers=None, layers_kwargs=None
    ):
        """Plot a grid with B-Scans."""
        rows = int(np.ceil(len(bs_range) / cols))
        if layers is None:
            layers = []

        fig, axes = plt.subplots(cols, rows, figsize=(rows * 4, cols * 4))

        with np.errstate(invalid="ignore"):
            for i in bs_range:
                bscan = self[i]
                ax = axes.flatten()[i]
                bscan.plot(ax=ax, layers=layers, layers_kwargs=layers_kwargs)
