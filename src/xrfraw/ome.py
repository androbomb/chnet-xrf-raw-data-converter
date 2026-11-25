"""OME-TIFF / OME-BigTIFF export e lettura (schema: output_schema.md §OME-TIFF).

Uno IFD per canale spettrale: i canali XRF sono bande OME ``<Channel>``
(SamplesPerPixel=1), NON campioni RGB. L'OME-XML nell'IFD 0 porta la griglia
(PhysicalSizeX/Y) e, sotto una MapAnnotation versionata (``urn:xrfraw:v1``),
il metadata JSON completo, gli attributi scalari (asse energetico esplicito
post-rebin, calibrazione originale e post-rebin distinte, fattore R, unità
keV e convenzione bin-mean) e la maschera (zlib+base64). I piani oltre il
primo
NON portano metadati shaped: tifffile deve vedere un'unica serie OME CYX.
Al read l'energia viene presa dall'asse esplicito se presente, altrimenti
ri-derivata da m/q (``energy = m*channel + q``).
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
    if ds.energy is not None:  # asse esplicito (post-rebin) come in H5/NPZ
        attrs = {**attrs, "energy_axis": ds.energy.tolist()}
    tds = "".join(f'<TiffData FirstC="{c}" FirstT="0" IFD="{c}" PlaneCount="1"/>'
                  for c in range(nc))
    chans = "".join(f'<Channel ID="Channel:0:{c}" SamplesPerPixel="1"><LightPath/></Channel>'
                    for c in range(nc))
    mask_b64 = base64.b64encode(zlib.compress(ds.mask.tobytes(), 9)).decode()
    ann = (
        f'<StructuredAnnotations>'
        f'<MapAnnotation ID="Annotation:0" Namespace={quoteattr(_ANN_KEY)}>'
        f'<Value>'
        f'<M K="meta">{escape(json.dumps(meta, ensure_ascii=False))}</M>'
        f'<M K="attrs">{escape(json.dumps(attrs, ensure_ascii=False))}</M>'
        f'<M K="mask">{mask_b64}</M>'
        f'</Value></MapAnnotation></StructuredAnnotations>'
    )
    # OME-XML 2016-06 conforme allo XSD ufficiale: Size* su Pixels, booleani
    # lowercase, DimensionOrder XYZCT, Channel prima di TiffData, annotation
    # sotto OME (ID "Annotation:N", Namespace) + Image.AnnotationRef.
    xml = (
        f'<OME xmlns="{_OME_NS}" Creator={quoteattr(_software())}>'
        f'<Image ID="Image:0" Name={quoteattr(meta["source_file"])}>'
        f'<Pixels ID="Pixels:0" BigEndian="false" DimensionOrder="XYZCT" '
        f'Type={quoteattr(_TYPE[meta["dtype"]])} Interleaved="false" '
        f'SizeX="{nx}" SizeY="{ny}" SizeZ="1" SizeC="{nc}" SizeT="1" '
        f'PhysicalSizeX={quoteattr(str(grid["x_step"]))} '
        f'PhysicalSizeXUnit={quoteattr(meta["units"]["x"])} '
        f'PhysicalSizeY={quoteattr(str(grid["y_step"]))} '
        f'PhysicalSizeYUnit={quoteattr(meta["units"]["y"])}>'
        f'{chans}{tds}</Pixels><AnnotationRef ID="Annotation:0"/>'
        f'</Image>{ann}</OME>'
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
    # shaped=False: senza JSON "shaped" per piano, altrimenti tifffile vede
    # N serie YX distinte invece di un'unica serie OME CYX.
    with tifffile.TiffWriter(str(path), bigtiff=bigtiff, shaped=False) as tw:
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
    if px is None:
        raise ValueError("malformed OME-XML (missing Pixels)")
    dtype = _TIFF_TYPE.get(px.get("Type") or "")
    if dtype is None:
        raise ValueError(f"unsupported OME Type {px.get('Type')!r}")
    if any(px.get(k) is None for k in ("SizeC", "SizeY", "SizeX")):
        raise ValueError("malformed OME-XML (missing Size* attributes)")
    nc, ny, nx = (int(px.get(k)) for k in ("SizeC", "SizeY", "SizeX"))
    if len(planes) != nc or planes[0].shape != (ny, nx) or planes[0].dtype != dtype:
        raise ValueError("OME-XML dimensions do not match the stored planes")
    sa = next((a for a in root.iter(f"{{{_OME_NS}}}MapAnnotation")
               if a.get("Namespace") == _ANN_KEY or a.get("Key") == _ANN_KEY), None)
    if sa is None:
        raise ValueError(f"missing {_ANN_KEY} MapAnnotation (file non xrfraw?)")
    entries = {m.get("K"): m.text or "" for m in sa.findall(f"{{{_OME_NS}}}Value/{{{_OME_NS}}}M")}
    if not entries:  # tolleranza: OME 2008-02 (MapAnnotation.Map)
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
    cal = meta.get("calibration")
    cal_m = cal_q = None
    energy = None
    calibrated = False
    axis = attrs.get("energy_axis", attrs.get("energy"))  # "energy" = file 0.1.1
    if axis is not None:  # asse esplicito (writer con calibrazione, post-rebin)
        energy = np.asarray(axis, dtype=np.float64)
        if energy.size != nc:
            raise ValueError("stored energy axis does not match SizeC")
    if cal:
        # 0.1.1: m/q efficaci gia' post-rebin; v2: m_rebinned/q_rebinned
        cal_m = cal.get("m_rebinned", cal["m"])
        cal_q = cal.get("q_rebinned", cal["q"])
        if energy is None:  # file senza asse esplicito: ri-deriva da m/q
            energy = cal_m * channel.astype(np.float64) + cal_q
        calibrated = True
    return Dataset(img=img, channel=channel, x_axis=x_axis, y_axis=y_axis,
                   mask=mask, metadata=meta, source_file=attrs["source_file"],
                   n_events=attrs["n_events"], energy=energy,
                   calibration_m=cal_m, calibration_q=cal_q, calibrated=calibrated)