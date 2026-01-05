import pickle
import numpy as np
import os
import csv
import time
from datetime import datetime, timedelta
from sklearn.neighbors import KNeighborsClassifier

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ATT_DIR = os.path.join(os.path.dirname(__file__), 'Attendance')
CASCADE_PATH = os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml')

# In-memory state for each user
_user_states = {}
_last_logged_at = {}

# Load model and cascade once on startup
_knn = None
_face_cascade = None

def _load_model_and_cascade():
    global _knn, _face_cascade

    # Ensure cv2 is available
    import cv2

    # Load KNN model if not already loaded
    if _knn is None:
        names_path = os.path.join(DATA_DIR, 'names.pkl')
        faces_path = os.path.join(DATA_DIR, 'faces_data.pkl')
        if not (os.path.isfile(names_path) and os.path.isfile(faces_path)):
            raise FileNotFoundError('names.pkl or faces_data.pkl not found in data/. Add faces first.')
        with open(names_path, 'rb') as f:
            labels = pickle.load(f)
        with open(faces_path, 'rb') as f:
            faces = pickle.load(f)
<<<<<<< HEAD
        # Ensure labels is a list and faces is a numpy array
        try:
            labels = list(labels)
        except Exception:
            labels = [str(x) for x in labels]

        faces = np.asarray(faces)

        # If counts mismatch, trim to the smaller length and persist fix
        n_labels = len(labels)
        n_faces = faces.shape[0] if faces.ndim >= 1 else 0
        if n_labels != n_faces:
            m = min(n_labels, n_faces)
            print(f"⚠️  Mismatch: {n_faces} face samples vs {n_labels} labels. Trimming to {m} entries.")
            try:
                labels = labels[:m]
                faces = faces[:m]
                # Persist corrected files
                with open(names_path, 'wb') as f:
                    pickle.dump(labels, f)
                with open(faces_path, 'wb') as f:
                    pickle.dump(faces, f)
                print("✅ Trimmed and saved corrected `names.pkl` and `faces_data.pkl`")
            except Exception as e:
                print(f"⚠️  Failed to persist trimmed data: {e}")

        if faces.ndim != 2:
            faces = faces.reshape(faces.shape[0], -1)
=======

        # Ensure labels is a list and faces is a numpy array
        try:
            labels = list(labels)
        except Exception:
            labels = [str(x) for x in labels]

        faces = np.asarray(faces)

        # If counts mismatch, trim to the smaller length and persist fix
        n_labels = len(labels)
        n_faces = faces.shape[0] if faces.ndim >= 1 else 0
        if n_labels != n_faces:
            m = min(n_labels, n_faces)
            print(f"⚠️  Mismatch: {n_faces} face samples vs {n_labels} labels. Trimming to {m} entries.")
            try:
                labels = labels[:m]
                faces = faces[:m]
                # Persist corrected files
                with open(names_path, 'wb') as f:
                    pickle.dump(labels, f)
                with open(faces_path, 'wb') as f:
                    pickle.dump(faces, f)
                print("✅ Trimmed and saved corrected `names.pkl` and `faces_data.pkl`")
            except Exception as e:
                print(f"⚠️  Failed to persist trimmed data: {e}")

        if faces.ndim != 2:
            faces = faces.reshape(faces.shape[0], -1)

>>>>>>> 1ed0492 (UI cleanup: removed duplicate buttons, centered header, restored camera access button)
        _knn = KNeighborsClassifier(n_neighbors=3, weights='uniform')
        _knn.fit(faces, labels)
        print("✅ KNN model loaded successfully")

    # Load face cascade if not already loaded
    if _face_cascade is None:
        # Try multiple approaches to load the cascade
        cascade_loaded = False

        # Method 1: Try loading from the data directory
        if os.path.exists(CASCADE_PATH):
            _face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
            if not _face_cascade.empty():
                print(f"✅ Successfully loaded cascade from {CASCADE_PATH}")
                cascade_loaded = True
            else:
                print(f"⚠️  Cascade file exists but failed to load from {CASCADE_PATH}")

        # Method 2: Try using OpenCV's built-in cascade (if available)
        if not cascade_loaded:
            try:
                # Some OpenCV installations have built-in cascades
                # Let's try a common alternative path
                import cv2.data
                builtin_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                if os.path.exists(builtin_path):
                    _face_cascade = cv2.CascadeClassifier(builtin_path)
                    if not _face_cascade.empty():
                        print(f"✅ Successfully loaded built-in cascade from {builtin_path}")
                        cascade_loaded = True
                    else:
                        print(f"⚠️  Built-in cascade exists but failed to load from {builtin_path}")
            except:
                pass

        # Method 3: If all else fails, raise an error with helpful instructions
        if not cascade_loaded:
            error_msg = f"""
❌ Failed to load cascade classifier from {CASCADE_PATH}.

This usually means:
1. The cascade file is corrupted or incomplete
2. The file was not downloaded properly

To fix this, you can:
1. Download the correct cascade file manually from:
   https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml
   Save it as: {CASCADE_PATH}

2. Or install OpenCV properly which should include the cascade files

3. Or run the download script: python data/download_cascade.py
"""
            raise RuntimeError(error_msg)


