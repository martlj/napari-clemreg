#!/usr/bin/env python3
# coding: utf-8

specs = {
    'z_min':{'widget_type': 'SpinBox',
           'label': 'Minimum z value for masking',
           "min": 0, "max": 10, "step": 1,
           'value': 0},

    'z_max':{'widget_type': 'SpinBox',
           'label': 'Maximum z value for masking',
           "min": 0, "max": 10, "step": 1,
           'value': 0},

    'registration_algorithm':{'label': 'Registration Algorithm',
                            'widget_type': 'ComboBox',
                            'choices': ["BCPD", "Rigid CPD"],
                            'choices': ["BCPD", "Rigid CPD", "Affine CPD"],
                            'value': 'Rigid CPD',
                            'tooltip': 'Speed: Rigid CPD > Affine CPD > BCPD'},

    'params_from_json':{'label': 'Parameters from JSON',
                      'widget_type': 'CheckBox',
                      'value': False},

    'load_json_file':{'label': 'Select Parameter File',
                    'widget_type': 'FileEdit',
                    'mode': 'r',
                    'filter': '*.json'},

    # Both choices run the exact same MitoNet model -- only how it's
    # invoked differs -- so both names lead with "MitoNet" to make that
    # explicit rather than reading like two different models.
    #
    # Default is MitoNet (Segment-Flow), not MitoNet (empanada-dl) --
    # empanada-dl is unmaintained and its numpy==1.22 pin means the
    # `empanada` extra currently cannot install at all on Python 3.11
    # (see issue #5), while Segment-Flow has been verified end-to-end
    # against real production data (see #5/#16). This is purely about
    # which one can actually work out of the box today.
    'em_segmentation_backend':{'label': 'EM Segmentation Backend',
                             'widget_type': 'ComboBox',
                             'choices': ['MitoNet (Segment-Flow)', 'MitoNet (empanada-dl)'],
                             'value': 'MitoNet (Segment-Flow)',
                             'tooltip': 'Both options run the same MitoNet model. '
                                        'MitoNet (Segment-Flow) shells out to a Nextflow '
                                        'pipeline and requires Nextflow and Conda on PATH. '
                                        'MitoNet (empanada-dl) requires the empanada-dl extra '
                                        '(see issue #5) -- currently uninstallable on Python 3.11.'},

    'log_sigma':{'label': 'Sigma',
               'widget_type': 'FloatSpinBox',
               'min': 0.5, 'max': 20, 'step': 0.5,
               'value': 3},

    'log_threshold':{'label': 'Threshold',
                   'widget_type': 'FloatSpinBox',
                   'min': 0, 'max': 20, 'step': 0.1,
                   'value': 1.2},

    'filter_segmentation':{'text': 'Apply size filter to segmentation',
                     'widget_type': 'CheckBox',
                     'value': False},

    'filter_size_lower':{'label': 'Lower filter threshold',
                    'widget_type': 'SpinBox',
                    'min': 0, 'max': 100, 'step': 1,
                    'value': 5},

    'filter_size_upper':{'label': 'Upper filter threshold',
                    'widget_type': 'SpinBox',
                    'min': 0, 'max': 100, 'step': 1,
                    'value': 95},

    'point_cloud_sampling_frequency':{'label': 'Sampling Frequency',
                                    'widget_type': 'SpinBox',
                                    'min': 1, 'max': 100, 'step': 1,
                                    'value': 3},

    'point_cloud_sigma':{'label': 'Sigma',
                       'widget_type': 'FloatSpinBox',
                       'min': 0, 'max': 10, 'step': 0.1,
                       'value': 1.0},

    'registration_voxel_size':{'label': 'Voxel Size',
                             'widget_type': 'SpinBox',
                             'min': 1, 'max': 1000, 'step': 1,
                             'value': 15},

    'registration_max_iterations':{'label': 'Maximum Iterations',
                                 'widget_type': 'SpinBox',
                                 'min': 1, 'max': 1000, 'step': 1,
                                 'value': 50},

    'warping_interpolation_order':{'label': 'Interpolation Order',
                                 'widget_type': 'SpinBox',
                                 'min': 0, 'max': 5, 'step': 1,
                                 'value': 1},

    'warping_approximate_grid':{'label': 'Approximate Grid',
                              'widget_type': 'SpinBox',
                              'min': 1, 'max': 10, 'step': 1,
                              'value': 5},

    'warping_sub_division_factor':{'label': 'Sub-division Factor',
                                 'widget_type': 'SpinBox',
                                 'min': 1, 'max': 10, 'step': 1,
                                 'value': 1},

    # Default keeps the warped FM output near its own native pixel size
    # rather than forcing it onto EM's (usually much finer) grid --
    # overlay in the viewer is handled via the layer's `scale`, not
    # matching pixel counts. 'EM pixel grid (legacy)' reproduces the
    # pre-existing behaviour, for anyone who wants the FM data actually
    # resampled onto EM's own pixel grid (e.g. for pixel-exact export).
    'warping_output_resolution':{'label': 'Output Pixel Size',
                               'widget_type': 'ComboBox',
                               'choices': ['Native LM resolution', 'EM pixel grid (legacy)'],
                               'value': 'Native LM resolution',
                               'tooltip': 'Native LM resolution (default): warp the FM image onto '
                                          'a pixel grid close to its own native resolution -- lighter, '
                                          'avoids unnecessary upsampling. The result is placed correctly '
                                          'relative to the EM image in the viewer via the layer\'s scale. '
                                          'EM pixel grid (legacy): resample the warped result onto the '
                                          'EM image\'s own (finer) pixel grid.'},

    'save_json':{'label': 'Save parameters',
               'widget_type': 'CheckBox',
               'value': False},

    'save_json_path':{'label': 'Path to save parameters',
                   'widget_type': 'FileEdit',
                   'mode': 'w',
                   'filter': '*.json'},

    'visualise_intermediate_results':{'label': 'Visualise Intermediate Results',
                                    'widget_type': 'CheckBox',
                                    'value': True
                                    },

    'moving_image_pixelsize_xy':{'label': 'FM Pixel size (xy)',
                                    'widget_type': 'QuantityEdit',
                                    'value': '0 nanometer'
                                    },

    'moving_image_pixelsize_z':{'label': 'FM Pixel size (z)',
                                    'widget_type': 'QuantityEdit',
                                    'value': '0 nanometer'
                                    },

    'fixed_image_pixelsize_xy':{'label': 'EM Pixel size (xy)',
                                    'widget_type': 'QuantityEdit',
                                    'value': '0 nanometer'
                                    },

    'fixed_image_pixelsize_z':{'label': 'EM Pixel size (z)',
                                    'widget_type': 'QuantityEdit',
                                    'value': '0 nanometer'
                                    },

    'registration_direction':{'label': 'Registration direction',
                                    'widget_type': 'RadioButtons',
                                    'choices': [u'FM \u2192 EM', u'EM \u2192 FM'],
                                    'value': u'FM \u2192 EM'
                                    },

    'Moving_Image':{'label': 'Fluorescence Microscopy Image (FM)'},

    'Fixed_Image':{'label': 'Electron Microscopy Image (EM)'},

    'Moving_Segmentation':{'label': 'Fluorescence Microscopy (FM) Segmentation'},

    'Fixed_Segmentation':{'label': 'Electron Microscopy (EM) Segmentation'},

    'Moving_Points':{'label': 'Fluorescence Microscopy (FM) Point Cloud'},

    'Fixed_Points':{'label': 'Electron Microscopy (EM) Point Cloud'},

    # "Run this step" buttons for the combined Run Registration widget's
    # per-stage collapsible sections -- run just that stage using
    # whichever layers currently sit in its own inputs (auto-set from a
    # previous step, manually picked, or pre-existing), independent of
    # the main "Register" call button which always runs the full
    # pipeline from Moving_Image/Fixed_Image onward. Not consumed inside
    # make_run_registration()'s own body -- wired to their .clicked
    # signal in on_init(), same as this widget's other button-like
    # fields (widget_header Labels are similarly unused in the body).
    'run_em_segmentation_button':{'widget_type': 'PushButton', 'text': 'Run this step'},

    'run_fm_segmentation_button':{'widget_type': 'PushButton', 'text': 'Run this step'},

    'run_point_cloud_sampling_button':{'widget_type': 'PushButton', 'text': 'Run this step'},

    'run_registration_and_warping_button':{'widget_type': 'PushButton', 'text': 'Run this step'}
}
