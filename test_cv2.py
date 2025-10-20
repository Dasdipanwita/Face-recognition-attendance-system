import cv2
print(f"OpenCV version: {cv2.__version__}")
print(f"OpenCV imported successfully from: {cv2.__file__}")

# Test if CascadeClassifier is available
try:
    cascade = cv2.CascadeClassifier()
    print("✅ CascadeClassifier is available")
except Exception as e:
    print(f"❌ CascadeClassifier error: {e}")

# Test if the data module is available
try:
    import cv2.data
    print(f"✅ cv2.data available: {cv2.data.haarcascades}")
except Exception as e:
    print(f"❌ cv2.data error: {e}")
