# Face Recognition Attendance System

## Overview
This project is a Face Recognition Attendance System that uses facial recognition technology to mark attendance. It is designed to be user-friendly and efficient, making it suitable for schools, offices, and other organizations.

## Features
- **User Registration**: Register users with their facial data.
- **Face Recognition**: Recognize faces in real-time to mark attendance.
- **Admin Dashboard**: Manage users, view attendance history, and more.
- **Attendance Reports**: Generate attendance reports for specific dates.
- **Secure Login**: Role-based authentication for admins and users.

## Project Structure
```
app.py                     # Main application entry point
check_data.py              # Utility to check data integrity
check_roles.py             # Role management utilities
check_templates.py         # Template validation utilities
comprehensive_test.py      # Comprehensive testing script
debug_login_sim.py         # Debugging login logic
debug_register.py          # Debugging registration logic
debug_users.py             # Debugging user management
recognizer.py              # Face recognition logic
registration.py            # User registration logic
requirements.txt           # Python dependencies
runtime.txt                # Runtime environment configuration
static/                    # Static files (CSS, JS, etc.)
templates/                 # HTML templates
Attendance/                # Attendance records
config/                    # Configuration files
data/                      # Data files (e.g., cascades)
scripts/                   # Helper scripts
```

## Prerequisites
- Python 3.8 or higher
- OpenCV
- Flask
- Other dependencies listed in `requirements.txt`

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/Face-recognition-attendance-system.git
   ```
2. Navigate to the project directory:
   ```bash
   cd Face-recognition-attendance-system
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. Run the application:
   ```bash
   python app.py
   ```
2. Open your browser and navigate to `http://127.0.0.1:5000`.
3. Use the admin credentials to log in and manage the system.

## File Descriptions
- **`app.py`**: The main entry point for the application.
- **`recognizer.py`**: Contains the logic for face recognition.
- **`registration.py`**: Handles user registration.
- **`templates/`**: HTML templates for the web interface.
- **`static/`**: Static files like CSS and JavaScript.
- **`Attendance/`**: Stores attendance records in CSV format.

## Contributing
Contributions are welcome! Please fork the repository and create a pull request with your changes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments
- OpenCV for face detection and recognition.
- Flask for the web framework.
- Contributors and the open-source community.