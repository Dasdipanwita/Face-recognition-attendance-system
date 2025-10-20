import cv2
import pickle
import numpy as np
import os
import csv
import time
import threading
from datetime import datetime, timedelta
from sklearn.neighbors import KNeighborsClassifier
import traceback

# Thread-safe flags/state
_running_event = threading.Event()
_thread = None
_state_lock = threading.Lock()
_last_logged_at = {}  # name -> datetime
_attendance_recorded = False  # Flag to track if attendance was recorded
_expected_user = None  # Expected user for verification
_recognition_failed = False  # Flag if face doesn't match expected user
_confirm_count = 0  # consecutive confirmation counter
_required_confirm = 3  # require this many consecutive good frames to accept
_mismatch_count = 0  # consecutive mismatch frames
_mismatch_limit = 5  # require this many mismatched frames before failing
_mismatch_name = None  # last mismatched recognized name
_current_frame = None  # Latest frame for video streaming
_frame_lock = threading.Lock()  # Lock for frame access

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ATT_DIR = os.path.join(os.path.dirname(__file__), 'Attendance')
CASCADE_PATH = os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml')

# User Access Control - Only these users can mark attendance
_ALLOWED_USERS = {"Dipanwita Das"}  # Set of users allowed to mark attendance

def _is_user_allowed(name: str) -> bool:
    """Check if a user is allowed to mark attendance"""
    # Always check role - admins are always allowed
    roles_path = os.path.join(DATA_DIR, 'roles.pkl')
    if os.path.isfile(roles_path):
        import pickle
        with open(roles_path, 'rb') as f:
            roles = pickle.load(f)
            # If user is admin, they're always allowed
            if roles.get(name.strip(), 'user') == 'admin':
                return True

    # Allow the user if they're in the allowed list OR if they match the expected user (logged-in user)
    global _expected_user
    if _expected_user and name.strip().lower() == _expected_user.strip().lower():
        return True

    # Otherwise check the allowed users list
    return name.strip() in _ALLOWED_USERS

def _get_allowed_users() -> set:
    """Get the current list of allowed users (including admins)"""
    allowed = _ALLOWED_USERS.copy()

    # Add all admin users to the list
    roles_path = os.path.join(DATA_DIR, 'roles.pkl')
    if os.path.isfile(roles_path):
        import pickle
        with open(roles_path, 'rb') as f:
            roles = pickle.load(f)
            for username, role in roles.items():
                if role == 'admin':
                    allowed.add(username + " (Admin)")

    return allowed

def _add_allowed_user(name: str):
    """Add a user to the allowed list"""
    _ALLOWED_USERS.add(name.strip())

def _remove_allowed_user(name: str):
    """Remove a user from the allowed list"""
    _ALLOWED_USERS.discard(name.strip())


def _today_csv_path():
    date = datetime.now().strftime('%d-%m-%Y')
    return os.path.join(ATT_DIR, f'Attendance_{date}.csv')


def _ensure_csv_header(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.isfile(path):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['NAME', 'TIME'])


def _load_model():
    names_path = os.path.join(DATA_DIR, 'names.pkl')
    faces_path = os.path.join(DATA_DIR, 'faces_data.pkl')
    if not (os.path.isfile(names_path) and os.path.isfile(faces_path)):
        raise FileNotFoundError('names.pkl or faces_data.pkl not found in data/. Add faces first.')
    with open(names_path, 'rb') as f:
        labels = pickle.load(f)
    with open(faces_path, 'rb') as f:
        faces = pickle.load(f)
    if faces.ndim != 2:
        faces = faces.reshape(faces.shape[0], -1)
    knn = KNeighborsClassifier(n_neighbors=3, weights='uniform')  # Optimized parameters
    knn.fit(faces, labels)
    return knn


