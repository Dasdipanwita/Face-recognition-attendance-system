import cv2
import os

# Test cascade loading
DATA_DIR = os.path.join(os.path.dirname('recognizer.py'), 'data')
CASCADE_PATH = os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml')

print(f'Cascade path: {CASCADE_PATH}')
print(f'File exists: {os.path.exists(CASCADE_PATH)}')

if os.path.exists(CASCADE_PATH):
    print(f'File size: {os.path.getsize(CASCADE_PATH)} bytes')
    cascade = cv2.CascadeClassifier(CASCADE_PATH)
    print(f'Cascade loaded: {not cascade.empty()}')

    if cascade.empty():
        print('ERROR: Cascade classifier is empty!')
        # Let's try to read the first few lines of the file
        with open(CASCADE_PATH, 'r') as f:
            content = f.read(200)
            print(f'File content preview: {content[:200]}')
    else:
        print('SUCCESS: Cascade classifier loaded successfully!')