_load_model_and_cascade()

def _today_csv_path():
    date = datetime.now().strftime('%d-%m-%Y')
    return os.path.join(ATT_DIR, f'Attendance_{date}.csv')

def _ensure_csv_header(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.isfile(path):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['NAME', 'TIME'])

def _should_log(name: str, cooldown_seconds: int = 60) -> bool:
    now = datetime.now()
    last = _last_logged_at.get(name)
    if last is None or (now - last) > timedelta(seconds=cooldown_seconds):
        return True
    return False

def _write_attendance(name: str):
    path = _today_csv_path()
    _ensure_csv_header(path)
    ts = datetime.now().strftime('%H:%M:%S')
    with open(path, 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([name, ts])
    _last_logged_at[name] = datetime.now()
    print(f"[WRITE] Attendance written: {name} at {ts}")

def recognize_frame(frame, expected_user):
    import cv2

    if _knn is None or _face_cascade is None:
        error_msg = "Model or cascade not loaded"
        if _knn is None and _face_cascade is None:
            error_msg = "Neither model nor cascade loaded. Check data files and cascade file."
        elif _knn is None:
            error_msg = "Face recognition model not loaded. Check faces_data.pkl and names.pkl files."
        elif _face_cascade is None:
            error_msg = "Face detection cascade not loaded. Check haarcascade_frontalface_default.xml file."
        return {"error": error_msg}

    state = _user_states.setdefault(expected_user, {
        'confirm_count': 0,
        'mismatch_count': 0,
        'mismatch_name': None
    })

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(gray, 1.1, 5)

    if len(faces) == 0:
        return {"status": "No face detected"}

    x, y, w, h = faces[0]
    crop = frame[y:y+h, x:x+w, :]
    resized = cv2.resize(crop, (50, 50)).flatten().reshape(1, -1)

    recognized_name = str(_knn.predict(resized)[0])

    if recognized_name.lower().strip() == expected_user.lower().strip():
        state['confirm_count'] += 1
        state['mismatch_count'] = 0
        state['mismatch_name'] = None

        if state['confirm_count'] >= 3:
            if _should_log(expected_user):
                _write_attendance(expected_user)
                state['confirm_count'] = 0
                return {
                    "attendance_recorded": True,
                    "message": f"SUCCESS! Attendance recorded for {expected_user}."
                }
            else:
                return {"status": "Attendance already recorded recently."}
    else:
        state['confirm_count'] = 0
        state['mismatch_count'] += 1
        state['mismatch_name'] = recognized_name

        if state['mismatch_count'] >= 5:
            state['mismatch_count'] = 0
            return {
                "recognition_failed": True,
                "camera_shutdown": True,
                "message": f"SECURITY ALERT! Multiple face mismatches detected. Camera disabled for security. Detected {recognized_name} instead of {expected_user}."
            }

    return {"status": "Recognition in progress"}


# User access control functions
_ALLOWED_USERS_FILE = os.path.join(DATA_DIR, 'allowed_users.pkl')

def _get_allowed_users():
    """Get the list of users allowed to mark attendance."""
    if os.path.exists(_ALLOWED_USERS_FILE):
        try:
            with open(_ALLOWED_USERS_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception:
            pass
    return []

def _add_allowed_user(username):
    """Add a user to the allowed attendance list."""
    allowed_users = _get_allowed_users()
    if username not in allowed_users:
        allowed_users.append(username)
        _save_allowed_users(allowed_users)

def _remove_allowed_user(username):
    """Remove a user from the allowed attendance list."""
    allowed_users = _get_allowed_users()
    if username in allowed_users:
        allowed_users.remove(username)
        _save_allowed_users(allowed_users)

def reset_camera_state(username):
    """Reset camera state for a user after security shutdown (admin only)"""
    if username in _user_states:
        _user_states[username] = {
            'confirm_count': 0,
            'mismatch_count': 0,
            'mismatch_name': None
        }
        print(f"[RESET] Camera state reset for user {username}")
        return True
    return False
