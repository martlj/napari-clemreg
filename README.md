

<h1 align="center">
napari-clemreg

</h1>

### An automated point cloud based registration algorithm for correlative light and volume electron microscopy
<p align="center">
    <a href="https://www.nature.com/articles/s41592-025-02794-0"><img alt="Paper" src="https://img.shields.io/badge/paper-Nat._Methods-orange"></a>
    <a href="https://github.com/martlj/napari-clemreg/actions/workflows/test.yml"><img alt="Tests" src="https://github.com/martlj/napari-clemreg/actions/workflows/test.yml/badge.svg"></a>
    <a href="https://pypi.org/project/napari-clemreg"><img alt="PyPI" src="https://img.shields.io/pypi/v/napari-clemreg.svg?color=green"></a><a href="https://pypistats.org/packages/napari-clemreg"><img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/napari-clemreg"></a>
    <a href="https://github.com/krentzd/napari-clemreg/"><img alt="github" src="https://img.shields.io/github/stars/krentzd/napari-clemreg?style=social"></a>
    <a href="https://github.com/krentzd/napari-clemreg/"><img alt="github" src="https://img.shields.io/github/forks/krentzd/napari-clemreg?style=social"></a>
</p>

## Overview
CLEM-Reg fully automates the registration step for vCLEM datasets by first segmenting mitochondria in both image modalities, sampling point
clouds from these segmentations and registering them. Once registered, the point cloud alignment is used to warp the fluorescence microscopy onto the 
volume electron microscopy. 
![width=200](docs%2Fimages%2Fclemreg_algorithm.png)


## Installation
### Local Installation

To install `napari-clemreg` it is recommended to create a fresh [conda] environment with Python 3.9:

```
conda create -n clemreg_env python=3.9
```
Now we must activate the conda environment.

``` 
conda activate clemreg_env
```

Next, install `napari` with the following command via [pip]: 

```
pip install "napari[all]"
```

Then, `napari-clemreg` can be installed with:
```
pip install napari-clemreg
```

Finally, to run napari run the following.
```
napari
```

When installing `napari-clemreg` on a Windows machine, the following error might appear:
```
ImportError: DLL load failed while importing pybind: A dynamic link library (DLL) initialization routine failed.
```
This is `open3d` (a dependency), which needs both the [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) and real GPU-backed OpenGL 4.1+ support — it won't import in a virtual machine or remote desktop without GPU passthrough (confirmed against [isl-org/Open3D#4468](https://github.com/isl-org/Open3D/issues/4468) and [#5328](https://github.com/isl-org/Open3D/issues/5328); this is also why this project's CI only tests Linux and macOS, not Windows).

