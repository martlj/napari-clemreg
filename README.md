

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

This fork (`martlj/napari-clemreg`) is being actively modernised — see [docs/napari-clemreg-modernisation-plan.md](docs/napari-clemreg-modernisation-plan.md) for the full plan. **All of this work lives on the `modernisation` branch, not `main`** — the default branch you'd get from a plain `git clone` doesn't have it yet.

If you already have this repo cloned, switch to that branch rather than cloning again (cloning into an existing checkout creates a confusing nested copy):
```
git fetch origin
git checkout modernisation
```
Otherwise, clone it directly onto that branch:
```
git clone -b modernisation https://github.com/martlj/napari-clemreg.git
cd napari-clemreg
```

This branch now requires **Python 3.11+**. `empanada-dl` (needed for the bundled EM Segmentation widget) currently blocks a normal install on Python 3.11 — it hard-pins `numpy==1.22`, which has no Python 3.11 wheels (tracked in [issue #5](https://github.com/martlj/napari-clemreg/issues/5)). Until that's resolved, install everything else and skip it.

Using [`uv`](https://docs.astral.sh/uv/) (recommended — fast, and installs the Python version for you if needed). `uv pip install` and `uv run` both auto-detect the local `.venv`, so **don't `source .venv/bin/activate`** — if you have a conda environment already active (e.g. `base` auto-activates in many setups), a plain `source activate` can silently lose to conda's own `PATH` handling and run the wrong `napari` entirely:

```
uv venv --python 3.11
uv pip install typing_extensions setuptools packaging pint numpy scipy "scikit-image>=0.22" "magicgui>=0.8.3" "napari>=0.6" open3d probreg transforms3d tqdm h5py matplotlib imageio tifffile torch connected-components-3d pyqt6
uv pip install -e . --no-deps
uv run napari
```

Or with plain `pip` in a conda environment (needs an existing Python 3.11+ interpreter):

```
conda create -n clemreg_dev python=3.11
conda activate clemreg_dev
pip install typing_extensions setuptools packaging pint numpy scipy "scikit-image>=0.22" "magicgui>=0.8.3" "napari>=0.6" open3d probreg transforms3d tqdm h5py matplotlib imageio tifffile torch connected-components-3d pyqt6
pip install -e . --no-deps
napari
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
11. **EM Segmentation Parameters** - Here are the advanced options for the segmentation of the mitochondria in the EM data.
    1. **Prediction Across Three Axis** - By selecting this option MitoNet will run segmentation across all three axis of the EM volume and then these three predictions will be aggregated. Only applies to the bundled `empanada (local)` backend.
    2. **EM Segmentation Backend** - Choose between `empanada (local)` (the bundled MitoNet, currently blocked on Python 3.11 — see [issue #5](https://github.com/martlj/napari-clemreg/issues/5)) and `AI-on-Demand (Segment-Flow)` — see [Using AI-on-Demand (AIoD) for EM Segmentation](#using-ai-on-demand-aiod-for-em-segmentation) below for the extra setup it needs.
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

The bundled `Electron Microscopy (EM) Segmentation` widget defaults to running MitoNet directly via `empanada-dl`, a dependency that's no longer actively maintained and currently blocks installation entirely on Python 3.11 (see [issue #5](https://github.com/martlj/napari-clemreg/issues/5)). As an alternative, both the standalone `EM Segmentation` widget and the all-in-one `Run Registration` widget offer an **EM Segmentation Backend** dropdown — switch it to `AI-on-Demand (Segment-Flow)` to run the same MitoNet model through Crick's [AI-on-Demand (AIoD)](https://franciscrickinstitute.github.io/aiod_docs/) Segment-Flow pipeline instead, with no other changes to your workflow. Unlike the earlier approach of running AIoD's own separate `aiod_napari` plugin and manually feeding its output into `Point Cloud Sampling`, this is fully integrated — just pick the backend and run.

**Prerequisites** (only needed for this backend — the rest of napari-clemreg works without them):
- [Nextflow](https://www.nextflow.io/) and [Conda](https://docs.conda.io/) on `PATH`.
- A JDK, ideally version 17–21 — very recent JDKs (tested: 26) fail with `Unsupported class file major version`. On macOS, `brew install openjdk@21` is enough on its own; it's auto-detected even without setting `JAVA_HOME` yourself. On other platforms, set `JAVA_HOME` to point at a compatible JDK if your system default is newer.
- The `segment-flow` extra, which pulls in the small, pure-Python packages needed to talk to AIoD's model registry (no heavy ML dependencies):
  ```
  uv pip install "napari-clemreg[segment-flow]"
  ```
  (or `pip install "napari-clemreg[segment-flow]"`)

Once those are in place, select `AI-on-Demand (Segment-Flow)` from the **EM Segmentation Backend** dropdown and run as normal. The first run on a given machine downloads and builds an isolated Conda environment for the model (cached under `~/.nextflow/aiod`, reused on later runs), so it can take several minutes; progress streams to the terminal. The model itself always runs inside Segment-Flow's own isolated environment, never in napari-clemreg's own Python process.

**Just want to try the pipeline without a GPU or setting up AIoD?** `File → Open Sample → napari-clemreg → EM Mask (precomputed, no GPU needed)` loads a precomputed EM segmentation matching the EM volume in the main sample data, so you can go straight to the `Point Cloud Sampling` widget without running any EM segmentation step at all.

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
