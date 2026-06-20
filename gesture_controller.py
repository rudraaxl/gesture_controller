"""
Hand Gesture Recognition - Device Controller
============================================
Controls: Volume, Presentation slides, Mouse cursor
Gestures: Open palm, Fist, Point, Peace, Thumbs up, OK, Swipe L/R

Requirements:
    pip install mediapipe opencv-python pycaw comtypes pyautogui numpy

Run:
    python gesture_controller.py
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import pyautogui
from collections import deque

# ─── Optional: Windows volume control ────────────────────────────────────────
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
    vol_range = volume_ctrl.GetVolumeRange()   # (min_dB, max_dB, step)
    VOLUME_AVAILABLE = True
except Exception:
    VOLUME_AVAILABLE = False
    print("[INFO] pycaw not available — volume control disabled (runs on Mac/Linux too)")

pyautogui.FAILSAFE = False

# ─── MediaPipe setup ──────────────────────────────────────────────────────────
mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils
mp_style = mp.solutions.drawing_styles

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.65,
    min_tracking_confidence=0.55
)

# ─── Colours (BGR) ───────────────────────────────────────────────────────────
C_BG      = (15, 15, 20)
C_ACCENT  = (100, 220, 160)    # teal
C_PURPLE  = (200, 140, 255)
C_WHITE   = (240, 240, 240)
C_DARK    = (40, 40, 50)
C_RED     = (80, 80, 220)
C_AMBER   = (40, 180, 240)

# ─── Gesture definitions (finger state vector) ───────────────────────────────
GESTURE_MAP = {
    (0,0,0,0,0): ("Fist",       "No action"),
    (1,1,1,1,1): ("Open palm",  "Move mouse"),
    (1,0,0,0,0): ("Point",      "Left click"),
    (1,1,0,0,0): ("Peace",      "Right click"),
    (0,0,0,0,1): ("Thumbs up",  "Volume up"),
    (1,0,0,0,1): ("Rock on",    "Volume down"),
    (1,1,1,0,0): ("Three",      "Next slide"),
    (0,1,1,1,0): ("Four",       "Prev slide"),
}

def finger_states(lm, handedness="Right"):
    """Return (thumb, index, middle, ring, pinky) — 1 = extended."""
    tips   = [4, 8, 12, 16, 20]
    joints = [3, 6, 10, 14, 18]
    states = []
    # Thumb — horizontal comparison (mirrored for handedness)
    if handedness == "Right":
        states.append(1 if lm[tips[0]].x < lm[joints[0]].x else 0)
    else:
        states.append(1 if lm[tips[0]].x > lm[joints[0]].x else 0)
    # Other fingers — vertical comparison
    for i in range(1, 5):
        states.append(1 if lm[tips[i]].y < lm[joints[i]].y else 0)
    return tuple(states)

def get_gesture(lm, handedness):
    fs = finger_states(lm, handedness)
    name, action = GESTURE_MAP.get(fs, ("Unknown", "—"))
    return name, action, fs

def draw_rounded_rect(img, x, y, w, h, r, color, thickness=-1):
    """Draw a filled rounded rectangle."""
    cv2.rectangle(img, (x+r, y), (x+w-r, y+h), color, thickness)
    cv2.rectangle(img, (x, y+r), (x+w, y+h-r), color, thickness)
    cv2.circle(img, (x+r,   y+r),   r, color, thickness)
    cv2.circle(img, (x+w-r, y+r),   r, color, thickness)
    cv2.circle(img, (x+r,   y+h-r), r, color, thickness)
    cv2.circle(img, (x+w-r, y+h-r), r, color, thickness)

def draw_ui_overlay(frame, gesture, action, fps, volume_pct, history, mode, hint):
    h, w = frame.shape[:2]

    # ── Dark semi-transparent top bar ────────────────────────────────────────
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 70), C_BG, -1)
    frame[:] = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)

    # Title
    cv2.putText(frame, "GestureAI", (16, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, C_ACCENT, 2, cv2.LINE_AA)
    cv2.putText(frame, "Hand Gesture Controller", (160, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, C_WHITE, 1, cv2.LINE_AA)

    # FPS badge
    fps_text = f"{int(fps)} FPS"
    cv2.putText(frame, fps_text, (w - 90, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, C_ACCENT, 1, cv2.LINE_AA)

    # ── Gesture panel (bottom-left) ───────────────────────────────────────────
    panel_y = h - 180
    overlay2 = frame.copy()
    draw_rounded_rect(overlay2, 12, panel_y, 340, 160, 10, C_BG)
    frame[:] = cv2.addWeighted(overlay2, 0.80, frame, 0.20, 0)

    # Gesture name
    cv2.putText(frame, gesture, (22, panel_y + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, C_PURPLE, 2, cv2.LINE_AA)
    # Action
    cv2.putText(frame, action, (22, panel_y + 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, C_ACCENT, 1, cv2.LINE_AA)

    # Mode badge
    mode_color = C_ACCENT if mode == "Mouse" else C_AMBER
    cv2.putText(frame, f"Mode: {mode}", (22, panel_y + 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, mode_color, 1, cv2.LINE_AA)

    # Live hint for judges
    cv2.putText(frame, hint, (22, panel_y + 124),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_WHITE, 1, cv2.LINE_AA)

    # ── Volume bar (bottom-right) ─────────────────────────────────────────────
    bx, by, bw, bh = w - 120, panel_y, 100, 140
    overlay3 = frame.copy()
    draw_rounded_rect(overlay3, bx, by, bw, bh, 8, C_BG)
    frame[:] = cv2.addWeighted(overlay3, 0.80, frame, 0.20, 0)

    cv2.putText(frame, "Volume", (bx + 10, by + 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, C_WHITE, 1, cv2.LINE_AA)
    # Bar track
    bar_x = bx + 35
    bar_top = by + 40
    bar_bot = by + 120
    bar_ht  = bar_bot - bar_top
    cv2.rectangle(frame, (bar_x, bar_top), (bar_x + 30, bar_bot), C_DARK, -1)
    filled = int(bar_ht * volume_pct / 100)
    fill_color = C_ACCENT if volume_pct < 70 else C_AMBER
    cv2.rectangle(frame, (bar_x, bar_bot - filled), (bar_x + 30, bar_bot), fill_color, -1)
    cv2.putText(frame, f"{int(volume_pct)}%", (bar_x - 4, bar_bot + 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, C_WHITE, 1, cv2.LINE_AA)

    # ── Mini gesture history ─────────────────────────────────────────────────
    hx = 310
    cv2.putText(frame, "Recent gestures", (hx, h - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, C_WHITE, 1, cv2.LINE_AA)
    for i, g in enumerate(list(history)[-5:]):
        alpha = 0.4 + 0.12 * i
        col   = tuple(int(c * alpha) for c in C_ACCENT)
        cv2.putText(frame, g, (hx + i * 60, h - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, col, 1, cv2.LINE_AA)

    return frame

# ─── Main loop ───────────────────────────────────────────────────────────────
def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    prev_time       = time.time()
    prev_gesture    = ""
    gesture_counter = 0
    CONFIRM_FRAMES  = 8           # frames to hold before firing action
    volume_pct      = 50.0
    history         = deque(maxlen=20)
    mode            = "Mouse"

    # Mouse smoothing / safer click confirmation
    smooth_x        = None
    smooth_y        = None
    last_target_x   = None
    last_target_y   = None
    MOVE_SMOOTHING  = 0.22
    POINTER_MARGIN  = 0.18
    POINTER_DEADZONE = 0.012
    CLICK_CONFIRM_FRAMES = 12

    # Swipe tracking
    wrist_trail     = deque(maxlen=15)
    last_action_t   = 0
    ACTION_COOLDOWN = 0.8         # seconds between actions

    print("\n[GestureAI] Starting... Press Q to quit, M to toggle mode\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process a smaller frame for better FPS while keeping landmark ratios intact.
        rgb_small = cv2.resize(rgb, None, fx=0.75, fy=0.75, interpolation=cv2.INTER_LINEAR)
        rgb_small.flags.writeable = False
        res = hands.process(rgb_small)
        rgb_small.flags.writeable = True

        # FPS
        now      = time.time()
        fps      = 1 / max(now - prev_time, 1e-5)
        prev_time = now

        gesture = "No hand"
        action  = "—"
        hint    = "Show one hand clearly to begin"

        if res.multi_hand_landmarks:
            for hand_lm, hand_info in zip(res.multi_hand_landmarks,
                                          res.multi_handedness):
                handedness = hand_info.classification[0].label

                # Draw skeleton
                mp_draw.draw_landmarks(
                    frame, hand_lm, mp_hands.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(color=C_PURPLE, thickness=2, circle_radius=3),
                    mp_draw.DrawingSpec(color=C_ACCENT,  thickness=2)
                )

                lm = hand_lm.landmark
                gesture, action, fs = get_gesture(lm, handedness)

                # Wrist for swipe detection
                wrist = lm[0]
                wrist_trail.append(wrist.x)

                # ── Action dispatch (debounced) ───────────────────────────
                if gesture == prev_gesture:
                    gesture_counter += 1
                else:
                    gesture_counter  = 0
                    prev_gesture     = gesture

                if mode == "Mouse" and gesture == "Open palm":
                    # Use a smaller active zone and ignore tiny shifts for steadier cursor control.
                    ix = lm[8].x
                    iy = lm[8].y
                    sw, sh = pyautogui.size()

                    norm_x = (ix - POINTER_MARGIN) / (1 - 2 * POINTER_MARGIN)
                    norm_y = (iy - POINTER_MARGIN) / (1 - 2 * POINTER_MARGIN)
                    norm_x = max(0.0, min(1.0, norm_x))
                    norm_y = max(0.0, min(1.0, norm_y))

                    target_x = norm_x * sw
                    target_y = norm_y * sh

                    if last_target_x is not None and abs(target_x - last_target_x) < sw * POINTER_DEADZONE:
                        target_x = last_target_x
                    if last_target_y is not None and abs(target_y - last_target_y) < sh * POINTER_DEADZONE:
                        target_y = last_target_y

                    last_target_x, last_target_y = target_x, target_y

                    if smooth_x is None or smooth_y is None:
                        smooth_x, smooth_y = target_x, target_y
                    else:
                        smooth_x += (target_x - smooth_x) * MOVE_SMOOTHING
                        smooth_y += (target_y - smooth_y) * MOVE_SMOOTHING
                    pyautogui.moveTo(int(smooth_x), int(smooth_y), duration=0)
                else:
                    smooth_x, smooth_y = None, None
                    last_target_x, last_target_y = None, None

                confirm_frames = CLICK_CONFIRM_FRAMES if gesture in ("Point", "Peace") else CONFIRM_FRAMES

                if mode == "Mouse" and gesture == "Open palm":
                    hint = "Open palm moves cursor continuously"
                elif mode == "Mouse" and gesture == "Point":
                    hint = f"Hold Point steady to click ({min(gesture_counter + 1, confirm_frames)}/{confirm_frames})"
                elif mode == "Mouse" and gesture == "Peace":
                    hint = f"Hold Peace steady for right click ({min(gesture_counter + 1, confirm_frames)}/{confirm_frames})"
                elif mode == "Slides" and gesture == "Three":
                    hint = "Hold Three for next slide"
                elif mode == "Slides" and gesture == "Four":
                    hint = "Hold Four for previous slide"
                elif gesture in ("Thumbs up", "Rock on"):
                    hint = "Hold gesture to adjust volume"
                elif gesture == "Fist":
                    hint = "Fist pauses input"
                else:
                    hint = f"Current gesture: {gesture}"

                if gesture_counter == confirm_frames and (now - last_action_t) > ACTION_COOLDOWN:
                    last_action_t = now
                    history.append(gesture[:6])

                    if gesture == "Point" and mode == "Mouse":
                        pyautogui.click()

                    elif gesture == "Peace" and mode == "Mouse":
                        pyautogui.rightClick()

                    elif gesture == "Thumbs up":
                        volume_pct = min(100, volume_pct + 10)
                        if VOLUME_AVAILABLE:
                            vol_db = vol_range[0] + (vol_range[1] - vol_range[0]) * (volume_pct / 100)
                            volume_ctrl.SetMasterVolumeLevel(vol_db, None)
                        print(f"[Volume] {int(volume_pct)}%")

                    elif gesture == "Rock on":
                        volume_pct = max(0, volume_pct - 10)
                        if VOLUME_AVAILABLE:
                            vol_db = vol_range[0] + (vol_range[1] - vol_range[0]) * (volume_pct / 100)
                            volume_ctrl.SetMasterVolumeLevel(vol_db, None)
                        print(f"[Volume] {int(volume_pct)}%")

                    elif gesture == "Three" and mode == "Slides":
                        pyautogui.press("right")
                        print("[Slides] Next →")

                    elif gesture == "Four" and mode == "Slides":
                        pyautogui.press("left")
                        print("[Slides] ← Prev")

                    elif gesture == "Fist":
                        print("[Gesture] Fist — hold")

                # ── Swipe detection ───────────────────────────────────────
                if len(wrist_trail) == 15:
                    dx = wrist_trail[-1] - wrist_trail[0]
                    if abs(dx) > 0.25 and (now - last_action_t) > ACTION_COOLDOWN:
                        last_action_t = now
                        if dx > 0:
                            gesture = "Swipe right"
                            action  = "Next slide"
                            history.append("Swipe>")
                            if mode == "Slides":
                                pyautogui.press("right")
                        else:
                            gesture = "Swipe left"
                            action  = "Prev slide"
                            history.append("<Swipe")
                            if mode == "Slides":
                                pyautogui.press("left")
                        wrist_trail.clear()

        # Draw overlay
        frame = draw_ui_overlay(frame, gesture, action, fps, volume_pct, history, mode, hint)

        cv2.imshow("GestureAI — Hand Gesture Controller", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('m'):
            mode = "Slides" if mode == "Mouse" else "Mouse"
            print(f"[Mode] Switched to {mode}")

    cap.release()
    cv2.destroyAllWindows()
    print("\n[GestureAI] Closed.")

if __name__ == "__main__":
    main()
