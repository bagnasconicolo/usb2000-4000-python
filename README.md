# USB2000/4000 Spectrometer Python-based Acquisition Tools

## Repository Description

This repository contains a collection of Python scripts for acquiring and
visualising spectra with Ocean Optics USB2000/USB4000 series spectrometers.
All scripts rely on the [`seabreeze`](https://github.com/ap--/python-seabreeze)
package together with standard scientific Python libraries.  The
scripts are stored directly in the repository root.  Example output folders generated
by the live acquisition programs can be found in `examples/data/` and are not
required for running the code.

## Installation

1. Install the required packages. The scripts use `numpy`, `pyqtgraph`,
   `PySide6` (for the Qt interface) and `matplotlib` for plotting. Use
   `pip` to install them:

   ```bash
   pip install seabreeze numpy pyqtgraph PySide6 matplotlib
   ```

2. On macOS you may need administrator privileges when accessing the
   spectrometer. The original example suggests running the scripts with
   `sudo` if necessary.

## Overview of Scripts

### `spec.py`
A minimal command‑line program that acquires a single averaged spectrum and
saves it to `usb2000_spectrum.tsv`. Important parts are:

- Requirements listed in the header comment([lines 1-6](spec.py#L1-L6)).
- Acquisition loop that averages several spectra, applies boxcar smoothing and finally stores the result as tab‑separated values([lines 49-67](spec.py#L49-L67)).



The saved file contains two columns named `wavelength_nm` and
`intensity_counts`. A plot of the spectrum is displayed using `matplotlib`.
The variables `integ_ms`, `n_average`, `dark_correct` and `boxcar_px`
at the beginning of the `main()` function can be edited to change the
integration time, number of averaged frames, dark subtraction and smoothing.
`boxcar_px` specifies the half-width of the boxcar smoothing window in
pixels. A value of `n` averages over `2n + 1` neighbouring samples.

### `speclive.py`
Graphical user interface that shows a live spectrum with a 1 s refresh rate.
It uses `pyqtgraph` and runs a timer to periodically read the instrument.
Highlights from the source include:

- Docstring describing its purpose and how to run it([lines 1-8](speclive.py#L1-L8)).
- Acquisition routine which averages several readings and updates the plot
  accordingly([lines 60-76](speclive.py#L60-L76)).


  The acquisition parameters `integ_ms`, `n_avg` and `boxcar_px` at the top
  of the `LiveSpectrum` class can be modified to change integration time,
  frame averaging and smoothing.

Close events are handled so that the spectrometer is properly released.

### `speclive2.py`
A faster variant of the live viewer refreshing every 100 ms. The display can
be paused or resumed by pressing the space bar. Key elements are:

- Introductory documentation that lists its dependencies([lines 1-5](speclive2.py#L1-L5)).
- Use of `QtWidgets.QShortcut` to toggle acquisition with the space key
  while the timer runs at 10 Hz([lines 41-55](speclive2.py#L41-L55)).


  Adjustable variables include `REFRESH_MS` for the update period as well as
  `integ_ms`, `n_avg` and `boxcar_px` which set the integration time,
  averaging and smoothing.

### `speclive3.py`
Extends the live view by adding a “CCD strip” representation below the plot.
Each pixel is coloured according to its wavelength. The script again refreshes
at 100 ms and allows pausing with the space key.

- The beginning of the script provides a utility that converts wavelengths
  into RGB values for the strip image([lines 15-36](speclive3.py#L15-L36)).
- The `update_frame` method builds this coloured line from the latest
  intensities and displays it under the graph([lines 88-110](speclive3.py#L88-L110)).


  Hot‑key `SPACE` pauses/resumes the display. Acquisition parameters such as
  `REFRESH_MS`, `integ_ms` and the boxcar smoothing width can be tweaked at
  the start of the script.

### `speclive4.py`
Most feature‑rich interface combining the live plot and CCD strip with several
keyboard shortcuts and export functions.

- The docstring enumerates the available hot‑keys, including saving the data
  and screenshots([lines 1-9](speclive4.py#L1-L9)).
- During startup a cross‑hair cursor is created and mouse movements update the
  displayed wavelength and intensity in the status bar([lines 50-116](speclive4.py#L50-L116)).
- Functions `save_csv`, `save_png` and `save_all` allow exporting the current
  spectrum in different formats, optionally creating a time‑stamped folder
  with both CSV and PNG files([lines 120-152](speclive4.py#L120-L152)).


  Hot‑keys are:
  `SPACE` to pause/resume, `C` to save a CSV file, `P` to save PNG images
  of the plot and CCD strip, and `S` to save both formats in a new folder.
  Acquisition parameters (`REFRESH_MS`, `integ_ms`) and smoothing width can be
  adjusted near the top of the script before running it.

## Usage

Run any of the scripts with Python after connecting a compatible
spectrometer. For example:

```bash
python spec.py          # acquire and save a single averaged spectrum
python speclive.py      # basic 1 Hz live viewer
python speclive2.py     # fast 100 ms display with start/stop
python speclive3.py     # live view with coloured CCD strip
python speclive4.py     # advanced viewer with export options
```

Close the windows normally to ensure the device connection is closed.

## License

This repository is distributed under the [MIT License](https://opensource.org/licenses/MIT).
Copyright © 2025 Nicolò Bagnasco.
For questions or collaboration opportunities please contact
<nicolo.bagnasco@seds.it>.

