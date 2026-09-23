#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np

def napari_get_reader(path):
    if isinstance(path, str) and path.endswith((".tif", ".tiff")):
        return bioio_reader

def bioio_reader(path: str):
    """ Reads pixel data and pixel-size metadata via bioio, rather than
    hand-parsing raw TIFF tags for ImageJ's specific metadata convention
    (the previous approach here, via PIL's EXIF extraction). bioio
    normalises both axis ordering and physical pixel size extraction
    across file formats via per-format reader plugins, so this isn't
    limited to ImageJ-written TIFFs the way the old approach was --
    confirmed directly: run against the two real sample-data TIFFs, it
    correctly extracts pixel size from the one that has it embedded, and
    correctly reports None (not a wrong silent default) for the one that
    doesn't.

    See data_preprocessing.get_pixelsize(), which reads the
    `physical_pixel_sizes` key this puts in the layer's metadata.
    """
    from bioio import BioImage

    img = BioImage(path)
    # bioio always orders axes as TCZYX; squeezing out any size-1 axes
    # (almost always T, and C when single-channel) gives the same shape
    # a widget expects -- (Z, Y, X) for a single-channel volume, or
    # (C, Z, Y, X) if there's more than one channel, for the user to
    # split via napari's own layer-splitting tools before running the
    # plugin's widgets, same as before.
    image_data = np.squeeze(img.data)

    layer_kwargs = {"metadata": {"physical_pixel_sizes": img.physical_pixel_sizes}}
    return [(image_data, layer_kwargs, "image")]
