from __future__ import annotations

import numpy as np
import pooch
import tifffile

# Cached under the OS-appropriate app-cache directory (~/.cache/napari-clemreg
# on Linux, ~/Library/Caches/napari-clemreg on macOS, %LOCALAPPDATA%\napari-clemreg
# on Windows) so these ~275MB/~337MB files are downloaded once, not on every
# call. Hashes pin the exact archived Zenodo record 7936982 files, verified on
# fetch so a corrupted/interrupted download is caught rather than silently used.
POOCH = pooch.create(
    path=pooch.os_cache("napari-clemreg"),
    base_url="https://zenodo.org/record/7936982/files/",
    registry={
        "em_20nm_z_40_145.tif": "sha256:805df382bee3c31a58b44e670d59eb2b299fe54a507151d4aff2f095d19c0f2a",
        "EM04468_2_63x_pos8T_LM_raw.tif": "sha256:3afd3730fcafebf4355a494e36c04c338dad2cf84f0d970c4e5f653435c51131",
    },
)


def make_sample_data():
    """Generates an image"""
    # Return list of tuples
    # [(data1, add_image_kwargs1), (data2, add_image_kwargs2)]
    # Check the documentation for more information about the
    # add_image_kwargs
    # https://napari.org/stable/api/napari.Viewer.html#napari.Viewer.add_image

    print('Loading EM...')
    em = tifffile.imread(POOCH.fetch('em_20nm_z_40_145.tif', progressbar=True))
    print('Loading FM...')
    fm = tifffile.imread(POOCH.fetch('EM04468_2_63x_pos8T_LM_raw.tif', progressbar=True))

    fm = np.moveaxis(fm, -1, 0)

    fm_metadata = {'ImageDescription': 'ImageJ=1.53t\nimages=112\nchannels=4\nslices=28\nhyperstack=true\nmode=grayscale\nunit=micron\nspacing=0.13\nloop=false\nmin=0.0\nmax=65535.0\n',
                   'XResolution': 28.349506,
                   'YResolution': 28.349506}
    em_metadata = {'ImageDescription': '\nunit=micron\nspacing=0.02\n',
                   'XResolution': 50,
                   'YResolution': 50}

    return [(em, {'name': 'EM', 'metadata': em_metadata}),
            (fm[0, 7:], {'blending': 'additive', 'colormap': 'green', 'name': 'FM_TGN46', 'metadata': fm_metadata}),
            (fm[1, 7:], {'blending': 'additive', 'colormap': 'magenta', 'name': 'FM_Lysotracker', 'metadata': fm_metadata}),
            (fm[2, 7:], {'blending': 'additive', 'colormap': 'cyan', 'name': 'FM_Mitotracker', 'metadata': fm_metadata}),
            (fm[3, 7:], {'blending': 'additive', 'colormap': 'blue', 'name': 'FM_Hoechst', 'metadata': fm_metadata})
            ]
