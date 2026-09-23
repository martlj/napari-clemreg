"""Behaviour tests for the widgets: run them and check what they do.

test_dock_widget.py only checks that each widget builds. Almost every
widget bug fixed so far (#23, #25, #27, #29, and the viewer-injection
crash fixed in 9305d4b), plus #53 and the open #47 and #50, is in code that only
runs once a widget is *called* or a button is *clicked*. These tests
cover that code.

They don't need a real napari window, so they avoid the local
offscreen-OpenGL segfault described in test_dock_widget.py:

- `viewer` is a `napari.components.ViewerModel` (layers, no canvas),
  installed as `napari.viewer.current_viewer()`. magicgui's napari
  integration uses that to fill Layer dropdowns and inject the viewer.
- `pipeline` swaps the four `widget_components.run_*` functions for fast
  stubs that record their keyword arguments. The widgets import these at
  call time, so patching the module attributes reaches all of them.
- `errors` captures `show_error` calls, which is how the widgets report
  problems to users.

Tests marked `xfail(strict=True)` pin a known, open bug to its issue.
When the bug is fixed the test starts passing, strict mode fails it, and
the marker needs removing.
"""
import json

import numpy as np
import pytest
from napari.components import ViewerModel
from napari.layers import Image, Labels, Points

import napari_clemreg.clemreg.widget_components as widget_components
from napari_clemreg.widgets import (
    fixed_segmentation,
    moving_segmentation,
    point_cloud_sampling,
    registration_warping,
    run_registration,
)
from napari_clemreg.widgets.fixed_segmentation import fixed_segmentation_widget
from napari_clemreg.widgets.moving_segmentation import moving_segmentation_widget
from napari_clemreg.widgets.point_cloud_sampling import point_cloud_sampling_widget
from napari_clemreg.widgets.registration_warping import registration_warping_widget
from napari_clemreg.widgets.run_registration import make_run_registration

SHAPE = (8, 32, 32)
TIMEOUT_MS = 5000


def _labels_array():
    labels = np.zeros(SHAPE, dtype=np.int64)
    labels[2:6, 8:20, 8:20] = 1
    return labels


def _points(name):
    return Points(np.random.default_rng(0).uniform(0, 30, size=(20, 3)), name=name)


class Pipeline:
    """Stand-ins for the widget_components.run_* functions.

    `calls[name]` is the list of kwargs each stub was called with. Set
    `fixed_result` / `moving_result` to change what the segmentation
    stubs return (e.g. 'No segmentation'), or `fixed_error` /
    `sampling_error` to make EM segmentation or point cloud sampling
    raise.
    """

    def __init__(self):
        self.calls = {name: [] for name in (
            'run_fixed_segmentation', 'run_moving_segmentation',
            'run_point_cloud_sampling', 'run_point_cloud_registration_and_warping')}
        self.fixed_result = _labels_array()
        self.moving_result = _labels_array()
        self.fixed_error = None
        self.sampling_error = None

    def run_fixed_segmentation(self, **kwargs):
        self.calls['run_fixed_segmentation'].append(kwargs)
        if self.fixed_error is not None:
            raise self.fixed_error
        return self.fixed_result

    def run_moving_segmentation(self, **kwargs):
        self.calls['run_moving_segmentation'].append(kwargs)
        return self.moving_result

    def run_point_cloud_sampling(self, **kwargs):
        self.calls['run_point_cloud_sampling'].append(kwargs)
        if self.sampling_error is not None:
            raise self.sampling_error
        # The real function's layer names; run_registration.py relies on
        # them to auto-set and highlight the next step's inputs.
        return _points('Moving_point_cloud'), _points('Fixed_point_cloud')

    def run_point_cloud_registration_and_warping(self, **kwargs):
        self.calls['run_point_cloud_registration_and_warping'].append(kwargs)
        warped = Image(np.zeros(SHAPE), name=kwargs['Moving_Image'].name + '_warped')
        return [warped], _points('transformed_points')


@pytest.fixture
def viewer(qtbot, monkeypatch):
    import napari.viewer

    model = ViewerModel()
    monkeypatch.setattr(napari.viewer, 'current_viewer', lambda: model)
    return model


