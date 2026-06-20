# Gesture

Real-time hand gesture control for mouse movement, clicks, slide navigation, and optional system volume.

This project uses **MediaPipe Hands** for hand landmark detection and a **rule-based gesture layer** to map finger states to desktop actions.

## Features

- Real-time single-hand tracking
- Mouse cursor control with smoothing and dead-zone filtering
- Left click and right click gestures with hold confirmation
- Slide navigation mode for presentations
- Swipe-based slide navigation
- On-screen overlay with gesture name, action, FPS, mode, volume, and live hints
- Optional Windows volume control via `pycaw`

## Demo Gestures

The script maps detected finger states to named gestures.

| Gesture | Action in Mouse Mode | Action in Slides Mode |
| --- | --- | --- |
| Open palm | Move cursor | No action |
| Point | Left click | No action |
| Peace | Right click | No action |
| Thumbs up | Volume up | Volume up |
| Rock on | Volume down | Volume down |
| Three | No action | Next slide |
| Four | No action | Previous slide |
| Swipe right | No action | Next slide |
| Swipe left | No action | Previous slide |
| Fist | Hold / pause | Hold / pause |

## Tech Stack

- [MediaPipe Hands](https://developers.google.com/mediapipe) for 21-point hand landmark detection
- [OpenCV](https://opencv.org/) for webcam capture and overlay rendering
- [PyAutoGUI](https://pyautogui.readthedocs.io/) for mouse and keyboard automation
- [pycaw](https://github.com/AndreMiras/pycaw) for optional Windows-only volume control

## Requirements

- Python **3.11** recommended
- Webcam
- macOS, Windows, or Linux
- Accessibility permissions if you want OS mouse/keyboard control

## Installation

### macOS / Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "mediapipe==0.10.14" "opencv-python<5" numpy pyautogui
```

### Windows

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install mediapipe==0.10.14 opencv-python numpy pyautogui pycaw comtypes
```

## Run

```bash
python gesture_controller.py
```

## Controls

- `Q`: quit the app
- `M`: toggle between `Mouse` and `Slides` mode

## Platform Notes

### macOS

You may need to enable your terminal app in:

- `System Settings > Privacy & Security > Camera`
- `System Settings > Privacy & Security > Accessibility`

Mouse movement, clicks, and slide controls should work once permissions are granted.

Volume control is disabled on macOS in the current implementation because `pycaw` is Windows-only.

### Windows

Volume gestures can work if `pycaw` and `comtypes` are installed.

## How It Works

1. OpenCV reads webcam frames.
2. MediaPipe Hands detects a hand and returns 21 landmarks.
3. The script compares fingertip positions against joints to determine which fingers are extended.
4. A gesture tuple is matched against `GESTURE_MAP`.
5. The mapped action triggers mouse, keyboard, or volume behavior.

## Performance Tuning in This Version

This script is tuned for demo reliability:

- reduced camera resolution for better FPS
- `model_complexity=0` in MediaPipe for faster inference
- internal frame downscaling before hand processing
- cursor smoothing for steadier movement
- dead-zone filtering to reduce jitter
- gesture hold confirmation to reduce accidental clicks

## Project Structure

```text
.
├── gesture_controller.py   # main prototype
├── demo.html               # browser demo / presentation fallback
└── README.md
```

## Known Limitations

- Only one hand is tracked at a time
- Gesture labels depend on the current rule-based mapping in `GESTURE_MAP`
- Volume control is Windows-specific
- Lighting, camera quality, and background clutter affect accuracy
- Very fast hand motion can reduce tracking stability

## Troubleshooting

### `AttributeError: module 'mediapipe' has no attribute 'solutions'`

Use Python 3.11 and install a compatible MediaPipe version:

```bash
python -m pip install "mediapipe==0.10.14"
```

### Cursor does not move or clicks do not work

Grant Accessibility permissions to the terminal app running the script.

### Camera does not open

Check webcam permissions and close any other app using the camera.

## Future Improvements

- Better gesture definitions and calibration
- Two-hand gestures
- Presentation-specific UI mode
- Custom gesture training
- Cross-platform audio control

## License

Use, modify, and adapt for demos, hackathons, and learning.
