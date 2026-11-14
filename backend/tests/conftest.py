import os

# Keep tests independent of any developer `.env` file.
os.environ.setdefault("SARVAM_API_KEY", "")