@pytest.fixture
def pipeline(monkeypatch):
    stubs = Pipeline()
    for name in stubs.calls:
        monkeypatch.setattr(widget_components, name, getattr(stubs, name))
    return stubs


@pytest.fixture
def errors(monkeypatch):
    messages = []
    for module in (fixed_segmentation, moving_segmentation, point_cloud_sampling,
                   registration_warping, run_registration):
        if hasattr(module, 'show_error'):
            monkeypatch.setattr(module, 'show_error', messages.append)
    return messages


@pytest.fixture
def images(viewer):
    """An FM and an EM image in the viewer, added before any widget is
    built so its Layer dropdowns pick them up."""
    rng = np.random.default_rng(0)
    fm = viewer.add_image(rng.random(SHAPE), name='FM')
    em = viewer.add_image(rng.random(SHAPE), name='EM')
    return fm, em


@pytest.fixture
def segmentations(viewer):
    fm_seg = viewer.add_labels(_labels_array(), name='FM_seg_existing')
    em_seg = viewer.add_labels(_labels_array(), name='EM_seg_existing')
    return fm_seg, em_seg


def _wait_for_layer(qtbot, viewer, name):
    qtbot.waitUntil(lambda: name in viewer.layers, timeout=TIMEOUT_MS)


def _is_highlighted(field):
    return field.native.styleSheet() != ''


# --- Split widgets -----------------------------------------------------------

def test_split_em_segmentation_adds_layer_and_passes_parameters(qtbot, viewer, pipeline, images):
    __, em = images
    gui = fixed_segmentation_widget()
    gui.em_seg_axis.value = True
    gui.em_segmentation_backend.value = 'MitoNet (empanada-dl)'

    gui(Fixed_Image=em)

    _wait_for_layer(qtbot, viewer, 'EM_segmentation')
    assert isinstance(viewer.layers['EM_segmentation'], Labels)
    (kwargs,) = pipeline.calls['run_fixed_segmentation']
    assert kwargs['Fixed_Image'] is em
    assert kwargs['em_seg_axis'] is True
    assert kwargs['em_segmentation_backend'] == 'MitoNet (empanada-dl)'


def test_split_fm_segmentation_adds_layer_and_passes_parameters(qtbot, viewer, pipeline, images):
    fm, __ = images
    gui = moving_segmentation_widget()
    gui.log_sigma.value = 4.5
    gui.log_threshold.value = 2.0

    gui(Moving_Image=fm)

    _wait_for_layer(qtbot, viewer, 'FM_segmentation')
    (kwargs,) = pipeline.calls['run_moving_segmentation']
    assert kwargs['Moving_Image'] is fm
    assert kwargs['log_sigma'] == 4.5
    assert kwargs['log_threshold'] == 2.0


def test_split_point_cloud_sampling_adds_both_point_clouds(qtbot, viewer, pipeline, segmentations):
    fm_seg, em_seg = segmentations
    gui = point_cloud_sampling_widget()
    gui.voxel_size.value = 42

    gui(Moving_Segmentation=fm_seg, Fixed_Segmentation=em_seg)

    _wait_for_layer(qtbot, viewer, 'Fixed_point_cloud')
    assert 'Moving_point_cloud' in viewer.layers
    (kwargs,) = pipeline.calls['run_point_cloud_sampling']
    assert kwargs['voxel_size'] == 42


def test_split_registration_warping_adds_warped_image(qtbot, viewer, pipeline, images):
    fm, em = images
    moving_points = viewer.add_layer(_points('Moving_point_cloud'))
    fixed_points = viewer.add_layer(_points('Fixed_point_cloud'))
    gui = registration_warping_widget()
    gui.registration_algorithm.value = 'Affine CPD'

    gui(Moving_Image=fm, Fixed_Image=em, Moving_Points=moving_points, Fixed_Points=fixed_points)

    _wait_for_layer(qtbot, viewer, 'FM_warped')
    assert 'transformed_points' in viewer.layers
    (kwargs,) = pipeline.calls['run_point_cloud_registration_and_warping']
    assert kwargs['registration_algorithm'] == 'Affine CPD'