[![Watch the video](docs%2Fimages%2Fclemreg_installation_thumbnail.png)](https://youtu.be/ZN68q9OU59s)

### Development Installation (this fork)

This fork (`martlj/napari-clemreg`) is being actively modernised — see [docs/napari-clemreg-modernisation-plan.md](docs/napari-clemreg-modernisation-plan.md) for the full plan. **All of this work lives on the `feature/split-clemreg-core` branch, not `main`** — the default branch you'd get from a plain `git clone` doesn't have it yet.

If you already have this repo cloned, switch to that branch rather than cloning again (cloning into an existing checkout creates a confusing nested copy):
```
git fetch origin
git checkout feature/split-clemreg-core
```
Otherwise, clone it directly onto that branch:
```
git clone -b feature/split-clemreg-core https://github.com/martlj/napari-clemreg.git
cd napari-clemreg
```

This branch now requires **Python 3.11+**. `empanada-dl` (needed for the bundled EM Segmentation widget) currently blocks a normal install on Python 3.11 — it hard-pins `numpy==1.22`, which has no Python 3.11 wheels (tracked in [issue #5](https://github.com/martlj/napari-clemreg/issues/5)). Until that's resolved, install everything else and skip it.

Using [`uv`](https://docs.astral.sh/uv/) (recommended — fast, and installs the Python version for you if needed):

```
uv venv --python 3.11
source .venv/bin/activate   # .venv\Scripts\activate on Windows
uv pip install typing_extensions setuptools packaging pint numpy scipy "scikit-image>=0.22" "magicgui>=0.8.3" "napari>=0.6" open3d probreg transforms3d tqdm h5py matplotlib imageio tifffile torch connected-components-3d pyqt5
uv pip install -e . --no-deps
```

Or with plain `pip` (needs an existing Python 3.11+ interpreter, e.g. via conda — `conda create -n clemreg_dev python=3.11 && conda activate clemreg_dev`), same package list:

```
pip install typing_extensions setuptools packaging pint numpy scipy "scikit-image>=0.22" "magicgui>=0.8.3" "napari>=0.6" open3d probreg transforms3d tqdm h5py matplotlib imageio tifffile torch connected-components-3d pyqt5
pip install -e . --no-deps
```

Either way, this gives you a working install of everything **except** the bundled EM Segmentation (MitoNet/empanada) widget. For EM segmentation, use [AI-on-Demand instead](#using-ai-on-demand-aiod-for-em-segmentation) — see Usage below.

### Docker Container
If you would like to run `napari-clemreg` in a docker container instead of installing it as above, please follow the instructions in our [Docker guide](docker_guide.md)

[![Watch the video](docs%2Fimages%2Fclemreg_docker_installation_guide.png)](https://youtu.be/2GRB99UlP6g)

## Usage
CLEM-reg is the combination of 5 main steps, electron microscopy segmentation, fluorescence microscopy segmentation,
point cloud sampling, point cloud registration and image warping. These 5 steps 
can be run all at once using the run registration widget.
Alternatively, they can be run individually with the numbered widgets.

![clemreg_widget_options.png](docs%2Fimages%2Fnapari_dropdown.png)

### Run Registration

![registration_labels.png](docs%2Fimages%2Fclemreg_params.png)

1. **Fluorescence Microscopy Image (FM)** - Here you select the layer with the fluorescence microscopy image.
2. **FM Pixel Size (xy)** - Here you can set the xy pixel size of your FM image and its corresponding unit.
3. **FM Pixel Size (z)** - Here you can set the z pixel size of your FM image and its corresponding unit.
4. **Mask ROI** - Here you can select a mask layer which will be used to crop the resulting segmentation mask in the FM.
5. **Electron Microscopy (EM)** - Here you can select the layer with the electron microscopy image.
6. **EM Pixel Size (xy)** - Here you can set the xy pixel size of your EM image and its corresponding unit.
7. **EM Pixel Size (z)** - Here you can set the z pixel size of your EM image and its corresponding unit.
8. **Registration Algorithm** - Here you can decide which type of registration algorith will be used for the registration of inputted LM and EM. In terms of speed of each algorithm the following is the generally true, Rigid CPD > Affine CPD > BCPD.
9. **Parameters from JSON** - Here you can select a JSON file containing the parameters for the registration.
10. **Parameters custom** - If you select this, you will be able to edit the default parameters.
11. **MitoNet Segmentation Parameters** - Here are the advanced options for the segmentation of the mitochondria in the EM data.
    1. **Prediction Across Three Axis** - By selecting this option MitoNet will run segmentation across all three axis of the EM volume and then these three predictions will be aggregate.
12. **LoG Segmentation Parameters** - Here are the advanced options for the segmentation of the mitochondria in the LM data.
    1. **Sigma** - Sigma value for the Laplacian of Gaussian filter.
    2. **Threshold** - Threshold value for the segmenting the LM data.
    3. **Apply size filter to segmentation** - If you select this, you can then select a lower and upper volume threshold to filter out spurious segmentation.
13. **Point Cloud Sampling** - Here are the advanced options for the point cloud sampling of the segmentations of the LM and EM data.
    1. **Sampling Frequency** - Frequency of point sampling from the fixed and moving segmentation. The greater the value the more points in the point cloud.
    2. **Voxel Size** - The size voxel size of each point. Smaller the size the less memory consumption.
    3. **Sigma** - Sigma value for the canny edge filter.
14. **Point Cloud Registration** - Here are the advanced options for the registration of the point clouds of both the LM and EM data.
    1. Maximum Iterations - The number of round of point cloud registration. If too small it won't converge on an opitmal registration.
15. **Image Warping** - Here are the advanced options for the image warping of the moving images.
    1. Interpolation Order - The order of the spline interpolation.
    2. Aproximate Grid - Controls the "resolution" of the grid onto which you're warping. A higher value reduces the step size between coordinates.
    3. Sub-division Factor - Controls the size of the chunk when applying the warping.
16. **Save Parameters** - Here you can select the option to save the advanced options you've selected to a JSON file which can be kept for reproducibility as well as running the registration again.
17. **Visualise Intermediate Results** - Here you can select to view the outputs of each step as they are completed.
18. **Registration direction** - Here you can select which of the modalities will be registered to the other. Either EM to FM or FM to EM.

[![Watch the video](docs%2Fimages%2Fclem_reg_tutorial_thumbnail.png)](https://youtu.be/ud3zTLgl8Ks)

### Split Registration
As well as being able to run all the steps of CLEM-reg in one widget (the `Run registration` widget),
you are also able to do all these steps independently using the `Split Registration` functionality. 

There are four separate widgets that encapsulate the 5 steps of CLEM-reg each of which have
their own unique input and output:
1. `Electron Micrscopy (EM) Segmentation` 
   - **Input**: EM Image
   - **Output**: EM Segmentation
2. `Fluorescence Microscopy (FM) Segmentation`
   - **Input**: LM Image
   - **Output**: LM Segmentation
3. `Point Cloud Sampling`
   - **Input**: LM Segmentation & EM Segmentation
   - **Output**: LM Point Cloud & LM Point Cloud
4. `Point Cloud Registration & Image Warping`
   - **Input**: EM Image, LM Image, LM Point Cloud & EM Point Cloud
   - **Output**: Registered LM Image, Registered LM Point Cloud

[![Watch the video](docs%2Fimages%2Fclemreg_split_registration_thumbnail.png)](https://youtu.be/cypDti0UUwY)

### Using AI-on-Demand (AIoD) for EM Segmentation

The bundled `Electron Microscopy (EM) Segmentation` widget uses MitoNet via `empanada-dl`, a dependency that is no longer actively maintained and can be difficult to install alongside a modern Python/napari setup. As an alternative, you can run MitoNet through the Crick's [AI-on-Demand (AIoD)](https://franciscrickinstitute.github.io/aiod_docs/) project instead, and feed its output straight into CLEM-Reg's own `Point Cloud Sampling` widget — no changes to the rest of the CLEM-Reg workflow are needed.

1. Install the [`aiod_napari`](https://github.com/FrancisCrickInstitute/aiod_napari) plugin alongside `napari-clemreg` in the same environment (it additionally requires [Nextflow](https://www.nextflow.io/) and Conda to actually run models — see AIoD's [Prerequisites](https://franciscrickinstitute.github.io/aiod_docs/sections/getting_started/#prerequisites)).
2. Open `Plugins → AI OnDemand → Inference`, point it at your EM image, and select the `empanada` model (MitoNet). AIoD handles splitting the volume, running the model — locally or on HPC, depending on profile — caching results, and loading the resulting segmentation back into napari as a `Labels` layer.
3. Use that `Labels` layer directly as the **EM Segmentation** input to CLEM-Reg's `Point Cloud Sampling` widget, then continue with `Point Cloud Registration & Image Warping` as usual.

See AIoD's [Inference widget documentation](https://franciscrickinstitute.github.io/aiod_docs/sections/front_ends/napari_plugin/inference/) for the full walkthrough.

### Registering Multiple LM Channels
One can register multiple LM channels at once by doing the following.

1. Start by splitting the LM channels into the separate layers by right-clicking on
the layer and then selecting `Split Stack`.
![merged-channel-split-options.png](docs%2Fimages%2Fmerged-channel-split-options.png)
This will result in each of the channels having their own individual layer. 

2. Once this is done we must link all the LM layers together, this is done 
by selecting all the layers which will highlight them in blue, once again right-clicking
on the layer and then selecting `Link Layers.`
![split-channels-link-layers.png](docs%2Fimages%2Fsplit-channels-link-layers.png)

3. When you finally go to run CLEM-reg ensure that for the `Moving Image`
you select the LM layer that contains mitochondria.
## Datasets
Below are the links to the datasets that were used as part of this study.

**EMPIAR-10819**
- [EM] - https://www.ebi.ac.uk/empiar/EMPIAR-10819/
- [FM] - https://www.ebi.ac.uk/biostudies/bioimages/studies/S-BSST707

**EMPIAR-11537**
- [EM] - https://www.ebi.ac.uk/empiar/EMPIAR-11537/
- [FM] - https://www.ebi.ac.uk/biostudies/bioimages/studies/S-BSST1075

Here is a sample dataset which is the binned version of EMPIAR-10819: https://zenodo.org/records/7936982.

## How to cite
```bibtex
@article{krentzel2025clem,
  title={CLEM-Reg: an automated point cloud-based registration algorithm for volume correlative light and electron microscopy},
  author={Krentzel, Daniel and Elphick, Matou{\v{s}} and Domart, Marie-Charlotte and Peddie, Christopher J and Laine, Romain F and Shand, Cameron and Henriques, Ricardo and Collinson, Lucy M and Jones, Martin L},
  journal={Nature Methods},
  pages={1--12},
  year={2025},
  publisher={Nature Publishing Group US New York}
}
```
## License

Distributed under the terms of the [MIT] licence,
"napari-clemreg" is free and open source software

[napari]: https://github.com/napari/napari
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@napari]: https://github.com/napari
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin
[file an issue]: https://github.com/krentzd/napari-clemreg/issues
[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
[conda]: https://docs.conda.io/en/latest/

[//]: # (This [napari] plugin was generated with [Cookiecutter] using [@napari]'s [cookiecutter-napari-plugin] template.)
