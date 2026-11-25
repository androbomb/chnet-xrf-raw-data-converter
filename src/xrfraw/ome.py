"""OME-TIFF / OME-BigTIFF export e lettura (schema: output_schema.md §OME-TIFF).

Uno IFD per canale spettrale: i canali XRF sono bande OME ``<Channel>``
(SamplesPerPixel=1), NON campioni RGB. L'OME-XML nell'IFD 0 porta la griglia
(PhysicalSizeX/Y) e, sotto una MapAnnotation versionata (``urn:xrfraw:v1``),
il metadata JSON completo, gli attributi scalari e la maschera (zlib+base64).
Al read la calibrazione viene ri-derivata da m/q (``energy = m*channel + q``).
"""
from __future__ import annotations

import base64
import json
import zlib
import xml.etree.ElementTree as ET
from importlib.metadata import PackageNotFoundError, version as _dist_version
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import numpy as np
import tifffile

from .dataset import Dataset
from .io import _attrs

_ANN_KEY = "urn:xrfraw:v1"
_OME_NS = "http://www.openmicroscopy.org/Schemas/OME/2016-06"
_TYPE = {"uint16": "uint16", "uint32": "uint32", "float32": "float", "float64": "double"}
_TIFF_TYPE = {"uint16": np.uint16, "uint32": np.uint32,
              "float": np.float32, "double": np.float64}


def _software() -> str:
    try:
        return f"xrfraw {_dist_version('chnet-xrf-raw-data-converter')}"
    except PackageNotFoundError:
        return "xrfraw"


def _ome_xml(ds: Dataset, compress: int) -> str:
    ny, nx, nc = ds.img.shape
    meta = ds.metadata
    grid = meta["grid"]
    attrs = _attrs(ds, compress)
    tds = "".join(f'<TiffData FirstC="{c}" FirstT="0" IFD="{c}" PlaneCount="1"/>'
                  for c in range(nc))
    chans = "".join(f'<Channel ID="Channel:0:{c}" SamplesPerPixel="1"><LightPath/></Channel>'
                    for c in range(nc))
    mask_b64 = base64.b64encode(zlib.compress(ds.mask.tobytes(), 9)).decode()
    xml = (
        f'<OME xmlns="{_OME_NS}" UniqueID={quoteattr("xrfraw-" + meta["source_file"])} '
        f'Creator={quoteattr(_software())}>'
        f'<Image ID="Image:0" Name={quoteattr(meta["source_file"])}>'
        f'<Pixels ID="Pixels:0" BigEndian="False" DimensionOrder="CYX" DimensionType="C" '
        f'Type={quoteattr(_TYPE[meta["dtype"]])} Interleaved="False" SamplesPerPixel="1" '
        f'PhysicalSizeX={quoteattr(str(grid["x_step"]))} '
        f'PhysicalSizeXUnit={quoteattr(meta["units"]["x"])} '
        f'PhysicalSizeY={quoteattr(str(grid["y_step"]))} '
        f'PhysicalSizeYUnit={quoteattr(meta["units"]["y"])}>'
        f'<Dimension C="{nc}" H="{ny}" W="{nx}"/>{tds}{chans}</Pixels>'
        f'<StructuredAnnotations>'
        f'<MapAnnotation ID="MapAnnotation:0" Key={quoteattr(_ANN_KEY)}>'
        f'<MapAnnotation.Map Key="meta">{escape(json.dumps(meta, ensure_ascii=False))}</MapAnnotation.Map>'
        f'<MapAnnotation.Map Key="attrs">{escape(json.dumps(attrs, ensure_ascii=False))}</MapAnnotation.Map>'
        f'<MapAnnotation.Map Key="mask">{mask_b64}</MapAnnotation.Map>'
        f'</MapAnnotation></StructuredAnnotations></Image></OME>'
    )
    # TIFF Description requires 7-bit ASCII: non-ASCII (es. unità µm) -> charref
    return xml.encode("ascii", "xmlcharrefreplace").decode("ascii")


def write_ome(ds: Dataset, path, compress: int = 4, bigtiff: bool | None = None) -> Path:
    """Scrivi ``ds`` come OME-TIFF: un piano (Y, X) per canale, senza copie del cubo."""
    path = Path(path)
    if bigtiff is None:
        bigtiff = ds.img.nbytes > 2**32  # classic TIFF si ferma a ~4 GB di dati
    xml = _ome_xml(ds, compress)
    compression = None if compress == 0 else "zlib"
    args = None if compress == 0 else {"level": compress}
    ny, nx, nc = ds.img.shape
    with tifffile.TiffWriter(str(path), bigtiff=bigtiff) as tw:
        for c in range(nc):
            tw.write(ds.img[:, :, c], description=xml if c == 0 else None,
                     compression=compression, compressionargs=args)
    return path


def read_ome(path) -> Dataset:
    """Leggi un OME-TIFF scritto da ``write_ome`` e restituisce un Dataset."""
    path = Path(path)
    with tifffile.TiffFile(str(path)) as tf:
        xml = tf.ome_metadata
        if not xml:
            raise ValueError(f"not an OME-TIFF (no OME-XML): {path}")
        planes = [tf.pages[i].asarray() for i in range(len(tf.pages))]
    root = ET.fromstring(xml)
    px = root.find(f"{{{_OME_NS}}}Image/{{{_OME_NS}}}Pixels")
    dim = px.find(f"{{{_OME_NS}}}Dimension") if px is not None else None
    if px is None or dim is None:
        raise ValueError("malformed OME-XML (missing Pixels/Dimension)")
    dtype = _TIFF_TYPE.get(px.get("Type") or "")
    if dtype is None:
        raise ValueError(f"unsupported OME Type {px.get('Type')!r}")
    nc, ny, nx = int(dim.get("C")), int(dim.get("H")), int(dim.get("W"))
    if len(planes) != nc or planes[0].shape != (ny, nx) or planes[0].dtype != dtype:
        raise ValueError("OME-XML dimensions do not match the stored planes")
    sa = root.find(f"{{{_OME_NS}}}Image/{{{_OME_NS}}}StructuredAnnotations/"
                   f"{{{_OME_NS}}}MapAnnotation")
    if sa is None or sa.get("Key") != _ANN_KEY:
        raise ValueError(f"missing {_ANN_KEY} MapAnnotation (file non xrfraw?)")
    entries = {m.get("Key"): m.text or "" for m in sa.findall(f"{{{_OME_NS}}}MapAnnotation.Map")}
    meta = json.loads(entries["meta"])
    attrs = json.loads(entries["attrs"])
    mask = np.frombuffer(zlib.decompress(base64.b64decode(entries["mask"])),
                         dtype=bool).reshape(ny, nx)
    img = np.stack(planes).astype(dtype).transpose(1, 2, 0)
    grid = meta["grid"]
    channel = np.arange(nc, dtype=np.uint32)
    x_axis = (grid["x_min"] + np.arange(nx) * grid["x_step"]).astype(np.float64)
    y_axis = (grid["y_min"] + np.arange(ny) * grid["y_step"]).astype(np.float64)
    energy = cal_m = cal_q = None
    calibrated = False
    cal = meta.get("calibration")
    if cal:
        cal_m, cal_q = cal["m"], cal["q"]
        energy = cal_m * channel.astype(np.float64) + cal_q
        calibrated = True
    return Dataset(img=img, channel=channel, x_axis=x_axis, y_axis=y_axis,
                   mask=mask, metadata=meta, source_file=attrs["source_file"],
                   n_events=attrs["n_events"], energy=energy,
                   calibration_m=cal_m, calibration_q=cal_q, calibrated=calibrated)