@pytest.mark.xfail(strict=True, reason='#50: split EM widget crashes on no segmentation')
def test_split_em_segmentation_reports_no_segmentation(qtbot, viewer, pipeline, errors, images):
    __, em = images
    pipeline.fixed_result = 'No segmentation'
    gui = fixed_segmentation_widget()

    gui(Fixed_Image=em)

    qtbot.waitUntil(lambda: bool(errors), timeout=TIMEOUT_MS)
    assert 'EM_segmentation' not in viewer.layers


@pytest.mark.xfail(strict=True, reason='#50: split FM widget crashes on no segmentation')
def test_split_fm_segmentation_reports_no_segmentation(qtbot, viewer, pipeline, errors, images):
    fm, __ = images
    pipeline.moving_result = 'No segmentation'
    gui = moving_segmentation_widget()

    gui(Moving_Image=fm)

    qtbot.waitUntil(lambda: bool(errors), timeout=TIMEOUT_MS)
    assert 'FM_segmentation' not in viewer.layers


# --- Run Registration: the Register button -----------------------------------

def _assert_also_reraised(raised, exc_type):
    """Register connects its segmentation workers' `errored` handlers
    after creating them, not through thread_worker(connect=...), so
    superqt also re-raises the exception in the main thread. In napari,
    that means the user sees the error twice: once from show_error and
    once as napari's own traceback notification. Pin that behaviour here,
    so a change to it is noticed.
    """
    assert [type(exc) for __, exc, __ in raised] == [exc_type]


def _run_registration(images):
    fm, em = images
    gui = make_run_registration()
    gui.Moving_Image.value = fm
    gui.Fixed_Image.value = em
    return gui


def test_register_runs_every_step_and_adds_warped_image(qtbot, viewer, pipeline, images):
    gui = _run_registration(images)
    gui.registration_voxel_size.value = 42
    gui.warping_output_resolution.value = 'EM pixel grid (legacy)'

    gui()

    _wait_for_layer(qtbot, viewer, 'FM_warped')
    assert all(len(calls) == 1 for calls in pipeline.calls.values())
    assert pipeline.calls['run_point_cloud_sampling'][0]['voxel_size'] == 42
    warp_kwargs = pipeline.calls['run_point_cloud_registration_and_warping'][0]
    assert warp_kwargs['warping_output_resolution'] == 'EM pixel grid (legacy)'


def test_register_reports_em_failure_and_does_not_register(qtbot, viewer, pipeline, errors, images):
    """#23: a failed segmentation used to leave Register silently hung."""
    pipeline.fixed_error = ValueError('boom')
    gui = _run_registration(images)

    with qtbot.capture_exceptions() as raised:
        gui()
        qtbot.waitUntil(lambda: any('EM segmentation failed' in m for m in errors), timeout=TIMEOUT_MS)
        qtbot.wait(200)

    assert pipeline.calls['run_point_cloud_sampling'] == []
    _assert_also_reraised(raised, ValueError)


def test_register_reports_segment_flow_failure(qtbot, viewer, pipeline, errors, images):
    """#53: Segment-Flow's errors used to subclass RuntimeError, which
    superqt's generator workers swallow, so Register silently hung."""
    from napari_clemreg.clemreg.segment_flow_segmentation import SegmentFlowNotAvailable

    pipeline.fixed_error = SegmentFlowNotAvailable('Nextflow not found')
    gui = _run_registration(images)

    with qtbot.capture_exceptions() as raised:
        gui()
        qtbot.waitUntil(lambda: any('Nextflow not found' in m for m in errors), timeout=TIMEOUT_MS)
        qtbot.wait(200)

    assert pipeline.calls['run_point_cloud_sampling'] == []
    _assert_also_reraised(raised, SegmentFlowNotAvailable)


def test_register_reports_runtime_error_from_segmentation(qtbot, viewer, pipeline, errors, images):
    """#53: any other RuntimeError (from numpy, torch, ...) must be
    reported too, not swallowed."""
    from napari_clemreg.clemreg.exceptions import ClemregError

    pipeline.fixed_error = RuntimeError('CUDA out of memory')
    gui = _run_registration(images)

    with qtbot.capture_exceptions() as raised:
        gui()
        qtbot.waitUntil(lambda: any('CUDA out of memory' in m for m in errors), timeout=TIMEOUT_MS)
        qtbot.wait(200)

    assert pipeline.calls['run_point_cloud_sampling'] == []
    _assert_also_reraised(raised, ClemregError)


