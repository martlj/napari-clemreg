# Design: OME-Zarr input, working format and FAIR project output

This document describes the design and the reasons for it. **It doesn't track status**: that's on GitHub, in the issues each phase below gets. When a decision changes, update the [decisions log](#decisions-log) rather than adding "update" notes to the text.

It builds on [the package split design](package-split.md), whose phase 1 types (`PixelSize`, `Transform`, `Params`, `Result`) everything here uses. It also extends §3 of the [modernisation plan](../napari-clemreg-modernisation-plan.md#3-mobie-project-output-option) and [#6](https://github.com/martlj/napari-clemreg/issues/6), which were written before OME-Zarr 0.6 existed. Where they disagree, this document takes precedence.

## Goal

1. **Any input.** Open OME-Zarr (0.4, 0.5 or 0.6, local or remote) or anything bioio can read (TIFF, OME-TIFF, CZI, ND2, LIF and so on), with physical pixel sizes, axes and channel names taken from the file wherever it has them.
2. **OME-Zarr as the working and output format.** Use the latest specification, [OME-Zarr 0.6](https://ngff.openmicroscopy.org/specifications/dev/) (released 2026-09-14): Zarr v3 with sharding, and RFC-5 named coordinate systems and coordinate transformations for the registration result.
3. **A project directory that is three things at once:**
   - an OME-Zarr scene, holding the raw images, the segmentations and the registration as standard transforms;
   - a valid [MoBIE](https://mobie.github.io/specs/mobie_spec.html) project, so the result opens in Fiji/MoBIE, including from S3;
   - an [RO-Crate](https://www.researchobject.org/ro-crate/), describing the inputs, outputs, parameters, software and provenance, so the result is FAIR and ready to deposit (Zenodo, BioImage Archive, EMPIAR).

The in-memory napari workflow stays as it is for quick, interactive runs. A project is what you get from the headless path, from the Nextflow pipeline ([#91](https://github.com/martlj/napari-clemreg/issues/91)), and from the plugin when you choose to save one.

## The state of the standards (checked 2026-10-11)

| | Status | What it means here |
|---|---|---|
| OME-Zarr 0.6 | Released 2026-09-14. Adds RFC-5: named `coordinateSystems`; `affine`, `rotation`, `sequence`, `displacements`, `coordinates` and `bijection` transforms; `scene` groups holding transforms between images; displacement fields stored as multiscale groups. | The registration result can be stored as a standard transform instead of only in our own format. |
| OME-Zarr 0.5 | Zarr v3, sharding. Widely read: Fiji's N5 library (and so MoBIE), ome-zarr-py, bioio-ome-zarr, napari-ome-zarr. | The safe fallback if a viewer can't read 0.6 yet. |
| Python writers | [ngff-zarr](https://github.com/fideus-labs/ngff-zarr) writes 0.4 to 0.6, including RFC-5 scenes and displacement fields, and adopted the final 0.6 tag on 2026-09-17. bioio-ome-zarr (3.8 is installed here) writes 0.4 and 0.5 with sharding, but not 0.6. | ngff-zarr for writing (D3). |
| MoBIE spec | 0.3.0. Image data includes `ome.zarr` and `ome.zarr.s3`. `sourceTransforms` are `affine` (BigDataViewer convention: 12 values, XYZ, physical units), `crop`, `mergedGrid`, `timepoints` and `transformedGrid`. MoBIE doesn't read RFC-5. | MoBIE views need the affine repeated in their own form. |
| MoBIE viewer, beyond the spec | `mobie-viewer-fiji` now reads non-linear transforms that the published spec and its JSON schema don't list yet (see *Non-linear transforms in MoBIE and BigWarp* below): `thinPlateSpline` (since November 2025), `elastixBSpline`, and `displacementField` (since May 2026), both as view `sourceTransforms` and in collection tables. | BCPD results could be shown in MoBIE without resampling, if the Fiji release users have includes these. |
| BigWarp | Saves landmarks as JSON (`movingPoints`, `fixedPoints`, in physical units) and builds a thin-plate spline from them with the r² log r kernel, the same kernel CLEM-Reg's BCPD warp uses. Exports displacement fields in an "NGFF" format written before RFC-5 was settled, so it may not match 0.6. | CLEM-Reg can write BigWarp landmarks, for MoBIE and for manual correction in BigWarp. |
| RO-Crate | 1.2 (2025). The OME 2024 NGFF Challenge put a top-level `ro-crate-metadata.json` in each OME-Zarr, with at least the organism (NCBI Taxon) and imaging method (FBbi). The Workflow Run RO-Crate profiles describe runs, and Nextflow's [nf-prov](https://www.researchobject.org/ro-crate/nf-prov) plugin writes them. | Per-image crates follow the NGFF Challenge convention, and the project crate follows the Process Run Crate profile. |

**Not yet verified:**
- whether MoBIE, napari-ome-zarr and bioio-ome-zarr open OME-Zarr **0.6** images (0.6 changes the `multiscales` metadata, so a reader that only knows 0.5 may refuse them);
- how MoBIE handles label groups nested inside an image, and multichannel `ome.zarr` sources;
- whether Segment-Flow runs end to end on an `.ome.zarr` input. Its `aiod_utils` already reads OME-Zarr through bioio-ome-zarr;
- whether MoBIE, napari-ome-zarr, bioio-ome-zarr and Neuroglancer place a cropped multiscale image by its `translation`, so it overlays the uncropped source, and whether bioio-ome-zarr returns the translation or `clemreg.io` has to read it from the metadata;
- which MoBIE release on the Fiji update site first includes the `thinPlateSpline` and `displacementField` transforms (the GitHub releases page hasn't been updated since 2022, so check the update site);
- whether MoBIE's thin-plate spline matches CLEM-Reg's resampled BCPD output, and whether it renders quickly enough with as many landmarks as BCPD produces.

Phase 0 checks all of these before any design depends on them.

## Should inputs be converted to OME-Zarr straight away?

**Yes, when a project is being made, and with a few exceptions.** MoBIE does the same: `mobie.add_image` converts on import. For CLEM-Reg the conversion isn't extra work, because the project needs the raw images anyway. For Rigid and Affine CPD, the output *is* the raw FM image plus a transform, with no resampling.

What importing first gives us:

- **One way of reading data in the pipeline.** After import every step reads lazy, chunked arrays from OME-Zarr, whatever the original format was. Format quirks are handled once, at import.
- **Metadata checked once.** Pixel sizes in µm, axis names and channel names are settled at import. A file with no pixel sizes, like the EM sample data today (#42), has to be given them explicitly, and the RO-Crate records that they were supplied by the user. They're never silently assumed.
- **Pyramids.** Later, segmentation and point cloud sampling can read the level closest to the working grid instead of resampling full-resolution data. This changes results, so it's opt-in (see *Later*).
- **Fewer files on HPC.** Sharding keeps a large volume to hundreds of files rather than tens of thousands, which matters on shared filesystems and when Nextflow stages data.
- **Viewers and deposition.** The same files open in MoBIE, napari and Neuroglancer, and can be uploaded as they are.

What it costs, and the rules that follow from that (D2):

- **Time and disk.** EM volumes can be tens to hundreds of GB.
  - Inputs that are already OME-Zarr **0.5 or 0.6** are **linked, not copied**: the scene references them by relative path or URL. This includes remote stores.
  - **0.4** inputs are linked too, since everything reads 0.4. There's an `--upgrade` option to rewrite them as sharded 0.6.
  - Other formats are converted losslessly, with the same dtype and no intensity rescaling. The original file's name, size and SHA-256 go in the RO-Crate.
- **Interactive use.** The plugin doesn't convert anything when a file is opened. Layers stay in memory as they do today, and conversion happens only when **Save project** is used (D2).

## Working on part of a large input

A CLEM experiment often uses only part of a large EM volume, or one region of a remote dataset. There are three ways to get at a part, in order of preference (D13):

1. **Read it lazily, with no copy.** A linked OME-Zarr input (D2) opens as a lazy, chunked array, so slicing it fetches only the chunks it needs, locally or from S3. The crop is a slice plus its origin, and the origin is what keeps coordinates in the frame of the whole image, as the Mask ROI already does. For viewing, MoBIE's `crop` source transform shows a region of a linked source without copying it.
2. **Copy it as OME-Zarr, in the source's frame.** Needed when the region is used many times over a slow link, staged to HPC by Nextflow, deposited on its own, or written back to. The copy:
   - crops every pyramid level with the same physical box: level *L*'s box is the full-resolution box divided by that level's downsampling factor, and the origin is a multiple of the coarsest factor so the levels stay aligned. A small crop that needs fewer levels gets a new pyramid from ngff-zarr instead;
   - keeps each level's `scale` and adds a `translation` set to the origin in µm, so the scene's transforms, the BigWarp landmarks and MoBIE views need no change;
   - copies stored chunks without decoding them when the box lies on chunk boundaries. With sharding the shard is the unit stored, so a box aligned only to chunks means decoding and re-encoding the shards at its edges;
   - crops `labels` groups with the same box, and keeps the `omero` channel names, colours and display ranges.
3. **Export it as OME-TIFF, at one resolution.** Only for tools that can't read OME-Zarr, such as older notebooks, and only for crops that fit in memory. OME-TIFF keeps the pixel sizes and channel names but has no standard place for the origin, so this is an export, not a working format.

Whichever way it's made, the project's RO-Crate records the source (path or URL and checksum), the resolution level, and the box in voxels and in µm.

## The project layout

```
sample01.clemreg/                       # project root = RO-Crate root
  ro-crate-metadata.json                # project crate (Process Run Crate)
  project.json                          # MoBIE project
  sample01/                             # MoBIE dataset
    dataset.json                        # MoBIE sources and views
    images/
      scene.ome.zarr/                   # OME-Zarr 0.6 scene: coordinate systems and transforms
        em/                             # multiscale image (or a link to the input)
          labels/em_segmentation/
          ro-crate-metadata.json        # per-image crate (organism, imaging method)
        fm/                             # multiscale image, (c, z, y, x)
          labels/fm_segmentation/
          ro-crate-metadata.json
        fm_registered/                  # resampled FM: BCPD always, Rigid/Affine CPD only if requested
        transforms/em_to_fm_displacements/   # BCPD only: multiscale displacement field
    tables/                             # MoBIE tables: segmentation tables, point clouds as spots
  clemreg/
    params.json                         # Params.to_json()
    mask_roi.json                       # MaskRoi, if used
    transform.json                      # Transform, CLEM-Reg's own exact form
    bigwarp_landmarks.json              # landmarks for MoBIE's thinPlateSpline and for BigWarp
    bigwarp_project.json                # opens FM, EM and the landmarks in BigWarp
    point_clouds/{moving,fixed,transformed}.parquet
    qc/                                 # overlay images and registration metrics
```

The exact nesting depends on what MoBIE accepts. Phase 0 checks it (D8).

## Transforms

Every transform written to disk comes from one `Transform` object, converted once into **physical units (µm)**. This conversion carries most of the risk, so it gets golden-value tests.

- **Physical units.** Both point clouds are computed on the same isotropic working grid (the EM z pixel size, `w`, on all three axes). So a working-grid affine `A` becomes a physical affine by scaling its translation column by `w`. Whether the working grid's origin matches each image's origin exactly (pixel corners or pixel centres, given `ndimage.zoom`) has to be pinned by a test with a known shift before this is relied on.
- **OME-Zarr 0.6 (RFC-5).** Each image has its own physical coordinate system (`z, y, x`, in micrometres). The scene declares:
  - **Rigid and Affine CPD:** an `affine` (4 × 4, axes in array order) with `input` set to `fm` and `output` set to `em`. That's the forward direction, from FM points to EM points, which is RFC-5's convention.
  - **BCPD:** RFC-5 has no thin-plate spline. Store a `displacements` field sampled on a grid in EM space, mapping EM to FM, which is what resampling needs and what `_make_inverse_warp` already computes. Also keep the exact TPS control points in `clemreg/transform.json`. Whether to also store the forward field and wrap both in a `bijection` is D5.
- **MoBIE, Rigid and Affine CPD.** The same physical affine, with the axes reversed (ZYX to XYZ) and flattened to the BigDataViewer 3 × 4 row-major list, goes in a view's `sourceTransforms` as `"CLEMRegistration"`. BDV transforms map source to global, so it's the same forward direction.
- **MoBIE, BCPD.** See *Non-linear transforms in MoBIE and BigWarp*. The preferred form is a `thinPlateSpline` transform built from BigWarp landmarks, which avoids resampling. The fallbacks are a `displacementField` in MoBIE's own format, then the resampled `fm_registered` image with no transform.
- **napari.** napari can't read RFC-5, but layers have an `affine`. The adapters can show the Rigid or Affine CPD result by giving the raw FM layer the physical affine, with no resampling, so **materialise and display** (#6) becomes optional for these algorithms. BCPD still needs the resampled image.
- **Consistency.** A test applies each written form (RFC-5 affine, MoBIE's 12 values, napari's layer affine, and the displacement field at sample points) to the same points and checks they agree with `Transform` itself.

The EM → FM direction (#68) is out of scope until #68 is decided.

## Non-linear transforms in MoBIE and BigWarp

Checked against the `mobie-viewer-fiji` and `bigwarp` source code on 2026-10-11. None of this is in the published MoBIE spec (0.3.0) or its JSON schema, so the code is the only reference, and it could still change.

**In MoBIE projects.** Alongside `affine`, a view's `sourceTransforms` can now contain:

| Transform | Added | What it holds |
|---|---|---|
| `thinPlateSpline` | November 2025 | `landmarksJson`: BigWarp landmark JSON, either inline or as a path or URI to a file. MoBIE builds the spline itself with BigWarp's code. |
| `elastixBSpline` | not checked | A path to an elastix `TransformParameters` file for a B-spline transform. |
| `displacementField` | May 2026 | `displacementFieldUri`: a path to a JSON metadata file (`type: "inverse_displacement_field"`, `version: 1`, `numDimensions`, `componentAxis`, `size`, `spacing`, `origin`, `dataType: "float32"`, `byteOrder: "BIG_ENDIAN"`, `convention: "x=y+d(y)"`, `rawPath`) pointing to a raw array. It's an *inverse* field, defined on the target grid, which says where to sample the source. That's what CLEM-Reg's `_make_inverse_warp` computes. It is **not** OME-Zarr. |
| `interpolatedAffine` | not checked | Not needed here. |

**In collection tables.** MoBIE collection tables are spreadsheets (CSV, TSV, Excel or Google Sheets) with one row per image, label image or spots table. They're a simpler alternative to a full project. The `affine` column takes either 12 numbers or the path to a *transformation table* listing transforms in order. Each row has a `type` (`affine`, `thin_plate_spline_uri`, `displacement_field_uri` or `elastix_bspline_uri`), a `value`, and optionally a `name` and `invert`. The older `thin_plate_spline` and `displacement_field_uri` columns are deprecated in favour of transformation tables. MoBIE treats images as one channel each, so a multichannel image needs one row per channel, using the `channel` column. So in a collection table, one multichannel OME-Zarr image can serve several channel sources. Phase 0 checks whether project `imageData` can select a channel in the same way (D6).

**BigWarp landmark JSON.**

```json
{"landmarks": {"type": "BigWarpLandmarks", "numDimensions": 3,
               "movingPoints": [[x, y, z], ...], "fixedPoints": [[x, y, z], ...],
               "active": [true, ...], "names": ["Pt-0", ...]}}
```

Points are in physical units, in XYZ order. For CLEM-Reg, the moving points are the FM point cloud and the fixed points are the same points after BCPD moved them into EM space, both converted to µm. BigWarp's thin-plate spline uses the r² log r kernel, the same as `_U` in `warp_image_volume.py`. So MoBIE should reproduce CLEM-Reg's warp from the same landmarks. MoBIE evaluates the spline exactly, while CLEM-Reg interpolates it from a coarser grid (`approximate_grid`), so small differences are expected. Phase 0 measures them.

**What this means for CLEM-Reg:**

- **BCPD results don't need resampling for MoBIE.** Write `clemreg/bigwarp_landmarks.json` and reference it from a `thinPlateSpline` source transform. If phase 0 finds this too slow (every rendered voxel is evaluated against every landmark), either reduce the landmarks or fall back to a `displacementField` written from the inverse warp CLEM-Reg already computes. The resampled `fm_registered` image stays as the last resort, and as an option for people using older MoBIE releases (D10).
- **Correcting a registration by hand.** The same landmarks file opens in BigWarp. See *Refining a registration by hand in BigWarp* for what's confirmed and what still needs checking.
- **Standards come first.** The RFC-5 `displacements` field in the scene stays the representation that follows the standard. The MoBIE and BigWarp forms are additional copies for viewers that don't read RFC-5 yet, all generated from the same `Transform` and covered by the consistency test.
- **BigWarp's own NGFF export** predates the final RFC-5. Until BigWarp is updated for 0.6, don't rely on BigWarp reading CLEM-Reg's RFC-5 fields, or on CLEM-Reg reading BigWarp's.

## Refining a registration by hand in BigWarp

The aim is that a user can open a CLEM-Reg result in [BigWarp](https://imagej.github.io/plugins/bigwarp), correct it by moving or adding landmarks, and bring the corrected transform back into the project. Parts of this are confirmed from BigWarp's source code (checked 2026-10-11, latest commit 2026-06-02). The rest hasn't been tried yet.

**Confirmed from the source code:**

- **Landmark import.** BigWarp's landmark table reads CSV or JSON, chosen by file extension (`LandmarkTableModel.load`). The JSON form is `{"landmarks": {...}}`, the same object MoBIE's `thinPlateSpline` reads, so one file can serve both. Each landmark has an `active` flag, which BigWarp uses to switch landmarks off without deleting them.
- **Project files.** A BigWarp settings ("project") file lists the images under `Sources`, each with a `uri`, a `name` and `isMoving`. It holds the transform under `Transform`, with a `type` and the `landmarks`, along with display settings. So CLEM-Reg can write one file that opens the FM image as moving, the EM image as fixed, and the landmarks with the right transform type, in a single step.
- **Transform types.** BigWarp fits *Thin Plate Spline*, *Affine*, *Similarity*, *Rotation* or *Translation* from the landmarks. It can also limit a thin-plate spline's effect to a region with a mask, which suits local corrections.
- **Same spline.** BigWarp's thin-plate spline uses the r² log r kernel, the same as CLEM-Reg's (`_U` in `warp_image_volume.py`).
- **Coordinates stay in the full image.** The Mask ROI sets voxels outside the region to zero without cropping (`mask_roi.py`), so FM point coordinates are in the frame of the whole FM image, not of a crop.

**What CLEM-Reg would write** (in `clemreg/`, from the same `Transform` as everything else):

- `bigwarp_landmarks.json`: landmarks in µm, XYZ order. FM points are the moving points, and the same points after registration, in EM space, are the fixed points.
- `bigwarp_project.json`: a BigWarp project referencing the project's FM image (moving, one source per channel) and EM image (fixed), the landmarks, and the transform type that matches the algorithm.
- **BCPD:** the thin-plate spline built from the control points. CLEM-Reg uses *every* point of both clouds as a control point, and on the sample data that's more than 1,000 per cloud (`test_gui_end_to_end.py` checks for more than 1,000). That's too many to edit by hand (see the checks below). So the editable file holds a well-spread subset, for example 100–300 points chosen by farthest-point sampling. The full set stays in `transform.json` for exact reproduction, and the QC output reports how far the subset's spline differs from the full one, as the mean and maximum displacement difference over the FM volume (D12).
- **Rigid and Affine CPD:** these have no landmarks of their own. CLEM-Reg generates them by applying the matrix to well-spread FM points, such as the corners of the FM volume plus a subset of the point cloud. Because the pairs are exact, BigWarp's fit recovers the same matrix. The transform type is *Affine* for Affine CPD. For Rigid CPD it's *Similarity*, since probreg's rigid CPD (`cpd.registration_cpd(..., tf_type_name='rigid')` with default options) also fits a uniform scale. The user can then switch to *Thin Plate Spline* to add local corrections on top.

**Bringing the correction back:** a `Transform.from_bigwarp()` reads the landmarks file (JSON or CSV), keeps only active landmarks, converts XYZ µm to CLEM-Reg's ZYX, and builds either a thin-plate spline or an affine fitted from the landmarks, depending on the transform type. The project then regenerates everything that depends on the transform (RFC-5 transforms, MoBIE views, the resampled image if one is wanted, and QC). The original landmarks are kept alongside the refined ones. The project's RO-Crate records the correction as its own step, carried out by a person using BigWarp (with its version), so the provenance shows that the result isn't purely automatic.

**Checks still to do** (added to phase 0, [#93](https://github.com/martlj/napari-clemreg/issues/93)):

1. **Coordinates line up.** Open a CLEM-Reg result in BigWarp and check the overlay matches CLEM-Reg's own. BigWarp places images by their calibration, so the landmarks need the same units and the same origin. ImgLib2 puts pixel centres at integer coordinates, which needs the same origin test as in *Transforms*. The EM sample TIFF has no pixel size (#42), so BigWarp would treat its pixels as 1 unit. Use the project's OME-Zarr images, or TIFFs with the calibration set.
2. **Opening images from a project file.** BigWarp opens TIFF paths from a project's `uri` (its test files do this). Check N5, Zarr and OME-Zarr 0.5 and 0.6 URIs, including S3, and that each FM channel appears as its own moving source.
3. **Responsiveness.** Time BigWarp with all of BCPD's landmarks and with subsets of 100, 300 and 1,000. Each edit solves the spline again (at a cost that grows roughly with the cube of the number of landmarks), and the landmark table is meant for tens to hundreds of hand-placed points. This sets the default subset size (D12).
4. **Agreement.** Compare BigWarp's warp with CLEM-Reg's resampled BCPD output, using both the full set and the subset.
5. **Affine recovery.** Check that BigWarp's *Affine* and *Similarity* fits reproduce CLEM-Reg's matrices from the generated pairs, and confirm whether probreg's rigid CPD fits a scale with the options CLEM-Reg uses.
6. **Import format.** Check whether BigWarp's *Import landmarks* accepts the `{"landmarks": ...}` JSON on its own, or only CSV and full project files. Check whether *Load project* accepts a file that has only `Sources` and `Transform`, without the display settings.
7. **Round trip.** Edit landmarks in BigWarp, export them, import them with `Transform.from_bigwarp()`, and check the result matches BigWarp's own warp of the same landmarks.

## FAIR metadata (RO-Crate)

- **Per-image crates**, at the root of each OME-Zarr image, following the NGFF Challenge convention: the organism (NCBI Taxon ID) and imaging method (an FBbi term, e.g. serial block-face SEM, FIB-SEM or confocal microscopy), plus a name and description. Only the user can supply these. The CLI takes them as options, the plugin's Save project form asks for them, and Nextflow takes them as samplesheet columns.
- **The project crate**, at the project root:
  - It conforms to RO-Crate 1.2 and the [Process Run Crate](https://w3id.org/ro/wfrun/process) profile.
  - Each pipeline step is a `CreateAction`. Its `instrument` is CLEM-Reg (the `SoftwareApplication`, with version, repository and the CLEM-Reg paper's DOI). Its `object` lists the inputs, its `result` the outputs, and parameters are `PropertyValue`s matching `params.json`.
  - It also records the licence, the authors (with ORCIDs where given), the original input files with checksums, any user-supplied pixel sizes, and where the EM segmentation came from (Segment-Flow version and model name, or a supplied mask).
- **Nextflow runs** (#91) also get a Workflow Run Crate from nf-prov. The project crate links to it rather than duplicating it.
- **Checks:** `rocrate-validator` in the tests. Required fields (D7) are enforced when a project is written, with an explicit "not specified" value allowed and recorded, so metadata is never silently missing.

| FAIR | How the project meets it |
|---|---|
| Findable | Rich metadata in the RO-Crate, using ontology terms (NCBI Taxon, FBbi). Ready for a DOI on deposition. |
| Accessible | Open, cloud-friendly formats (OME-Zarr, JSON-LD) that stream from S3 in MoBIE and Neuroglancer. |
| Interoperable | Standard OME-Zarr 0.6 transforms, a valid MoBIE project, and schema.org/RO-Crate metadata. |
| Reusable | Licence, parameters, software version, input checksums, and step-by-step provenance. |

## What changes in the workflow

| Part | Today | With this design |
|---|---|---|
| Reading (`_reader.py`, `data_preprocessing.get_pixelsize`) | napari reader for TIFF only. Pixel sizes come from ImageJ-style metadata, in nm. | A core `clemreg.io.open_image(path_or_url)` using bioio, returning a lazy array, `PixelSize` (µm), axis and channel names, and source details. The plugin doesn't register a competing `.zarr` reader (napari-ome-zarr already does, and see #40). Its adapters take pixel sizes from the layer's `scale` and `units` when the layer came from another reader. |
| FM segmentation (`segment_fm`) | Whole array in memory. | Unchanged. FM volumes are small; it reads level 0 from the project and writes a `labels` group. |
| EM segmentation (`segment_em`, Segment-Flow) | Writes a temporary TIFF and runs Segment-Flow on it. | Passes the project's EM OME-Zarr straight to Segment-Flow (if phase 0 confirms it works), and writes the mask as a `labels` group. A supplied mask is imported like any other input. |
| Mask ROI | A napari `Shapes` layer, becoming `MaskRoi` in the split. | Saved as `clemreg/mask_roi.json`, and linked in the RO-Crate. |
| Point cloud sampling (`_make_isotropic`) | Resamples full-resolution segmentations onto the working grid. | Unchanged by default, so the baseline is unchanged. Reading a pyramid level is a later opt-in. Point clouds are saved, and shown in MoBIE as spots tables. |
| Registration | Point clouds in, matrix or TPS out. | Unchanged. `Transform` gains the physical-units conversion and the serialisers above. |
| Warping (`warp_image_volume`) | Dense `ndimage` resampling of whole arrays in memory. | Rigid and Affine CPD write no image at all unless asked. When resampling is needed it runs chunk by chunk (dask, output chunks aligned to shards) and writes straight to OME-Zarr, so large volumes fit in memory. BCPD also writes the displacement field. |
| Output | napari layers. | napari layers, and optionally a project. The Run Registration widget gets the #6 output-mode setting and the metadata fields. A saved project can be reopened in napari. |
| Sample data (#41, #42) | TIFFs on Zenodo, with a hard-coded EM pixel size. | A published CLEM-Reg project on Zenodo (OME-Zarr 0.6, correct pixel sizes, RO-Crate), used as the demo and as a test fixture. The TIFFs stay for older notebooks. |
| Nextflow (#91) | Planned. | The first process imports each sample into a project, and the project directory is the published output. |

## Dependencies

- Core `[io]` extra: bioio, bioio-ome-zarr and bioio-tifffile (as planned in the split), plus whichever other bioio format plugins are documented. bioio-ome-zarr needs Python 3.11 or newer, which the project already requires.
- Core `[ome-zarr]` extra: ngff-zarr, zarr ≥ 3 and dask, for writing projects.
- Core `[fair]` extra: `rocrate` (ro-crate-py). Possibly folded into `[ome-zarr]` as a single `[project]` extra.
- Test-only: `rocrate-validator`, and either mobie-utils (conda-forge; a separate CI job) or MoBIE's published JSON schemas for project validation (D4).
- No new required dependencies for the plugin. Save project needs the extras and says so clearly when they're missing.

## Phases

Each phase is one PR (or a few), leaves the tests passing, and keeps the pipeline output baseline (`test_pipeline_baseline.py`) unchanged.

0. **Compatibility check**, nothing merged except possibly a script. Write a small sharded scene with ngff-zarr, in 0.6 (affine plus displacements) and in 0.5. Open it in MoBIE/Fiji, napari-ome-zarr, bioio-ome-zarr and Neuroglancer. Test MoBIE with nested label groups, multichannel sources and linked external stores. Run Segment-Flow on an `.ome.zarr` input. Time sharded writes of a large dask array. Find the first Fiji update-site release of MoBIE with `thinPlateSpline` and `displacementField`. Open a BCPD result in MoBIE through `thinPlateSpline` and through `displacementField`, compare both with CLEM-Reg's resampled output and time the rendering. Carry out the BigWarp checks in *Refining a registration by hand in BigWarp*. Open a cropped multiscale image with a `translation`, in 0.5 and 0.6, in each viewer and in bioio-ome-zarr, and check it overlays the uncropped source. The results settle D1, D5, D6, D8, D10, D11, D12 and D13.
1. **Reading** (needs package split phase 1, #58): `clemreg.io.open_image` returning a `PixelSize` in µm, replacing `get_pixelsize`. The adapters read layer `scale` and `units`. Tests run on generated fixtures: TIFF, OME-TIFF, and OME-Zarr 0.4, 0.5 and 0.6. This also lets the plugin run on images opened by napari-ome-zarr.
2. **Physical transforms**: the physical-units conversion, the RFC-5, MoBIE and napari serialisers, the consistency test, and the origin test. In the plugin, show the Rigid and Affine CPD results through the layer `affine`.
3. **Import and project writer**: `clemreg.project` and `clemreg import`. Convert, or link, inputs into a sharded multiscale scene, with per-image crates and the required metadata.
4. **Pipeline on projects**: segmentations as `labels`, Segment-Flow fed from the project, `MaskRoi`, params and point clouds saved, scene transforms written, chunked warping and the BCPD displacement field, and QC outputs.
5. **MoBIE**: `project.json`, `dataset.json`, sources, views and tables generated from the scene, validated in CI (D4) and checked by hand in Fiji. BCPD results use `thinPlateSpline` or `displacementField` (D10), and a collection table is written if D11 says so. The BigWarp landmarks and project files are written here too. This replaces the `mobie_export.py` design in #6.
6. **Project RO-Crate**: the Process Run Crate, validation, and the link to nf-prov output for Nextflow runs (#91).
7. **Plugin**: **Save project** (the #6 output-mode setting), metadata fields, and reopening a project. Decide on #40 if formats beyond those already handled are needed.
8. **Sample data**: publish the sample project (#41, #42) and switch the slow tests to it.

Phases 1 and 2 can start as soon as package split phase 1 merges. Phases 3 to 6 make up the headless path, and Nextflow (#91) needs phases 3 and 4.

**Later:**
- importing refined BigWarp landmarks back into a project (`Transform.from_bigwarp()`), with the correction recorded as its own step in the RO-Crate;
- reading a pyramid level for segmentation and sampling (opt-in, because it changes results);
- writing projects straight to S3;
- RFC-4 orientation metadata;
- 2D projects (#79). OME-Zarr 0.6 handles 2D with no special cases, so `Transform` with an `ndim` (planned in #58) carries over.

## Risks

- **MoBIE features outside its spec.** The non-linear transforms are in the viewer's code but not in the published spec or schema, so they could change and nothing validates them. Mitigations: state a minimum MoBIE version, test against it in phase 0 and in the release checklist, and keep the resampled image as an option.
- **Viewers lag behind the spec.** 0.6 is a month old. MoBIE doesn't read RFC-5, napari doesn't either, and support for reading 0.6 images is unconfirmed. Mitigations: the MoBIE views repeat each transform in a form MoBIE reads (an affine, or BigWarp landmarks for BCPD), a resampled image is available when nothing else works, the `ngff_version` setting can switch to 0.5 images (D1), and dependency versions are pinned.
- **Getting a transform wrong.** Axis order, units, direction (forward or inverse) and pixel origin are each a likely source of a silent misalignment. Mitigations: one `Transform` source, golden-value tests, the consistency test, and a check by eye in MoBIE and napari against a known-good overlay, added to the manual release checklist.
- **Disk and time.** Converting large EM volumes duplicates them. Linking OME-Zarr inputs, and making conversion explicit, keeps this visible and avoidable.
- **Sharding and parallel writes.** Only one writer can safely write to a shard at a time. Dask chunks for writing must line up with shards, which also limits how parallel chunked warping can be.
- **Label images.** Segmentations and resampled labels must keep integer types and nearest-neighbour interpolation (`order=0`), and pyramids for labels must be downsampled by a mode or nearest rule, not by averaging.
- **Metadata people won't fill in.** Required fields with an explicit "not specified" value make the gap visible without blocking a run.
- **The baseline.** None of this is meant to change results. The pipeline output baseline must pass unchanged in every phase, except for opt-in features that are documented as changing results.

## Decisions log

Each decision is **Proposed** until confirmed in its phase's issue.

| # | Decision | Options considered | Proposed | Status |
|---|---|---|---|---|
| D1 | OME-Zarr version written | 0.6 everywhere; 0.5 images plus a 0.6 scene; a setting | 0.6 everywhere, behind an `ngff_version` setting, falling back to 0.5 images (with the 0.6 scene alongside, if the spec allows a 0.6 scene to reference 0.5 images) if phase 0 finds MoBIE can't read 0.6. | Proposed |
| D2 | When inputs are converted | always on import; never; convert other formats and link OME-Zarr; in the GUI, only on Save project | Convert other formats on import; link OME-Zarr 0.4 to 0.6, with an `--upgrade` option; in the GUI, convert only on Save project. | Proposed |
| D3 | Library for writing OME-Zarr | ngff-zarr; bioio-ome-zarr; ome-zarr-py | ngff-zarr, the only Python writer confirmed for 0.6 and RFC-5. bioio stays the reader for other formats. | Proposed |
| D4 | Writing MoBIE metadata | mobie-utils; our own small writer checked against MoBIE's JSON schemas | Our own writer: mobie-utils writes its own OME-Zarr (0.4) and is mostly installed through conda. Use mobie-utils or the schemas only in tests. The schemas don't cover the non-linear transforms yet (D10), so those are checked by opening the project in MoBIE. | Proposed |
| D5 | Storing a BCPD result | EM-to-FM displacement field only; a `bijection` of both fields; TPS control points only | The EM-to-FM displacement field in the scene, plus the exact TPS control points in `clemreg/transform.json` and `clemreg/bigwarp_landmarks.json`. A resampled `fm_registered` for napari, and for MoBIE only as D10 decides. Add the `bijection` if phase 0 shows a reader that uses it. | Proposed |
| D6 | Multichannel FM | one multichannel image; one image per channel | One multichannel image, matching the input, if MoBIE can select a channel from an `ome.zarr` source; otherwise one image per channel. | Proposed |
| D7 | Required FAIR metadata | none; organism and imaging method; also licence and authors | Organism, imaging method and licence are required, each allowing an explicit "not specified". Authors, ORCIDs and description are optional. | Proposed |
| D8 | Project layout | as above; MoBIE's own default layout with a separate scene | As above, adjusted for whatever phase 0 shows MoBIE accepts. | Proposed |
| D9 | Images with no pixel size | refuse; assume 1; use a sample-data override | Refuse to import without explicit pixel sizes, and record the values the user gives as user-supplied. | Proposed |
| D10 | BCPD in MoBIE | resampled `fm_registered` only; `thinPlateSpline` from BigWarp landmarks; MoBIE `displacementField` | `thinPlateSpline`, if phase 0 shows it matches CLEM-Reg's output and renders fast enough, with `displacementField` as the fallback. Keep writing `fm_registered` as an option for older MoBIE releases. | Proposed |
| D11 | MoBIE output form | a MoBIE project; a collection table; both | A MoBIE project (a versioned spec, with views), plus a collection table with a transformation table if it costs little, since it opens directly in Fiji and suits Nextflow batch output. | Proposed |
| D12 | Landmarks exported for editing in BigWarp | all of BCPD's control points; a well-spread subset; let the user choose | A subset chosen by farthest-point sampling, with a default size set by phase 0's timing and agreement checks. Report the difference from the full spline in QC, and keep the full set in `transform.json`. | Proposed |
| D13 | Working on part of a large input | read lazily with no copy; copy as OME-Zarr; export as TIFF | Read lazily by default. When a copy is needed, write OME-Zarr with a `translation` so it stays in the source's frame, cropping the existing pyramid levels or regenerating them for small crops. OME-TIFF only as an export for tools that can't read OME-Zarr. Record the source and box in the RO-Crate. Confirmed once phase 0 shows the viewers and bioio honour the translation. | Proposed |
