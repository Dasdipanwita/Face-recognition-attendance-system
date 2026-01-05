import urllib.request
import os

DATA_DIR = os.path.dirname(__file__)
url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
filename = os.path.join(DATA_DIR, "haarcascade_frontalface_default.xml")

print(f"Downloading to {filename}...")
try:
    urllib.request.urlretrieve(url, filename)
    size = os.path.getsize(filename)
    print(f"Downloaded {filename} ({size} bytes)")
    if size > 1000:
        print("File appears valid")
    else:
        print("Warning: file size is small")
except Exception as e:
    print('Download error:', e)
