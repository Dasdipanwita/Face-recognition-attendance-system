import urllib.request
import os

# Download the Haar cascade file
url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
filename = "haarcascade_frontalface_default.xml"

print(f"Downloading {filename}...")
try:
    urllib.request.urlretrieve(url, filename)
    print(f"✅ Successfully downloaded {filename}")

    # Verify file exists and has content
    if os.path.exists(filename):
        file_size = os.path.getsize(filename)
        print(f"✅ File size: {file_size} bytes")
        if file_size > 0:
            print("✅ File downloaded successfully!")
        else:
            print("❌ Downloaded file is empty")
    else:
        print("❌ File was not created")

except Exception as e:
    print(f"❌ Error downloading file: {e}")