def test_register_surfaces_runtime_error_from_registration(qtbot, viewer, pipeline, images):
    """#53: a RuntimeError in the registration worker (e.g. from
    open3d) must reach the user rather than end the run silently."""
    from napari_clemreg.clemreg.exceptions import ClemregError

    pipeline.sampling_error = RuntimeError('open3d failed')
    gui = _run_registration(images)

    with qtbot.capture_exceptions() as raised:
        gui()
        qtbot.waitUntil(lambda: bool(raised), timeout=TIMEOUT_MS)

    assert [type(exc) for __, exc, __ in raised] == [ClemregError]
    assert 'open3d failed' in str(raised[0][1])
    assert 'FM_warped' not in viewer.layers


def test_register_reports_no_segmentation(qtbot, viewer, pipeline, errors, images):
    """#25: 'No segmentation' used to crash with an unrelated AttributeError."""
    pipeline.moving_result = 'No segmentation'
    gui = _run_registration(images)

    with qtbot.capture_exceptions() as raised:
        gui()
        qtbot.waitUntil(lambda: any('No mitochondria found' in m for m in errors), timeout=TIMEOUT_MS)

    assert pipeline.calls['run_point_cloud_sampling'] == []
    _assert_also_reraised(raised, ValueError)


# --- Run Registration: the "Run this step" buttons ---------------------------

def test_em_step_auto_sets_and_highlights_next_input(qtbot, viewer, pipeline, images):
    gui = _run_registration(images)

    gui.run_em_segmentation_button.clicked.emit()

    _wait_for_layer(qtbot, viewer, 'EM_segmentation')
    qtbot.waitUntil(lambda: gui.run_em_segmentation_button.native.isEnabled(), timeout=TIMEOUT_MS)
    assert gui.Fixed_Segmentation.value is viewer.layers['EM_segmentation']
    assert _is_highlighted(gui.Fixed_Segmentation)


def test_fm_step_auto_sets_and_highlights_next_input(qtbot, viewer, pipeline, images):
    gui = _run_registration(images)

    gui.run_fm_segmentation_button.clicked.emit()

    _wait_for_layer(qtbot, viewer, 'FM_segmentation')
    assert gui.Moving_Segmentation.value is viewer.layers['FM_segmentation']
    assert _is_highlighted(gui.Moving_Segmentation)


def test_point_cloud_step_runs_from_existing_segmentations(qtbot, viewer, pipeline, images, segmentations):
    fm_seg, em_seg = segmentations
    gui = _run_registration(images)
    gui.Moving_Segmentation.value = fm_seg
    gui.Fixed_Segmentation.value = em_seg

    gui.run_point_cloud_sampling_button.clicked.emit()

    _wait_for_layer(qtbot, viewer, 'Fixed_point_cloud')
    (kwargs,) = pipeline.calls['run_point_cloud_sampling']
    assert kwargs['Moving_Segmentation'] is fm_seg
    assert kwargs['Fixed_Segmentation'] is em_seg
    assert gui.Moving_Points.value is viewer.layers['Moving_point_cloud']
    assert _is_highlighted(gui.Fixed_Points)


def test_registration_step_adds_warped_image(qtbot, viewer, pipeline, images):
    gui = _run_registration(images)
    gui.Moving_Points.value = viewer.add_layer(_points('Moving_point_cloud'))
    gui.Fixed_Points.value = viewer.add_layer(_points('Fixed_point_cloud'))

    gui.run_registration_and_warping_button.clicked.emit()

    _wait_for_layer(qtbot, viewer, 'FM_warped')


def test_step_button_reports_error_and_is_re_enabled(qtbot, viewer, pipeline, errors, images):
    pipeline.fixed_error = RuntimeError('boom')
    gui = _run_registration(images)

    gui.run_em_segmentation_button.clicked.emit()

    qtbot.waitUntil(lambda: any('EM segmentation failed' in m for m in errors), timeout=TIMEOUT_MS)
    assert gui.run_em_segmentation_button.native.isEnabled()


# --- Split and combined widgets pass the same parameters ---------------------

def _without_layers(kwargs):
    return {k: v for k, v in kwargs.items() if not hasattr(v, 'data')}


