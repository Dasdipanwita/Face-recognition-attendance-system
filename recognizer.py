import pickle
import numpy as np
import os
import csv
import time
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from sklearn.neighbors import KNeighborsClassifier

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ATT_DIR = os.path.join(os.path.dirname(__file__), 'Attendance')
CASCADE_PATH = os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml')
DEFAULT_TIMEZONE_NAME = 'Asia/Kolkata'

# In-memory state for each user
_user_states = {}
_last_logged_at = {}


def _fallback_timezone(tz_name):
    if tz_name == 'Asia/Kolkata':
        return timezone(timedelta(hours=5, minutes=30), name='IST')
    return None


def _get_app_timezone():
    """Return a tzinfo to use for timestamps.
    Priority: APP_TIMEZONE env var (IANA name) -> TZ env var -> default app timezone -> system local tz -> UTC
    """
    tz_name = os.environ.get('APP_TIMEZONE') or os.environ.get('TZ') or DEFAULT_TIMEZONE_NAME
    if tz_name:
        if ZoneInfo:
            try:
                return ZoneInfo(tz_name)
            except Exception:
                pass
        fallback_tz = _fallback_timezone(tz_name)
        if fallback_tz is not None:
            return fallback_tz

    try:
        return datetime.now().astimezone().tzinfo or timezone.utc
    except Exception:
        return timezone.utc

# Load model and cascade once on startup
_knn = None
_face_cascade = None

def _load_model_and_cascade():
    global _knn, _face_cascade
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

        # Normalize types
        try:
            labels = list(labels)
        except Exception:
            labels = [str(x) for x in labels]

        faces = np.asarray(faces)
        if faces.ndim != 2:
            faces = faces.reshape(faces.shape[0], -1)

        # If counts mismatch, trim to the smaller length and persist fix
        n_labels = len(labels)
        n_faces = faces.shape[0] if faces.ndim >= 1 else 0
        if n_labels != n_faces:
            m = min(n_labels, n_faces)
            print(f"⚠️  Mismatch: {n_faces} face samples vs {n_labels} labels. Trimming to {m} entries.")
            try:
                labels = labels[:m]
                faces = faces[:m]
                with open(names_path, 'wb') as f:
                    pickle.dump(labels, f)
                with open(faces_path, 'wb') as f:
                    pickle.dump(faces, f)
                print("✅ Trimmed and saved corrected `names.pkl` and `faces_data.pkl`")
            except Exception as e:
                print(f"⚠️  Failed to persist trimmed data: {e}")

        # Fit KNN
        try:
            knn = KNeighborsClassifier(n_neighbors=3)
            knn.fit(faces, labels)
            _knn = knn
        except Exception as e:
            raise RuntimeError(f"Failed to fit recognition model: {e}")

    # Load cascade
    cascade_loaded = False
    try:
        _face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
        if not _face_cascade.empty():
            cascade_loaded = True
    except Exception:
        pass

    if not cascade_loaded:
        # Try OpenCV builtin
        try:
            builtin_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            _face_cascade = cv2.CascadeClassifier(builtin_path)
            if not _face_cascade.empty():
                cascade_loaded = True
        except Exception:
            pass

    if not cascade_loaded:
        error_msg = f"Failed to load cascade classifier from {CASCADE_PATH}.\n" \
                    "Ensure the file exists or install OpenCV's haarcascades.\n" \
                    f"You can download it from: https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml\n"
        raise RuntimeError(error_msg)


try:
    _load_model_and_cascade()
except Exception as _startup_err:
    print(f"[WARN] Could not load face recognition model on startup: {_startup_err}")
    print("[WARN] Face recognition will be unavailable until data files are present in data/.")

def _today_csv_path():
    tz = _get_app_timezone()
    date = datetime.now(tz).strftime('%d-%m-%Y')
    return os.path.join(ATT_DIR, f'Attendance_{date}.csv')

def _ensure_csv_header(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.isfile(path):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['NAME', 'TIME'])

def _should_log(name: str, cooldown_seconds: int = 60) -> bool:
    now = datetime.now(_get_app_timezone())
    last = _last_logged_at.get(name)
    if last is None or (now - last) > timedelta(seconds=cooldown_seconds):
        return True
    return False

def _write_attendance(name: str):
    path = _today_csv_path()
    _ensure_csv_header(path)
    now = datetime.now(_get_app_timezone())
    ts = now.strftime('%H:%M:%S')
    with open(path, 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([name, ts])
    _last_logged_at[name] = now
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
            # Before writing attendance, verify user is allowed
            if not _is_user_allowed(expected_user):
                state['confirm_count'] = 0
                return {
                    "attendance_denied": True,
                    "message": f"Access denied. {expected_user} is not allowed to mark attendance. Please request access from an admin."
                }

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
_ACCESS_REQUESTS_FILE = os.path.join(DATA_DIR, 'access_requests.pkl')

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


def _save_allowed_users(users):
    """Persist the allowed users list to disk."""
    try:
        os.makedirs(os.path.dirname(_ALLOWED_USERS_FILE), exist_ok=True)
        with open(_ALLOWED_USERS_FILE, 'wb') as f:
            pickle.dump(users, f)
    except Exception:
        pass


def _is_user_allowed(username: str) -> bool:
    """Return True if username is allowed to mark attendance (in allowed list or an admin)."""
    # Exact-match check (case-insensitive)
    allowed = _get_allowed_users()
    for u in allowed:
        try:
            if str(u).lower().strip() == str(username).lower().strip():
                return True
        except Exception:
            continue

    # Check roles.pkl for admin role
    roles_path = os.path.join(DATA_DIR, 'roles.pkl')
    if os.path.isfile(roles_path):
        try:
            with open(roles_path, 'rb') as f:
                roles = pickle.load(f)
            role = roles.get(username)
            if role and str(role).lower().strip() == 'admin':
                return True
        except Exception:
            pass

    return False


def _get_access_requests():
    """Return list of pending access request usernames."""
    if os.path.exists(_ACCESS_REQUESTS_FILE):
        try:
            with open(_ACCESS_REQUESTS_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception:
            pass
    return []


def _add_access_request(username: str):
    """Add a user's request to be allowed. Avoid duplicates."""
    requests = _get_access_requests()
    for r in requests:
        try:
            if str(r).lower().strip() == str(username).lower().strip():
                return
        except Exception:
            continue
    requests.append(username)
    try:
        os.makedirs(os.path.dirname(_ACCESS_REQUESTS_FILE), exist_ok=True)
        with open(_ACCESS_REQUESTS_FILE, 'wb') as f:
            pickle.dump(requests, f)
    except Exception:
        pass


def _remove_access_request(username: str):
    requests = _get_access_requests()
    cleaned = [r for r in requests if not (str(r).lower().strip() == str(username).lower().strip())]
    try:
        os.makedirs(os.path.dirname(_ACCESS_REQUESTS_FILE), exist_ok=True)
        with open(_ACCESS_REQUESTS_FILE, 'wb') as f:
            pickle.dump(cleaned, f)
    except Exception:
        pass

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
