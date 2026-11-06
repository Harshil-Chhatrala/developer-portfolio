# Traffic Pulse — Intelligent Traffic Management System

Traffic Pulse is a notebook-based prototype for estimating vehicle counts on four intersection approaches and allocating green-signal time in proportion to the detected traffic.

## What the supplied notebook implements

1. Loads a lane image and converts it to grayscale.
2. Applies Gaussian smoothing.
3. Uses Otsu thresholding and morphological opening.
4. Detects external contours and counts contours above a configurable area.
5. Estimates green time for North, East, South, and West using each lane's share of the total detected count.
6. Simulates vehicle discharge using a configurable headway.

## Technology
Python, Jupyter Notebook / Google Colab, OpenCV, NumPy, SciPy, Pillow, Matplotlib.

## Run in Google Colab

1. Open `TrafficPulse.ipynb` in Google Colab.
2. Run the first cell and upload four lane images named exactly:
   - `north.jpg`
   - `east.jpg`
   - `south.jpg`
   - `west.jpg`
3. Run the remaining cells in order.

You can also run the notebook locally after installing the dependencies and placing the four image files in the notebook's working directory.

## Dependencies

```bash
pip install numpy scipy pillow opencv-python matplotlib jupyter
```

## Configuration

The notebook currently uses `HEADWAY = 2.0` seconds and derives `DISCHARGE_RATE = 1 / HEADWAY`. Vehicle detection thresholds (`sigma` and `min_area`) are configurable in the notebook.

## Current prototype limitations

- Vehicle counts are estimated from image contours; this is a basic image-processing approach and can miscount overlapping vehicles, shadows, or background objects.
- The notebook uses four static input images rather than a live camera or physical sensors.
- The green-time allocation is a proportional simulation, not a validated real-world traffic-signal controller.
- The simulation models vehicle discharge with a simplified fixed headway.

This is an academic prototype. Do not connect it directly to real traffic-control hardware without extensive validation and safety engineering.

## Suggested improvements

- Add representative sample images (only images you own or have permission to publish).
- Compare detected counts with manually labelled ground truth.
- Evaluate precision, recall, and counting error.
- Extend the prototype to video/live-camera input and test robust lane-region detection.
