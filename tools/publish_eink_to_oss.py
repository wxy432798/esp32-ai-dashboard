#!/usr/bin/env python3
import argparse
import base64
import email.utils
import hashlib
import hmac
import json
import os
import struct
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_SOURCE = "http://127.0.0.1:8788"
DEFAULT_BUCKET = "claudecodesapi"
DEFAULT_REGION = "oss-cn-chengdu"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _fetch(source: str, path: str, timeout: int) -> bytes:
    url = source.rstrip("/") + path
    request = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _canonicalized_oss_headers(headers: dict[str, str]) -> str:
    items = []
    for key, value in headers.items():
        lower = key.lower()
        if lower.startswith("x-oss-"):
            items.append((lower, " ".join(str(value).strip().split())))
    return "".join(f"{key}:{value}\n" for key, value in sorted(items))


def _signature(method: str, bucket: str, key: str, headers: dict[str, str],
               access_key_secret: str) -> str:
    content_md5 = headers.get("Content-MD5", "")
    content_type = headers.get("Content-Type", "")
    date = headers.get("Date", "")
    canonicalized_headers = _canonicalized_oss_headers(headers)
    canonicalized_resource = f"/{bucket}/{key}"
    string_to_sign = "\n".join([
        method,
        content_md5,
        content_type,
        date,
        canonicalized_headers + canonicalized_resource,
    ])
    digest = hmac.new(
        access_key_secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def _put_object(endpoint: str, bucket: str, key: str, data: bytes, content_type: str,
                access_key_id: str, access_key_secret: str, public_read: bool,
                timeout: int) -> None:
    url = f"{endpoint.rstrip('/')}/{key}"
    headers = {
        "Date": email.utils.formatdate(usegmt=True),
        "Content-Type": content_type,
        "Content-MD5": base64.b64encode(hashlib.md5(data).digest()).decode("ascii"),
    }
    if public_read:
        headers["x-oss-object-acl"] = "public-read"
    signature = _signature("PUT", bucket, key, headers, access_key_secret)
    headers["Authorization"] = f"OSS {access_key_id}:{signature}"
    request = urllib.request.Request(url, data=data, method="PUT", headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status not in (200, 201):
            raise RuntimeError(f"PUT {key} returned HTTP {response.status}")


def _public_endpoint(bucket: str, region: str) -> str:
    return f"https://{bucket}.{region}.aliyuncs.com"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _frame_info(frame: bytes) -> dict[str, Any]:
    header_len = 26
    if len(frame) < header_len or frame[:8] != b"EINK3C01":
        raise ValueError("invalid e-ink frame header")
    width, height, _reserved, black_len, red_len, crc32 = struct.unpack("<HHHIII", frame[8:26])
    expected = header_len + black_len + red_len
    if expected != len(frame):
        raise ValueError(f"bad frame length {len(frame)} != {expected}")
    return {
        "width": width,
        "height": height,
        "crc32": f"{crc32:08x}",
        "bytes": len(frame),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish rendered ESP32 e-ink frame files to Aliyun OSS.")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="render source base URL")
    parser.add_argument("--prefix", default="render", help="OSS object prefix")
    parser.add_argument("--bucket", default=_env("OSS_BUCKET", DEFAULT_BUCKET))
    parser.add_argument("--region", default=_env("OSS_REGION", DEFAULT_REGION))
    parser.add_argument("--endpoint", default=_env("OSS_ENDPOINT", ""))
    parser.add_argument("--access-key-id", default=_env("OSS_ACCESS_KEY_ID", ""))
    parser.add_argument("--access-key-secret", default=_env("OSS_ACCESS_KEY_SECRET", ""))
    parser.add_argument("--env-file", default="", help="optional .env file containing OSS_* values")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--no-public-read", action="store_true")
    args = parser.parse_args()

    if args.env_file:
        _load_env_file(Path(args.env_file).expanduser())
        args.bucket = args.bucket or _env("OSS_BUCKET", DEFAULT_BUCKET)
        args.region = args.region or _env("OSS_REGION", DEFAULT_REGION)
        args.endpoint = args.endpoint or _env("OSS_ENDPOINT", "")
        args.access_key_id = args.access_key_id or _env("OSS_ACCESS_KEY_ID", "")
        args.access_key_secret = args.access_key_secret or _env("OSS_ACCESS_KEY_SECRET", "")

    bucket = args.bucket
    region = args.region
    endpoint = args.endpoint or _public_endpoint(bucket, region)
    access_key_id = args.access_key_id
    access_key_secret = args.access_key_secret
    if not access_key_id or not access_key_secret:
        print("missing OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET", file=sys.stderr)
        return 2

    manifest = json.loads(_fetch(args.source, "/render/manifest.json", args.timeout).decode("utf-8"))
    frame = _fetch(args.source, manifest.get("url") or "/render/eink.bin", args.timeout)
    png = _fetch(args.source, manifest.get("png_url") or "/render/eink.png", args.timeout)
    frame_info = _frame_info(frame)

    prefix = args.prefix.strip("/")
    public_manifest: dict[str, Any] = dict(manifest)
    public_manifest["url"] = f"/{prefix}/eink.bin"
    public_manifest["png_url"] = f"/{prefix}/eink.png"
    public_manifest["oss_endpoint"] = endpoint
    public_manifest.update(frame_info)
    manifest_bytes = json.dumps(public_manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    public_read = not args.no_public_read
    objects = [
        (f"{prefix}/eink.bin", frame, "application/octet-stream"),
        (f"{prefix}/eink.png", png, "image/png"),
        (f"{prefix}/manifest.json", manifest_bytes, "application/json; charset=utf-8"),
    ]
    for key, data, content_type in objects:
        _put_object(endpoint, bucket, key, data, content_type,
                    access_key_id, access_key_secret, public_read, args.timeout)
        print(f"uploaded {endpoint}/{key} ({len(data)} bytes)")

    print(json.dumps({
        "manifest": f"{endpoint}/{prefix}/manifest.json",
        "frame": f"{endpoint}/{prefix}/eink.bin",
        "png": f"{endpoint}/{prefix}/eink.png",
        "crc32": public_manifest.get("crc32"),
        "bytes": public_manifest.get("bytes"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