def test_split_and_combined_sampling_receive_the_same_parameters(qtbot, viewer, pipeline, images, segmentations):
    """With default settings, the split Point Cloud Sampling widget and
    Run Registration's step button must call the pipeline identically,
    so the two can't drift apart."""
    fm_seg, em_seg = segmentations
    point_cloud_sampling_widget()(Moving_Segmentation=fm_seg, Fixed_Segmentation=em_seg)
    qtbot.waitUntil(lambda: len(pipeline.calls['run_point_cloud_sampling']) == 1, timeout=TIMEOUT_MS)

    gui = _run_registration(images)
    gui.Moving_Segmentation.value = fm_seg
    gui.Fixed_Segmentation.value = em_seg
    gui.run_point_cloud_sampling_button.clicked.emit()
    qtbot.waitUntil(lambda: len(pipeline.calls['run_point_cloud_sampling']) == 2, timeout=TIMEOUT_MS)

    split, combined = pipeline.calls['run_point_cloud_sampling']
    assert _without_layers(split) == _without_layers(combined)


def test_split_and_combined_registration_receive_the_same_parameters(qtbot, viewer, pipeline, images):
    fm, em = images
    moving_points = viewer.add_layer(_points('Moving_point_cloud'))
    fixed_points = viewer.add_layer(_points('Fixed_point_cloud'))
    registration_warping_widget()(Moving_Image=fm, Fixed_Image=em,
                                  Moving_Points=moving_points, Fixed_Points=fixed_points)
    calls = pipeline.calls['run_point_cloud_registration_and_warping']
    qtbot.waitUntil(lambda: len(calls) == 1, timeout=TIMEOUT_MS)

    gui = _run_registration(images)
    gui.Moving_Points.value = moving_points
    gui.Fixed_Points.value = fixed_points
    gui.run_registration_and_warping_button.clicked.emit()
    qtbot.waitUntil(lambda: len(calls) == 2, timeout=TIMEOUT_MS)

    split, combined = calls
    assert _without_layers(split) == _without_layers(combined)


# --- Known, open GUI bugs -----------------------------------------------------

@pytest.mark.xfail(strict=True, raises=NameError, reason='#47: Save parameters crashes Register')
def test_register_saves_parameters_to_json(qtbot, viewer, pipeline, images, tmp_path):
    path = tmp_path / 'params.json'
    gui = _run_registration(images)
    gui.save_json.value = True
    gui.save_json_path.value = path

    gui()

    assert json.loads(path.read_text())['log_sigma'] == gui.log_sigma.value


@pytest.mark.xfail(strict=True, reason='#47: Parameters from JSON never reads the file')
def test_register_loads_parameters_from_json(qtbot, viewer, pipeline, images, tmp_path):
    path = tmp_path / 'params.json'
    path.write_text(json.dumps({'log_sigma': 7.0}))
    gui = _run_registration(images)
    gui.params_from_json.value = True
    gui.load_json_file.value = path

    gui()

    qtbot.waitUntil(lambda: pipeline.calls['run_moving_segmentation'], timeout=TIMEOUT_MS)
    assert pipeline.calls['run_moving_segmentation'][0]['log_sigma'] == 7.0


@pytest.mark.xfail(strict=True, reason='#48: three-axis option shown for Segment-Flow, where it does nothing')
@pytest.mark.parametrize('factory', [make_run_registration, fixed_segmentation_widget],
                         ids=['run_registration', 'split_em_segmentation'])
def test_three_axis_option_unavailable_with_segment_flow(qtbot, factory):
    gui = factory()
    gui.em_segmentation_backend.value = 'MitoNet (empanada-dl)'
    gui.em_segmentation_backend.value = 'MitoNet (Segment-Flow)'

    assert gui.em_seg_axis.native.isHidden() or not gui.em_seg_axis.enabled


@pytest.mark.xfail(strict=True, reason='#49: Voxel Size sits under Point Cloud Registration')
def test_voxel_size_is_in_point_cloud_sampling_section(qtbot):
    from superqt import QCollapsible

    gui = make_run_registration()
    voxel_size = gui.registration_voxel_size.native
    (section,) = [s for s in gui.native.findChildren(QCollapsible) if s.isAncestorOf(voxel_size)]

    assert section.text() == 'Point Cloud Sampling'

