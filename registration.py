import cv2
import pickle
import numpy as np
import os
import threading
import time

# Registration state
_registration_running = threading.Event()
_registration_thread = None
_registration_lock = threading.Lock()
_registration_progress = {"current": 0, "total": 100, "status": "idle", "name": ""}
_current_reg_frame = None
_reg_frame_lock = threading.Lock()

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CASCADE_PATH = os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml')


def _capture_faces(name: str):
    """Background worker to capture face samples"""
    global _registration_progress, _current_reg_frame

    try:
        with _registration_lock:
            _registration_progress = {"current": 0, "total": 100, "status": "capturing", "name": name}


        # Debug info: ensure cascade file exists and report its size
        try:
            exists = os.path.exists(CASCADE_PATH)
            size = os.path.getsize(CASCADE_PATH) if exists else 0
        except Exception:
            exists = False
            size = 0
        print(f"[REG] Cascade path: {CASCADE_PATH}, exists={exists}, size={size}")

        facedetect = cv2.CascadeClassifier(CASCADE_PATH)
        # Fallback: try OpenCV builtin cascade if loading from data/ failed
        if facedetect.empty():
            try:
                import cv2 as _cv2
                builtin = _cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                print(f"[REG] Primary cascade failed; trying built-in cascade at {builtin}")
                facedetect = cv2.CascadeClassifier(builtin)
            except Exception:
                pass

        # Fail early with a clear message if cascade still didn't load
        if facedetect.empty():
            with _registration_lock:
                _registration_progress["status"] = "error"
            raise RuntimeError(f"Face detection cascade failed to load from {CASCADE_PATH} (exists={exists}, size={size}), and built-in cascade also failed.")

        # Debug info: ensure cascade file exists and report its size
        try:
            exists = os.path.exists(CASCADE_PATH)
            size = os.path.getsize(CASCADE_PATH) if exists else 0
        except Exception:
            exists = False
            size = 0
        print(f"[REG] Cascade path: {CASCADE_PATH}, exists={exists}, size={size}")

        facedetect = cv2.CascadeClassifier(CASCADE_PATH)
        # Fallback: try OpenCV builtin cascade if loading from data/ failed
        if facedetect.empty():
            try:
                import cv2 as _cv2
                builtin = _cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                print(f"[REG] Primary cascade failed; trying built-in cascade at {builtin}")
                facedetect = cv2.CascadeClassifier(builtin)
            except Exception:
                pass

        # Fail early with a clear message if cascade still didn't load
        if facedetect.empty():
            with _registration_lock:
                _registration_progress["status"] = "error"
            raise RuntimeError(f"Face detection cascade failed to load from {CASCADE_PATH} (exists={exists}, size={size}), and built-in cascade also failed.")

        video = cv2.VideoCapture(0)

        if not video.isOpened():
            with _registration_lock:
                _registration_progress["status"] = "error"
            return

        faces_data = []
        i = 0

        while _registration_running.is_set() and len(faces_data) < 100:
            ret, frame = video.read()
            if not ret:
                time.sleep(0.05)
                continue

            # Create display frame
            display_frame = frame.copy()

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Try multiple detection strategies - START VERY AGGRESSIVE
            gray_eq = cv2.equalizeHist(gray)
            faces = facedetect.detectMultiScale(gray_eq, scaleFactor=1.05, minNeighbors=2, minSize=(30, 30))

            # Fallback strategies if no face detected
            if len(faces) == 0:
                faces = facedetect.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=2, minSize=(30, 30))

            if len(faces) == 0:
                faces = facedetect.detectMultiScale(gray_eq, scaleFactor=1.03, minNeighbors=1, minSize=(20, 20))

            if len(faces) == 0:
                faces = facedetect.detectMultiScale(gray, scaleFactor=1.02, minNeighbors=1, minSize=(20, 20))

            for (x, y, w, h) in faces:
                crop_img = frame[y:y+h, x:x+w, :]
                resized_img = cv2.resize(crop_img, (50, 50))
                if i % 10 == 0:
                    faces_data.append(resized_img)
                    with _registration_lock:
                        _registration_progress["current"] = len(faces_data)
                i += 1

                # Draw rectangle and progress on display frame
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(display_frame, f"{len(faces_data)}/100", (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Store frame for streaming
            with _reg_frame_lock:
                _current_reg_frame = display_frame.copy()

            time.sleep(0.03)

        video.release()
        cv2.destroyAllWindows()

        if len(faces_data) < 100:
            with _registration_lock:
                _registration_progress["status"] = "error"
            return

        # Save the data
        with _registration_lock:
            _registration_progress["status"] = "saving"

        faces_data = np.asarray(faces_data)
        faces_data = faces_data.reshape(100, -1)

        names_path = os.path.join(DATA_DIR, 'names.pkl')
        faces_path = os.path.join(DATA_DIR, 'faces_data.pkl')

        # Save names
        if not os.path.isfile(names_path):
            names = [name] * 100
            with open(names_path, 'wb') as f:
                pickle.dump(names, f)
        else:
            with open(names_path, 'rb') as f:
                names = pickle.load(f)
            names = names + [name] * 100
            with open(names_path, 'wb') as f:
                pickle.dump(names, f)

        # Save faces
        if not os.path.isfile(faces_path):
            with open(faces_path, 'wb') as f:
                pickle.dump(faces_data, f)
        else:
            with open(faces_path, 'rb') as f:
                faces = pickle.load(f)
            faces = np.append(faces, faces_data, axis=0)
            with open(faces_path, 'wb') as f:
                pickle.dump(faces, f)

        with _registration_lock:
            _registration_progress = {"current": 100, "total": 100, "status": "completed", "name": name}

    except Exception as e:
        with _registration_lock:
            _registration_progress["status"] = "error"
        print(f"Registration error: {e}")
    finally:
        _registration_running.clear()


def start_registration(name: str, role: str = 'user') -> dict:
    """Start face registration for a new user"""
    global _registration_thread

    if _registration_running.is_set():
        return {"success": False, "message": "Registration already in progress"}

    if not name or len(name.strip()) == 0:
        return {"success": False, "message": "Name is required"}

    name = name.strip()
    # Normalize role to lowercase and safe value
    role = (role or 'user').strip().lower()
    if role not in ('admin', 'user'):
        role = 'user'

    # Save the role for later use
    roles_path = os.path.join(DATA_DIR, 'roles.pkl')
    if os.path.isfile(roles_path):
        with open(roles_path, 'rb') as f:
            roles = pickle.load(f)
    else:
        roles = {}

    roles[name] = role
    with open(roles_path, 'wb') as f:
        pickle.dump(roles, f)

    with _registration_lock:
        global _registration_progress
        _registration_progress = {"current": 0, "total": 100, "status": "starting", "name": name}

    _registration_running.set()
    _registration_thread = threading.Thread(target=_capture_faces, args=(name,), daemon=True)
    _registration_thread.start()

    return {"success": True, "message": "Registration started"}


def stop_registration() -> dict:
    """Stop ongoing registration"""
    _registration_running.clear()
    if _registration_thread:
        _registration_thread.join(timeout=3)

    with _registration_lock:
        _registration_progress["status"] = "stopped"

    return {"success": True, "message": "Registration stopped"}


def get_progress() -> dict:
    """Get current registration progress"""
    with _registration_lock:
        return _registration_progress.copy()


def get_registration_frame():
    """Get the current registration video frame for streaming"""
    with _reg_frame_lock:
        if _current_reg_frame is not None:
            return _current_reg_frame.copy()
        return None


def is_running() -> bool:
    """Check if registration is currently running"""
    return _registration_running.is_set()
