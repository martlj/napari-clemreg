import napari
from magicgui import magic_factory
from napari.layers import Image, Labels
from napari.utils.notifications import show_error
from napari.qt.threading import thread_worker

from ..clemreg.on_init_specs import specs
from ..clemreg._qt_layout import wrap_in_scroll_area

@magic_factory(layout='vertical', call_button='Segment',
               widget_header={'widget_type': 'Label',
                              'label': f'<h2 text-align="left">Electron Microscopy Segmentation</h2>'},
               Fixed_Image=specs['Fixed_Image'],
               em_seg_axis=specs['em_seg_axis'],
               em_segmentation_backend=specs['em_segmentation_backend'],
               )
def fixed_segmentation_widget(viewer: 'napari.viewer.Viewer',
                              widget_header,
                              Fixed_Image: Image,
                              em_seg_axis: bool,
                              em_segmentation_backend: str
                              ):
    """
    This widget takes an EM image as input and performs
    segmentation of the mitochondria on it using the
    Empanada MitoNet model.

    Parameters
    ----------
    viewer :
        napari viewer
    widget_header : str
        Heading of the widget
    Fixed_Image :
        The EM Image
    em_seg_axis :
        Option to run segmentation across three axis
    em_segmentation_backend :
        Which EM segmentation backend to use: the bundled empanada-dl
        (MitoNet), or Crick's AI-on-Demand (Segment-Flow) pipeline

    Returns
    -------
    napari Labels layer containing the segmentation of mitochondria
    produced by the MitoNet model.

    """
    import numpy as np

    @thread_worker
    def _run_fixed_thread(**kwargs):
        from ..clemreg.widget_components import run_fixed_segmentation
        #Increasing levels of CLAHE

        seg_volume = run_fixed_segmentation(**kwargs)

        return Labels(seg_volume.astype(np.int64), **{'name': 'EM_segmentation', 'metadata': Fixed_Image.metadata})

    def _add_data(return_value):
        if isinstance(return_value, str):
            show_error('WARNING: No mitochondria in Fixed Image')
            return

        viewer.add_layer(return_value)

    if Fixed_Image is None:
        show_error("WARNING: You have not inputted both a fixed and moving image")
        return

    if len(Fixed_Image.data.shape) != 3:
        show_error("WARNING: Your Fixed_Image must be 3D, you're current input has a shape of {}".format(
            Fixed_Image.data.shape))
        return
    elif len(Fixed_Image.data.shape) == 3 and (Fixed_Image.data.shape[2] == 3 or Fixed_Image.data.shape[2] == 4):
        show_error("WARNING: YOUR fixed_image is RGB, your input must be grayscale and 3D")
        return

    worker_fixed = _run_fixed_thread(Fixed_Image=Fixed_Image,
                                     em_seg_axis=em_seg_axis,
                                     em_segmentation_backend=em_segmentation_backend)
    worker_fixed.returned.connect(_add_data)
    worker_fixed.start()


def fixed_segmentation_dock_widget(napari_viewer: 'napari.viewer.Viewer'):
    """The actual napari-docked widget -- wraps fixed_segmentation_widget()
    in a QScrollArea so the panel has a bounded height/width, matching
    AIoD's own napari plugin's approach (verified against its real
    source). This widget is small (3 fields), so there's no burst-reveal
    lag to fix here, but the same scroll-bounding is applied for
    consistency across every widget in this plugin.
    """
    # magic_factory's __call__ treats kwargs as widget-option overrides,
    # not runtime values, so call with no args and let its own
    # Viewer-typed-parameter auto-injection resolve the current viewer.
    gui = fixed_segmentation_widget()
    return wrap_in_scroll_area(gui.native)
