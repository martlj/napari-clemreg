import logging

import pytest

from napari_clemreg.clemreg.em_segmentation import BACKENDS
from napari_clemreg.clemreg.on_init_specs import EM_BACKEND_LABELS, default_em_backend_label
from napari_clemreg.clemreg.widget_components import EM_BACKENDS


def test_every_core_backend_has_a_dropdown_label():
    assert set(EM_BACKEND_LABELS) == set(BACKENDS)
    assert set(EM_BACKENDS.values()) == set(BACKENDS)


def test_default_em_backend_is_segment_flow_without_env(monkeypatch):
    monkeypatch.delenv("CLEMREG_EM_BACKEND", raising=False)
    assert default_em_backend_label() == 'MitoNet (Segment-Flow)'


@pytest.mark.parametrize("name", BACKENDS)
def test_default_em_backend_honours_env(monkeypatch, name):
    monkeypatch.setenv("CLEMREG_EM_BACKEND", name)
    assert EM_BACKENDS[default_em_backend_label()] == name


def test_default_em_backend_ignores_unknown_env(monkeypatch, caplog):
    monkeypatch.setenv("CLEMREG_EM_BACKEND", "cellpose")
    with caplog.at_level(logging.WARNING):
        assert default_em_backend_label() == 'MitoNet (Segment-Flow)'
    assert "CLEMREG_EM_BACKEND" in caplog.text
