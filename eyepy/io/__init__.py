from pathlib import Path

from eyepy import EyeData, EyeVolume, EyeEnface
from eyepy.io.lazy import LazyVolume


def import_heyex_xml(path):
    from eyepy.io.heyex import HeyexXmlReader

    reader = HeyexXmlReader(path)

    l_volume = LazyVolume(
        bscans=reader.bscans,
        localizer=reader.localizer,
        meta=reader.oct_meta,
        data_path=reader.path,
    )

    # if not l_volume.ScanPattern in [3,4]:
    #
    #
    # layer_height_maps = l_volume.layers
    # enface_meta = Meta(size_x, size_y, scale_x, scale_y, modality, laterality, field_size, scan_focus, visit_date, exam_time)
    # volume_meta = Meta(bscan_positions, )
    # volume = EyeVolume(data=l_volume.volume, annotations=, meta=)
    # enface = EyeEnface(data=l_volume.localizer)

    # return EyeData(volume=volume, enface=enface, meta=meta)


def import_heyex_vol(path):
    from eyepy.io.heyex import HeyexVolReader

    reader = HeyexVolReader(path)
    l_volume = LazyVolume(
        bscans=reader.bscans,
        localizer=reader.localizer,
        meta=reader.oct_meta,
        data_path=Path(path).parent,
    )


def import_bscan_folder(path):
    path = Path(path)
    img_paths = sorted(list(path.iterdir()))

    def read_func(p):
        return lambda: imageio.imread(p)

    bscans = [Bscan(read_func(p), name=p.name) for p in img_paths]
    return cls(bscans=bscans, data_path=path)


def import_enface_image():
    pass


def import_duke_mat():
    import scipy.io as sio

    loaded = sio.loadmat(path)
    data = np.moveaxis(loaded["images"], -1, 0)
    label = np.swapaxes(loaded["layerMaps"], 1, 2)

    bscans = []
    mapping = {"BM": 2, "RPE": 1, "ILM": 0}
    for d, l in zip(data, label):
        annotation = Annotation({"layers": LayerAnnotation(l, mapping)})
        bscans.append(Bscan(d, annotation=annotation))
    return cls(
        bscans=bscans,
        meta=Meta(**{"Age": loaded["Age"]}),
        data_path=Path(path).parent,
    )
