from flask import Flask, render_template, url_for, jsonify, Response, request, redirect, flash, session
from functools import wraps
import csv
import json
import os
import time
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

import recognizer  # local module controlling webcam recognizer thread
import registration  # local module for user registration

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'  # Required for flash messages

# Default admin credentials (change in production!)
ADMIN_USERNAME = 'admin'
ADMIN_DEFAULT_PASSWORD = 'admin123'
ADMIN_CREDS_PATH = os.path.join(os.path.dirname(__file__), 'config', 'admin_credentials.json')
ADMIN_PASSWORD_MIN_LENGTH = 8

ATT_DIR = os.path.join(os.path.dirname(__file__), 'Attendance')


def _ensure_admin_credentials_file():
    """Create the admin credentials file with default values if it is missing or invalid."""
    config_dir = os.path.dirname(ADMIN_CREDS_PATH)
    os.makedirs(config_dir, exist_ok=True)

    # New format: store passwords for multiple admins
    default_payload = {
        'admins': {}  # Format: {username: {password_hash, last_updated}}
    }

    if not os.path.isfile(ADMIN_CREDS_PATH):
        with open(ADMIN_CREDS_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_payload, f, indent=2)
        return

    try:
        with open(ADMIN_CREDS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = None

    # Migrate old format to new format
    if data and 'username' in data and 'password_hash' in data:
        # Old format detected, migrate to new format
        old_username = data.get('username', ADMIN_USERNAME)
        old_password_hash = data.get('password_hash')
        new_data = {
            'admins': {
                old_username: {
                    'password_hash': old_password_hash,
                    'last_updated': data.get('last_updated', datetime.now().isoformat())
                }
            }
        }
        with open(ADMIN_CREDS_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2)
    elif not data or 'admins' not in data:
        # Invalid or missing data, create new structure
        with open(ADMIN_CREDS_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_payload, f, indent=2)


def load_admin_credentials():
    """Return all admin credentials as a dictionary {username: password_hash}."""
    _ensure_admin_credentials_file()
    with open(ADMIN_CREDS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    admins = data.get('admins', {})
    # Return a dict with {username: password_hash}
    return {username: admin_data['password_hash'] for username, admin_data in admins.items()}


def get_admin_password_hash(username):
    """Get the password hash for a specific admin user. Returns None if not found."""
    _ensure_admin_credentials_file()
    with open(ADMIN_CREDS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    admins = data.get('admins', {})
    admin_data = admins.get(username)

    if admin_data:
        return admin_data['password_hash']

    # If admin not found, create default password for them
    default_hash = generate_password_hash(ADMIN_DEFAULT_PASSWORD)
    admins[username] = {
        'password_hash': default_hash,
        'last_updated': datetime.now().isoformat()
    }
    data['admins'] = admins
    with open(ADMIN_CREDS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    return default_hash


def update_admin_password(username, new_password):
    """Persist a freshly hashed admin password for a specific admin user."""
    _ensure_admin_credentials_file()
    with open(ADMIN_CREDS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    admins = data.get('admins', {})
    admins[username] = {
        'password_hash': generate_password_hash(new_password),
        'last_updated': datetime.now().isoformat()
    }
    data['admins'] = admins

    with open(ADMIN_CREDS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


# Create default credentials on startup
load_admin_credentials()


# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('user_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def today_filename():
    ts = datetime.now()
    date = ts.strftime('%d-%m-%Y')
    return f'Attendance_{date}.csv'


def read_csv_rows(path):
    rows = []
    if not os.path.isfile(path):
        return rows
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = [row for row in reader if row]
    # strip header if present
    if rows and rows[0] and rows[0][0].lower() == 'name':
        rows = rows[1:]
    return rows


@app.context_processor
def inject_year():
    return {'year': datetime.now().year}


@app.route('/')
def home():
    if 'username' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return render_template('index.html', title='Face Attendance')


# --- Authentication routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to appropriate dashboard
    if 'username' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Check if user is registered
        import pickle
        base_dir = os.path.dirname(__file__)
        names_path = os.path.join(base_dir, 'data', 'names.pkl')
        roles_path = os.path.join(base_dir, 'data', 'roles.pkl')

        # Load registered names if available
        if os.path.isfile(names_path):
            try:
                with open(names_path, 'rb') as f:
                    registered_names = list(pickle.load(f))
            except Exception:
                registered_names = []
        else:
            registered_names = []

        # Case-insensitive username lookup in registered names
        matched_name = None
        for name in registered_names:
            try:
                if str(name).lower().strip() == username.lower().strip():
                    matched_name = name
                    break
            except Exception:
                continue

        # If not found in names.pkl, check roles.pkl for an admin match
        if not matched_name and os.path.isfile(roles_path):
            try:
                with open(roles_path, 'rb') as f:
                    roles = pickle.load(f)
                for role_name, role_value in roles.items():
                    if str(role_name).lower().strip() == username.lower().strip() and str(role_value).lower() == 'admin':
                        matched_name = role_name
                        break
            except Exception:
                pass

        if matched_name:
            # Determine role from roles.pkl if present
            user_role = 'user'
            if os.path.isfile(roles_path):
                try:
                    with open(roles_path, 'rb') as f:
                        roles = pickle.load(f)
                    user_role = roles.get(matched_name, 'user')
                except Exception:
                    user_role = 'user'

            try:
                user_role = str(user_role).lower()
            except Exception:
                user_role = 'user'

            # For admin users, verify password
            if user_role == 'admin':
                stored_hash = get_admin_password_hash(matched_name)
                if not check_password_hash(stored_hash, password):
                    flash('Invalid password for admin user', 'error')
                    return render_template('login.html', title='Login')

            session['username'] = matched_name
            session['role'] = user_role

            if user_role == 'admin':
                flash(f'Welcome Admin {matched_name}!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash(f'Welcome {matched_name}!', 'success')
                return redirect(url_for('user_dashboard'))

        flash('User not registered. Please register first.', 'error')

    return render_template('login.html', title='Login')


@app.route('/logout')
def logout():
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye {username}! You have been logged out.', 'info')
    return redirect(url_for('login'))
    # If already logged in, redirect to appropriate dashboard

@app.route('/admin/change-password', methods=['GET', 'POST'])
@admin_required
def change_admin_password():
    username = session.get('username')

    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        # Load registered names if available
        if os.path.isfile(names_path):
            try:
                with open(names_path, 'rb') as f:
                    registered_names = list(pickle.load(f))
            except Exception:
                registered_names = []
        else:
            registered_names = []
        if not check_password_hash(stored_hash, current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('change_password.html', title='Change Password', min_length=ADMIN_PASSWORD_MIN_LENGTH)

        # Validate new password
        if len(new_password) < ADMIN_PASSWORD_MIN_LENGTH:
            flash(f'New password must be at least {ADMIN_PASSWORD_MIN_LENGTH} characters long.', 'error')
            return render_template('change_password.html', title='Change Password', min_length=ADMIN_PASSWORD_MIN_LENGTH)

        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'error')
            return render_template('change_password.html', title='Change Password', min_length=ADMIN_PASSWORD_MIN_LENGTH)

        update_admin_password(username, new_password)
        flash('Admin password updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('change_password.html', title='Change Password', min_length=ADMIN_PASSWORD_MIN_LENGTH)


# --- Dashboard routes ---
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', title='Admin Dashboard', username=session.get('username'))


@app.route('/user/dashboard')
@login_required
def user_dashboard():
    return render_template('user_dashboard.html', title='My Dashboard', username=session.get('username'))


@app.route('/user/my-attendance')
@login_required
def user_my_attendance():
    username = session.get('username')
    date_str = datetime.now().strftime('%d-%m-%Y')
    path = os.path.join(ATT_DIR, today_filename())
    error = None
    my_records = []

    try:
        all_records = read_csv_rows(path)
        # Filter records for current user
        my_records = [row for row in all_records if row and row[0] == username]
    except Exception as e:
        error = f'Failed to read file: {e}'

    return render_template('user_attendance.html', title='My Attendance', date=date_str, records=my_records, error=error, username=username)


@app.route('/attendance/today')
@admin_required
def attendance_today():
    date_str = datetime.now().strftime('%d-%m-%Y')
    path = os.path.join(ATT_DIR, today_filename())
    error = None
    records = []
    try:
        records = read_csv_rows(path)
    except Exception as e:
        error = f'Failed to read file: {e}'
    return render_template('attendance_today.html', title='Today', date=date_str, records=records, error=error)


@app.route('/attendance/history')
@admin_required
def attendance_history():
    files = []
    if os.path.isdir(ATT_DIR):
        for name in os.listdir(ATT_DIR):
            if name.lower().endswith('.csv') and name.startswith('Attendance_'):
                files.append(name.replace('Attendance_', '').replace('.csv', ''))
        files.sort(key=lambda d: datetime.strptime(d, '%d-%m-%Y'), reverse=True)
    return render_template('attendance_history.html', title='History', files=files)


@app.route('/attendance/<date>')
@admin_required
def attendance_by_date(date):
    # expected date format: DD-MM-YYYY
    path = os.path.join(ATT_DIR, f'Attendance_{date}.csv')
    error = None
    records = []
    try:
        records = read_csv_rows(path)
    except Exception as e:
        error = f'Failed to read file: {e}'
    return render_template('attendance_today.html', title=f'Attendance {date}', date=date, records=records, error=error)


# --- Recognizer control endpoints ---
@app.route('/recognizer')
@login_required
def recognizer_control():
    username = session.get('username')
    return render_template('recognizer.html', title='Recognizer', username=username)


@app.route('/detect', methods=['POST'])
@login_required
def detect():
    try:
        data = request.get_json()
        image_data = data['image'].split(',')[1]
        username = session.get('username')

        import base64
        import numpy as np
        import cv2

        # Decode the image
        img_bytes = base64.b64decode(image_data)
        img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)

        if frame is None:
            print("[ERROR] Failed to decode image")
            return jsonify({"match": False, "message": "Failed to decode image"}), 500

        # Process the frame
        result = recognizer.recognize_frame(frame, username)

        # Map recognizer responses to the new schema
        if result.get("attendance_recorded"):
            return jsonify({"match": True, "message": result.get("message", "Attendance recorded")})
        if result.get("recognition_failed"):
            # Check if camera should be shut down due to security alert
            if result.get("camera_shutdown"):
                print(f"[SECURITY] Camera shutdown triggered for user {username}")
                return jsonify({
                    "match": False,
                    "message": result.get("message", "Face not recognized"),
                    "camera_shutdown": True
                })
            else:
                return jsonify({"match": False, "message": result.get("message", "Face not recognized")})

        # For intermediate statuses, keep feeding frames
        return jsonify({
            "match": False,
            "message": result.get("status", "Recognition in progress")
        })
    except Exception as e:
        print(f"[ERROR] detect: {e}")
        return jsonify({"match": False, "message": str(e)}), 500


# --- SSE stream for live attendance ---
@app.route('/stream/attendance')
def stream_attendance():
    # Server-Sent Events that emits the latest N lines whenever file changes
    def gen():
        path = os.path.join(ATT_DIR, today_filename())
        last_size = 0
        while True:
            try:
                if os.path.isfile(path):
                    size = os.path.getsize(path)
                    if size != last_size:
                        last_size = size
                        rows = read_csv_rows(path)
                        payload = {"rows": rows[-20:]}  # last 20
                        yield f"data: {payload}\n\n"
            except Exception as e:
                yield f"data: {{'error': '{str(e)}'}}\n\n"
            time.sleep(1)
    return Response(gen(), mimetype='text/event-stream')


# --- Registration endpoints ---
@app.route('/register')
def register_page():
    progress = registration.get_progress()
    return render_template('register.html', title='Register New User', progress=progress)


@app.route('/register/start', methods=['POST'])
def register_start():
    name = request.form.get('name', '').strip()
    role = request.form.get('role', 'user').strip()

    if not name:
        flash('Please enter your name', 'error')
        return redirect(url_for('register_page'))

    # Only allow admin to register admin users
    if role == 'admin' and session.get('role') != 'admin':
        flash('Only admins can register admin users', 'error')
        return redirect(url_for('register_page'))

    result = registration.start_registration(name, role)
    if result['success']:
        role_text = 'admin' if role == 'admin' else 'user'
        flash(f'Registration started for {name} as {role_text}. Please look at the camera.', 'info')
    else:
        flash(result['message'], 'error')

    return redirect(url_for('register_page'))


@app.route('/register/stop', methods=['POST'])
def register_stop():
    registration.stop_registration()
    flash('Registration stopped', 'info')
    return redirect(url_for('register_page'))


@app.route('/register/progress')
def register_progress():
    return jsonify(registration.get_progress())


@app.route('/registration_feed')
def registration_feed():
    """Stream video frames from the registration camera"""
    def generate():
        import cv2
        while True:
            frame = registration.get_registration_frame()
            if frame is not None:
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.033)  # ~30 FPS

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


# --- User Access Control endpoints ---
@app.route('/admin/allowed-users')
@admin_required
def manage_allowed_users():
    """Admin page to manage which users can mark attendance"""
    allowed_users = recognizer._get_allowed_users()
    return render_template('manage_users.html', title='Manage Allowed Users', allowed_users=allowed_users)


@app.route('/admin/allowed-users/add', methods=['POST'])
@admin_required
def add_allowed_user():
    """Add a user to the allowed attendance list"""
    username = request.form.get('username', '').strip()
    if not username:
        flash('Please enter a username', 'error')
        return redirect(url_for('manage_allowed_users'))

    recognizer._add_allowed_user(username)
    flash(f'User "{username}" added to allowed list', 'success')
    return redirect(url_for('manage_allowed_users'))


@app.route('/admin/allowed-users/remove', methods=['POST'])
@admin_required
def remove_allowed_user():
    """Remove a user from the allowed attendance list"""
    username = request.form.get('username', '').strip()

    # Remove "(Admin)" suffix if present
    if username.endswith(" (Admin)"):
        flash('Admin users cannot be removed from the allowed list. They have permanent access.', 'error')
        return redirect(url_for('manage_allowed_users'))

    recognizer._remove_allowed_user(username)
    flash(f'User "{username}" removed from allowed list', 'success')
    return redirect(url_for('manage_allowed_users'))


@app.route('/admin/reset-camera/<username>', methods=['POST'])
@admin_required
def reset_camera_state(username):
    """Reset camera state for a user after security shutdown"""
    success = recognizer.reset_camera_state(username)
    if success:
        flash(f'Camera state reset for user "{username}". They can now use face recognition again.', 'success')
    else:
        flash(f'Failed to reset camera state for user "{username}". User may not exist or may not have an active camera session.', 'error')
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, threaded=True)