# How to Use the Face Recognition Attendance System

## IMPORTANT: This is a Web Application!

The camera feed appears in your **web browser**, NOT as a separate window.

## Step-by-Step Instructions

### STEP 1: Start the Server

Open Command Prompt or Terminal and run:

```bash
cd "D:\OneDrive\Desktop\ML based project\face_recognition_project"
python main.py
```

**You should see:**
```
* Serving Flask app 'main'
* Running on http://127.0.0.1:8000
```

**Leave this window open!** Don't close it. This is the server running.

---

### STEP 2: Open Your Web Browser

1. Open **Google Chrome**, **Firefox**, or **Edge**
2. In the address bar, type: `http://localhost:8000`
3. Press Enter

**You should see:** The Face Attendance home page

---

### STEP 3: Register Your Face (First Time Only)

If this is your first time:

1. Click **"Register"** button
2. Enter your name (example: "John Doe")
3. Select role: "user" or "admin"
4. Click **"Start Registration"**
5. **LOOK AT YOUR BROWSER** - you'll see the camera feed there
6. Position your face in front of the camera
7. Wait for 100 samples to be collected (progress shows on screen)
8. When done, it will say "Registration completed"

**Important:**
- Camera feed appears IN THE BROWSER window
- NOT a separate camera window
- Keep looking at the browser page

---

### STEP 4: Login

1. Click **"Login"** link
2. Enter your name (same as registration)
3. For regular users: No password needed
4. For admin: Password is "admin123"
5. Click **"Login"**

---

### STEP 5: Mark Attendance

1. After login, click **"Camera"** in the navigation menu
2. You'll see the camera control page
3. Click **"Start Camera"** button
4. **LOOK AT YOUR BROWSER** - camera feed appears below the button
5. Position your face in front of the camera
6. System will verify your identity:
   - Shows "Verifying as: [Your Name]"
   - If match: Green box around face with "MATCH: [Name] [1/3]"
   - Progress increases: [2/3], then [3/3]
   - After 3 matches: **Green popup appears!**
   - "Verification Successful!" message
   - Attendance is marked automatically
   - Camera stops

**If verification fails:**
- Red box appears: "MISMATCH: Got [X], Need [Y]"
- After 5 mismatches: **Red popup appears**
- "Verification Failed!" message
- Camera stops, no attendance marked

---

## Common Confusions Explained

### "Nothing happens when I run main.py"

**This is NORMAL!** The app doesn't open a window automatically.

After running `python main.py`:
1. You see messages in terminal (server is running)
2. **YOU** need to open a web browser
3. **YOU** need to type `http://localhost:8000` in the address bar
4. THEN you'll see the website

Think of it like this:
- `python main.py` = Start the server (like turning on a TV)
- Opening browser = Turn on your remote control
- Typing `http://localhost:8000` = Change to the right channel

### "Where is the camera window?"

**There is NO separate camera window!**

The camera feed appears:
- In your **web browser**
- On the **same page** where you clicked "Start Camera"
- **Below** the Start/Stop buttons
- As a video stream on the webpage

### "I don't see my face"

Make sure:
1. You clicked "Start Camera" button
2. You're looking at the **browser window** (not terminal)
3. You scrolled down on the page (camera feed is below buttons)
4. Your browser has camera permissions
5. No other app is using your camera

---

## Browser Camera Permissions

### Chrome:
1. When you first start camera, Chrome will ask for permission
2. A popup appears at top of browser: "Allow localhost to use camera?"
3. Click **"Allow"**

### Firefox:
1. Firefox asks: "Share your camera with localhost?"
2. Click dropdown, select your camera
3. Click **"Allow"**

### Edge:
1. Edge asks: "Allow localhost to access your camera?"
2. Click **"Allow"**

**If you accidentally clicked "Block":**

**Chrome:**
1. Click the lock icon (🔒) in address bar
2. Find "Camera" setting
3. Change to "Allow"
4. Refresh page

**Firefox:**
1. Click the camera icon in address bar
2. Click "X" to remove block
3. Refresh page

**Edge:**
1. Click lock icon in address bar
2. Change Camera to "Allow"
3. Refresh page

---

## Testing the System

### Quick Test (Without Web Interface):

To test if camera and face detection work at basic level:

```bash
cd "D:\OneDrive\Desktop\ML based project\face_recognition_project"
python simple_test.py
```

This opens a **separate window** (not browser) to test camera.
- Green box = Face detected
- Press 'q' to quit

### Full Test (Web Interface):

1. Start server: `python main.py`
2. Open browser: `http://localhost:8000`
3. Register yourself
4. Login
5. Go to Camera page
6. Click Start Camera
7. Watch the browser page for camera feed

---

## Troubleshooting

### "Cannot access http://localhost:8000"

**Make sure:**
- `python main.py` is still running (check terminal)
- You typed the address correctly
- Port 8000 is not blocked by firewall

**Try:**
- `http://127.0.0.1:8000` instead
- Close and restart browser
- Check if another app is using port 8000

### "Camera feed not appearing in browser"

1. Click F12 in browser to open Developer Tools
2. Look at Console tab
3. Check for error messages
4. Common issues:
   - Browser blocked camera access
   - Another app is using camera
   - Camera not connected

**Fix:**
- Allow camera in browser settings
- Close Zoom/Teams/Skype
- Check camera in Windows Camera app

### "Face not detected in browser"

See the file: `CAMERA_NOT_DETECTING_FIX.md`

### "Server won't start"

**Error: "Address already in use"**
- Another instance is already running
- Close other terminals running `python main.py`
- Or change port in main.py (line 456)

**Error: "Module not found"**
```bash
pip install flask flask-cors opencv-python scikit-learn numpy
```

---

## What You Should See At Each Step

### Starting Server:
```
Terminal:
* Serving Flask app 'main'
* Running on http://127.0.0.1:8000
```

### Opening Browser:
```
Browser shows:
┌─────────────────────────┐
│ Face Attendance         │
│ ├ Home                  │
│ ├ Register              │
│ └ Login                 │
│                         │
│ Welcome to Face         │
│ Attendance System       │
│                         │
│ [Register] [Login]      │
└─────────────────────────┘
```

### Starting Camera:
```
Browser shows:
┌─────────────────────────┐
│ Face Recognition Camera │
│                         │
│ ● Camera Running        │
│                         │
│ [Stop Camera]           │
│                         │
│ ┌─────────────────────┐ │
│ │                     │ │
│ │  [VIDEO FEED HERE]  │ │
│ │  (You see yourself) │ │
│ │                     │ │
│ └─────────────────────┘ │
│                         │
│ Verifying as: YourName  │
│ MATCH: YourName [1/3]   │
└─────────────────────────┘
```

---

## Summary

**Remember:**
1. Run `python main.py` in terminal → Server starts
2. Open web browser → Type `http://localhost:8000`
3. Everything happens IN THE BROWSER (registration, camera, verification)
4. Camera feed appears on the webpage, not a separate window
5. Look at the browser to see your face and verification status

**The system is a WEB APPLICATION, not a desktop application!**
