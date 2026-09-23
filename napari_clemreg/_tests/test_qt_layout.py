import numpy as np
from qtpy.QtWidgets import QApplication

from napari_clemreg.clemreg._qt_layout import mark_auto_set, clear_highlight_on_user_select


def _labels_field():
    import napari
    from magicgui.widgets import create_widget

    viewer = napari.viewer.ViewerModel()
    layer_a = viewer.add_labels(np.zeros((4, 4, 4), dtype=np.uint8), name='layer_a')
    layer_b = viewer.add_labels(np.zeros((4, 4, 4), dtype=np.uint8), name='layer_b')

    field = create_widget(annotation=napari.layers.Labels, label='test')
    field.choices = (layer_a, layer_b)
    return field, layer_a, layer_b


def test_mark_auto_set_sets_value_and_highlight():
    QApplication.instance() or QApplication([])
    field, layer_a, __ = _labels_field()

    mark_auto_set(field, layer_a)

    assert field.value is layer_a
    assert field.native.styleSheet() != ''


def test_programmatic_reassignment_does_not_clear_highlight():
    """mark_auto_set() itself does `field.value = ...` -- if the
    highlight-clearing handler were wired to magicgui's own `.changed`
    signal (fired identically for a programmatic assignment and genuine
    user interaction) instead of the underlying Qt widget's `activated`
    signal (fired only for real user interaction), it would immediately
    undo its own highlight the moment mark_auto_set() applied it.
    """
    QApplication.instance() or QApplication([])
    field, layer_a, __ = _labels_field()
    clear_highlight_on_user_select(field)

    mark_auto_set(field, layer_a)
    assert field.native.styleSheet() != ''

    field.value = layer_a
    assert field.native.styleSheet() != ''


def test_genuine_user_interaction_clears_highlight():
    QApplication.instance() or QApplication([])
    field, layer_a, __ = _labels_field()
    clear_highlight_on_user_select(field)

    mark_auto_set(field, layer_a)
    assert field.native.styleSheet() != ''

    field.native.activated.emit(1)
    assert field.native.styleSheet() == ''