def _load_cascade():
    """Load the face detection cascade classifier"""
    # Try multiple methods to find the cascade file

    # Method 1: Use OpenCV's built-in data path (recommended for newer OpenCV versions)
    try:
        import cv2
        if hasattr(cv2.data, 'haarcascades'):
            builtin_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(builtin_path):
                print(f"[CASCADE] Using OpenCV built-in cascade: {builtin_path}")
                return cv2.CascadeClassifier(builtin_path)
    except:
        pass

    # Method 2: Try the local data directory path
    if os.path.exists(CASCADE_PATH):
        print(f"[CASCADE] Using local cascade: {CASCADE_PATH}")
        return cv2.CascadeClassifier(CASCADE_PATH)

    # Method 3: Try to download if missing
    try:
        print("[CASCADE] Cascade file not found, attempting to download...")
        import urllib.request
        url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
        urllib.request.urlretrieve(url, CASCADE_PATH)
        print(f"[CASCADE] Downloaded cascade to: {CASCADE_PATH}")
        return cv2.CascadeClassifier(CASCADE_PATH)
    except Exception as e:
        print(f"[CASCADE] Failed to download cascade: {e}")

    # Method 4: Last resort - create a minimal working file
    print("[CASCADE] Creating minimal cascade file...")
    minimal_cascade = """<?xml version="1.0"?>
<opencv_storage>
<cascade type_id="opencv-cascade-classifier">
  <stageType>BOOST</stageType>
  <featureType>HAAR</featureType>
  <height>24</height>
  <width>24</width>
  <stageNum>1</stageNum>
  <stages>
    <stage>
      <maxWeakCount>1</maxWeakCount>
      <stageThreshold>-1.</stageThreshold>
      <weakClassifiers/>
    </stage>
  </stages>
  <features/>
</cascade>
</opencv_storage>"""
    with open(CASCADE_PATH, 'w') as f:
        f.write(minimal_cascade)

    return cv2.CascadeClassifier(CASCADE_PATH)


def _should_log(name: str, cooldown_seconds: int = 60) -> bool:
    now = datetime.now()
    with _state_lock:
        last = _last_logged_at.get(name)
        if last is None or (now - last) > timedelta(seconds=cooldown_seconds):
            _last_logged_at[name] = now
            return True
        return False


