import urllib.request
import os

# Download the Haar cascade file from OpenCV's official repository
url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
filename = "haarcascade_frontalface_default.xml"

print(f"Downloading {filename} from {url}...")

try:
    # Download the file
    urllib.request.urlretrieve(url, filename)
    print(f"✅ Successfully downloaded {filename}")

    # Verify file exists and has content
    if os.path.exists(filename):
        file_size = os.path.getsize(filename)
        print(f"✅ File size: {file_size} bytes")

        if file_size > 1000:  # Real cascade files are much larger than 1KB
            print("✅ File appears to be a valid cascade file!")
            print("✅ Download completed successfully!")

            # Show first few lines to verify it's a real cascade file
            with open(filename, 'r') as f:
                first_lines = ''.join(f.readlines()[:5])
                print(f"✅ File preview: {first_lines[:100]}...")
        else:
            print("❌ Downloaded file is too small - likely not a valid cascade file")
    else:
        print("❌ File was not created")

except Exception as e:
    print(f"❌ Error downloading file: {e}")
