import os
import sys
import boto3
import mimetypes
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv

load_dotenv()

# Required environment variables
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")
ENDPOINT_URL = os.getenv("ENDPOINT_URL")           # e.g. https://storage.company.internal
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS")     # e.g. https://mforcoding.nxtgen.ai (used for bucket CORS)
IMAGE_DIR = os.getenv("IMAGE_DIR", "Authflow")
PUBLIC_UPLOAD = os.getenv("PUBLIC_UPLOAD", "true").lower() in ("1", "true", "yes")

if not (ACCESS_KEY and SECRET_KEY and BUCKET_NAME and ENDPOINT_URL):
    print("Error: ACCESS_KEY, SECRET_KEY, BUCKET_NAME and ENDPOINT_URL must be set in environment.")
    sys.exit(1)

# Create boto3 session + s3 client for S3-compatible endpoint
session = boto3.session.Session(
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
)
s3_client = session.client("s3", endpoint_url=ENDPOINT_URL)

# Helper to construct public object URL in path-style (common for custom clouds)
def build_object_url(endpoint_url: str, bucket: str, key: str) -> str:
    parsed = urlparse(endpoint_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    # If endpoint contains a path (rare), preserve it
    if parsed.path and parsed.path != "/":
        base = base.rstrip("/") + parsed.path
    # Default to path-style: https://endpoint/<bucket>/<key>
    return urljoin(base.rstrip("/") + "/", f"{bucket}/{key}")

# Attempt to list directory
try:
    files = os.listdir(IMAGE_DIR)
except FileNotFoundError:
    print(f"Error: The directory '{IMAGE_DIR}' was not found.")
    sys.exit(1)

uploaded = []
for fname in files:
    if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
        continue

    file_path = os.path.join(IMAGE_DIR, fname)
    key = fname  # change if you require folder or unique naming e.g. f"uploads/{uuid4()}_{fname}"

    # Determine content type
    content_type, _ = mimetypes.guess_type(file_path)
    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    # Some internal clouds don't support ACLs; set only if PUBLIC_UPLOAD True
    if PUBLIC_UPLOAD:
        extra_args["ACL"] = "public-read"

    try:
        s3_client.upload_file(file_path, BUCKET_NAME, key, ExtraArgs=extra_args if extra_args else None)

        # Construct URL. For S3-compatible clouds without virtual-hosted style, path-style is common:
        url = build_object_url(ENDPOINT_URL, BUCKET_NAME, key)

        print(f"Uploaded {file_path} -> {url}")
        uploaded.append(url)

    except Exception as e:
        print(f"Error uploading {file_path}: {e}")

print(f"\nTotal uploaded: {len(uploaded)}")
for u in uploaded:
    print(u)