def _write_attendance(name: str):
    global _attendance_recorded, _expected_user
    caller = ''.join(traceback.format_stack(limit=6))

    # Check if user is allowed to mark attendance
    if not _is_user_allowed(name):
        print(f"[ACCESS DENIED] User '{name}' is NOT allowed to mark attendance. Only these users are allowed: {_ALLOWED_USERS}")
        print("[ACCESS DENIED] caller stack:\n" + caller)
        return

    # Safety: never write attendance for a different user than the one expected
    if _expected_user is not None and name.lower().strip() != _expected_user.lower().strip():
        print(f"[SECURITY] REFUSED write_attendance('{name}') while expected_user='{_expected_user}'")
        print("[SECURITY] caller stack:\n" + caller)
        return

    path = _today_csv_path()
    _ensure_csv_header(path)
    ts = datetime.now().strftime('%H:%M:%S')
    with _state_lock:
        with open(path, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([name, ts])
        _attendance_recorded = True  # Mark that attendance was recorded
    print(f"[WRITE] Attendance written: {name} at {ts}")
    print("[WRITE] caller stack:\n" + caller)



def _worker_loop():
    global _attendance_recorded, _recognition_failed, _confirm_count, _mismatch_count, _mismatch_name, _current_frame
    try:
        knn = _load_model()
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        _running_event.clear()
        return

    face_cascade = _load_cascade()

    # Verify cascade loaded correctly
    if face_cascade.empty():
        print(f"[ERROR] Failed to load cascade classifier")
        _running_event.clear()
        return
    else:
        print(f"[OK] Cascade classifier loaded successfully")

    # Improved camera initialization with retry logic (cross-platform)
    cap = None
    for attempt in range(3):
        try:
            # Try different backends for cross-platform compatibility
            backends = [0, cv2.CAP_V4L2, cv2.CAP_GSTREAMER, cv2.CAP_ANY]
            for backend in backends:
                cap = cv2.VideoCapture(0 + backend)  # Try different backend IDs
                if cap.isOpened():
                    print(f"[CAMERA] Camera opened successfully with backend {backend}")
                    break
                cap.release()
                cap = None

            if cap is None:
                cap = cv2.VideoCapture(0)  # Fallback to default

            if cap.isOpened():
                # Set camera properties for better performance
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)

                # Read a test frame to ensure camera is working
                test_ret, test_frame = cap.read()
                if test_ret and test_frame is not None:
                    print(f"[CAMERA] Camera initialized successfully on attempt {attempt + 1}")
                    break
                else:
                    print(f"[CAMERA] Camera opened but couldn't read frame on attempt {attempt + 1}")
                    cap.release()
                    cap = None
            else:
                print(f"[CAMERA] Failed to open camera on attempt {attempt + 1}")
        except Exception as e:
            print(f"[CAMERA] Exception during camera init attempt {attempt + 1}: {e}")
            if cap:
                cap.release()
            cap = None

        if attempt < 2:
            time.sleep(0.5)

    if cap is None or not cap.isOpened():
        print("[ERROR] Failed to initialize camera after 3 attempts")
        _running_event.clear()
        return

    try:
        failed_frame_count = 0
        max_failed_frames = 50  # Stop if we can't read 50 consecutive frames

        while _running_event.is_set():
            ok, frame = cap.read()
            if not ok or frame is None:
                failed_frame_count += 1
                print(f"[WARNING] Failed to read frame ({failed_frame_count}/{max_failed_frames})")
                if failed_frame_count >= max_failed_frames:
                    print("[ERROR] Too many failed frame reads. Stopping camera.")
                    _running_event.clear()
                    break
                time.sleep(0.05)
                continue

            # Reset failed frame counter on successful read
            failed_frame_count = 0

            # Create a copy for display
            display_frame = frame.copy()

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Try multiple detection strategies for better results
            faces = []

            # Strategy 1: Very lenient - START AGGRESSIVE (most important fix!)
            gray_eq = cv2.equalizeHist(gray)
            faces = face_cascade.detectMultiScale(gray_eq, scaleFactor=1.05, minNeighbors=2, minSize=(30, 30))

            # Strategy 2: Try without equalization (sometimes better)
            if len(faces) == 0:
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=2, minSize=(30, 30))

            # Strategy 3: Even more aggressive
            if len(faces) == 0:
                faces = face_cascade.detectMultiScale(gray_eq, scaleFactor=1.03, minNeighbors=1, minSize=(20, 20))

            # Strategy 4: Maximum sensitivity
            if len(faces) == 0:
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.02, minNeighbors=1, minSize=(20, 20),
                                                     flags=cv2.CASCADE_SCALE_IMAGE)

            # Display status text when no face detected
            if len(faces) == 0:
                print("[DETECTION] No face detected in current frame")
                cv2.putText(display_frame, "No face detected - please face the camera", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(display_frame, "Ensure good lighting and camera is not blocked", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            else:
                print(f"[DETECTION] {len(faces)} face(s) detected")

                cv2.putText(display_frame, f"Verifying as: {_expected_user}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                # Debug info
                if len(faces) > 1:
                    cv2.putText(display_frame, f"Multiple faces detected ({len(faces)})", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 1)

            # Process only the largest face (closest to camera)
            if len(faces) > 0:
                # Sort by area (w * h) and take the largest
                faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                x, y, w, h = faces[0]  # Use only the largest face

                crop = frame[y:y+h, x:x+w, :]
                # Resize to match training data size (50x50) - keep as BGR to match registration
                resized = cv2.resize(crop, (50, 50)).flatten().reshape(1, -1)

                # Get distances to neighbors
                # Note: n_neighbors in kneighbors() refers to training samples, not unique classes
                distances, indices = knn.kneighbors(resized, n_neighbors=min(5, len(knn._fit_X)))
                all_distances = distances[0]
                # Get the actual class names for each neighbor
                # knn._y contains encoded labels (0, 1, 2), we need to map back to class names
                all_neighbors = []
                for idx in indices[0]:
                    label_idx = knn._y[idx]  # This is 0, 1, or 2
                    class_name = knn.classes_[label_idx]  # Map to actual name
                    all_neighbors.append(str(class_name))

                best_distance = float(all_distances[0])
                recognized_name = str(knn.predict(resized)[0])

                print(f"[DETECTION] Face detected! Recognized as: '{recognized_name}' (distance: {best_distance:.3f})")
                print(f"[VERIFICATION] Expected user: '{_expected_user}'")
                print(f"[NEIGHBORS] Top 5 matches: {list(zip(all_neighbors, [f'{d:.1f}' for d in all_distances]))}")

                # Adaptive threshold based on training data analysis
                # Distance is Euclidean in high-dimensional space, so values are typically 4000-7000
                CONFIDENCE_THRESHOLD = 6000.0  # Must be below this to be considered confident
                VERIFICATION_THRESHOLD = 5500.0  # Must be below this when verifying against expected user

                # Draw rectangle and text on display frame
                color = (0, 255, 0)  # Green by default
                label = recognized_name

                if _expected_user is not None:
                    # More robust verification:
                    # 1. Check if recognized name matches expected user
                    # 2. Check if distance is low enough (confident match)
                    # 3. Check if expected user appears in top matches
                    name_match = (recognized_name.lower().strip() == _expected_user.lower().strip())
                    confident = (best_distance <= CONFIDENCE_THRESHOLD)

                    # Count how many neighbors match expected user
                    expected_matches = sum(1 for n in all_neighbors if n.lower().strip() == _expected_user.lower().strip())
                    total_neighbors = len(all_neighbors)

                    # Additional verification: if recognized name matches, but it's not dominant in neighbors, reject
                    if name_match:
                        # At least 60% of neighbors should be the expected user for high confidence
                        required_matches = max(2, int(total_neighbors * 0.6))  # At least 60% or minimum 2
                        if expected_matches >= required_matches and best_distance <= VERIFICATION_THRESHOLD:
                            match = True
                            confident = True
                        else:
                            print(f"[WEAK MATCH] Only {expected_matches}/{total_neighbors} neighbors match '{_expected_user}' or distance too high ({best_distance:.1f})")
                            match = False
                            confident = False
                    else:
                        match = False

                    if match and confident:
                        _confirm_count += 1
                        _mismatch_count = 0
                        _mismatch_name = None
                        color = (0, 255, 0)  # Green for match
                        label = f"MATCH: {recognized_name} [{_confirm_count}/3]"
                        print(f"[CONFIRM] {_confirm_count}/3 for '{_expected_user}' (distance={best_distance:.3f})")

                        # Add verification status to display
                        status_text = f"Verifying... {_confirm_count}/3 confirmations"
                        cv2.putText(display_frame, status_text, (10, 60),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    else:
                        print(f"[VERIFICATION FAILED] Detected: '{recognized_name}', Expected: '{_expected_user}', Distance: {best_distance:.3f}")
                        _confirm_count = 0
                        _mismatch_count += 1
                        _mismatch_name = recognized_name
                        color = (0, 0, 255)  # Red for mismatch
                        label = f"MISMATCH: Got {recognized_name}, Need {_expected_user}"
                        print(f"[MISMATCH] {_mismatch_count}/{_mismatch_limit} (last mismatch: '{_mismatch_name}')")

                        # Add mismatch warning to display
                        warning_text = f"FACE MISMATCH! Attempt {_mismatch_count}/{_mismatch_limit}"
                        cv2.putText(display_frame, warning_text, (10, 60),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                        if _mismatch_count >= _mismatch_limit:
                            print(f"[VERIFICATION FAILED] Too many mismatches ({_mismatch_count}). Stopping recognition.")
                            _recognition_failed = True
                            _running_event.clear()
                            break

                    if _confirm_count >= 3:
                        if _should_log(_expected_user):
                            print(f"[ATTENDANCE] ✅ Writing attendance for '{_expected_user}'")
                            # Display success message on frame
                            success_frame = display_frame.copy()
                            cv2.putText(success_frame, "VERIFICATION SUCCESS!", (10, display_frame.shape[0] - 50),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)
                            cv2.putText(success_frame, f"Attendance marked for {_expected_user}", (10, display_frame.shape[0] - 20),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            with _frame_lock:
                                _current_frame = success_frame.copy()

                            _write_attendance(_expected_user)
                            time.sleep(1.5)  # Show success message briefly
                            _confirm_count = 0
                            _running_event.clear()
                            break
                        else:
                            print(f"[ATTENDANCE] ⏭️ Skipped (cooldown) for '{_expected_user}'")
                            _confirm_count = 0
                            # Show cooldown message
                            cv2.putText(display_frame, "ATTENDANCE ALREADY MARKED (COOLDOWN)", (10, display_frame.shape[0] - 20),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                            _running_event.clear()
                            break
                else:
                    # No expected user - should not happen with current system
                    # For security, we reject this mode
                    print(f"[SECURITY ERROR] No expected user specified! Stopping recognition.")
                    _confirm_count = 0
                    color = (0, 0, 255)  # Red
                    label = "ERROR: No user specified"
                    _running_event.clear()
                    break

                # Draw rectangle and label on display frame
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(display_frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Store the frame for streaming
            with _frame_lock:
                _current_frame = display_frame.copy()

            if not _running_event.is_set():
                break
            time.sleep(0.03)

    finally:
        try:
            cap.release()
        except Exception:
            pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
def start(expected_user=None) -> dict:
    """Start recognition in background. Returns status dict.

    Args:
        expected_user: The username of the logged-in user. Only this user's face will be accepted.
    """
    global _attendance_recorded, _expected_user, _recognition_failed, _confirm_count, _mismatch_count, _mismatch_name
    print(f"[START] start() called with expected_user={expected_user!r}")

    if _running_event.is_set():
        return {"running": True, "message": "Already running"}

    # Security: Always require an expected user
    if not expected_user or not expected_user.strip():
        print("[SECURITY ERROR] No expected user provided!")
        return {"running": False, "message": "Security error: No user specified"}

    # clear per-session throttles and flags
    with _state_lock:
        _last_logged_at.clear()
        _attendance_recorded = False
        _recognition_failed = False
        _expected_user = expected_user.strip()
        _confirm_count = 0
        _mismatch_count = 0
        _mismatch_name = None

    print(f"\n{'='*60}")
    print(f"[START] Camera started with expected_user: '{expected_user}'")
    print(f"[START] ONLY '{expected_user}' can mark attendance in this session")
    print(f"{'='*60}\n")

    _running_event.set()
    global _thread
    _thread = threading.Thread(target=_worker_loop, daemon=True)
    _thread.start()
    return {"running": True, "message": "Started"}


def stop() -> dict:
    """Stop recognition and wait for thread to finish."""
    _running_event.clear()
    t = None
    global _thread
    t, _thread = _thread, None
    if t is not None:
        t.join(timeout=5)
    return {"running": False, "message": "Stopped"}

def status() -> dict:
    return {
        "running": _running_event.is_set(),
        "attendance_recorded": _attendance_recorded,
        "recognition_failed": _recognition_failed,
        "expected_user": _expected_user,
        "mismatch_name": _mismatch_name,
        "mismatch_count": _mismatch_count,
        "allowed_users": list(_ALLOWED_USERS)
    }

def get_last_attendance() -> dict:
    """Get the last recorded attendance name and time"""
    with _state_lock:
        if _last_logged_at:
            # Get the most recent entry
            last_name = max(_last_logged_at.items(), key=lambda x: x[1])
            return {
                "name": last_name[0],
                "time": last_name[1].strftime('%H:%M:%S')
            }
    return None

def clear_flags():
    """Clear attendance_recorded and recognition_failed flags"""
    global _attendance_recorded, _recognition_failed, _mismatch_count, _mismatch_name
    with _state_lock:
        _attendance_recorded = False
        _recognition_failed = False
        _mismatch_count = 0
        _mismatch_name = None

def get_current_frame():
    """Get the current video frame for streaming"""
    with _frame_lock:
        if _current_frame is not None:
            return _current_frame.copy()
        return None