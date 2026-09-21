"""Sample-data caching (modernisation plan §8.1, issue #11).

The fast test below just checks the pooch registry is well-formed --
no network. The end-to-end test actually downloads/caches the real
~275MB + ~337MB Zenodo files, so it's marked slow and skipped unless
`pytest --run-slow` is passed.
"""
import re

import pytest

from napari_clemreg.clemreg.sample_data import POOCH, make_sample_data

SHA256_HEX = re.compile(r"^sha256:[0-9a-f]{64}$")


def test_pooch_registry_is_well_formed():
    assert POOCH.base_url.startswith("https://")
    assert len(POOCH.registry) == 2
    for fname, hash_str in POOCH.registry.items():
        assert fname.endswith(".tif")
        assert SHA256_HEX.match(hash_str), f"{fname} hash doesn't look like sha256: {hash_str!r}"


@pytest.mark.slow
def test_make_sample_data_returns_expected_layers():
    result = make_sample_data()

    assert len(result) == 5
    names = [kwargs["name"] for _, kwargs in result]
    assert names == ["EM", "FM_TGN46", "FM_Lysotracker", "FM_Mitotracker", "FM_Hoechst"]

    em_data, em_kwargs = result[0]
    assert em_data.shape == (106, 1750, 1484)
    assert em_data.dtype.name == "uint8"

    for data, kwargs in result[1:]:
        assert data.ndim == 3
        assert "metadata" in kwargs
