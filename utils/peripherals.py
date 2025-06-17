import os

import pyaudio


def check_microphone():
    """Check if microphone is available"""
    try:
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()

        for i in range(device_count):
            device_info = p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                p.terminate()
                return True
        p.terminate()
        return False
    except:
        return False


def check_camera():
    """Scan all available webcams and select the one with the highest actual resolution."""
    import cv2
    import time

    best_camera = None
    best_resolution = (0, 0)

    for camera_index in range(10):
        try:
            cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW if os.name == 'nt' else 0)

            if cap.isOpened():
                time.sleep(0.3)

                resolutions_to_test = [(1920, 1080), (1280, 720), (640, 480)]
                max_res = (0, 0)

                for width, height in resolutions_to_test:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    time.sleep(0.2)

                    ret, frame = cap.read()
                    if ret and frame is not None:
                        actual_h, actual_w = frame.shape[:2]
                        if actual_w * actual_h > max_res[0] * max_res[1]:
                            max_res = (actual_w, actual_h)

                print(f"Camera {camera_index} max resolution: {max_res}")

                if max_res[0] * max_res[1] > best_resolution[0] * best_resolution[1]:
                    best_resolution = max_res
                    best_camera = camera_index

                cap.release()

        except Exception as e:
            print(f"Error with camera {camera_index}: {e}")

    if best_camera is not None:
        print(f"Best camera: {best_camera}, Resolution: {best_resolution}")
        return True, best_resolution[0], best_resolution[1]
    else:
        return False, 0, 0
