# OSS Direct E-Ink Delivery

The ESP32 can read the rendered frame directly from Aliyun OSS, while OSS
AccessKey credentials stay only on the Mac or server that publishes objects.

```text
Mac or server
  -> render/fetch manifest.json, eink.bin, eink.png
  -> PUT objects to OSS

ESP32
  -> GET /render/manifest.json from OSS
  -> GET /render/eink.bin from OSS with HTTP Range headers
  -> display frame
```

## Bucket

```text
OSS_BUCKET=claudecodesapi
OSS_REGION=oss-cn-chengdu
https://claudecodesapi.oss-cn-chengdu.aliyuncs.com
```

Do not put `OSS_ACCESS_KEY_ID` or `OSS_ACCESS_KEY_SECRET` in firmware or Git.

## Publish

Set credentials in the shell, or put them in a server-side `.env` that is not
committed:

```bash
export OSS_ACCESS_KEY_ID="..."
export OSS_ACCESS_KEY_SECRET="..."
export OSS_BUCKET="claudecodesapi"
export OSS_REGION="oss-cn-chengdu"
```

Publish the current locally relayed frame:

```bash
python3 tools/publish_eink_to_oss.py \
  --source http://127.0.0.1:8788 \
  --prefix render
```

Expected public URLs:

```text
http://claudecodesapi.oss-cn-chengdu.aliyuncs.com/render/manifest.json
http://claudecodesapi.oss-cn-chengdu.aliyuncs.com/render/eink.bin
http://claudecodesapi.oss-cn-chengdu.aliyuncs.com/render/eink.png
```

HTTPS also works for browsers, but the current ESP32 firmware uses plain
`WiFiClient`, so use port `80` first.

## Firmware Config

```cpp
#define DASHBOARD_API_HOST "claudecodesapi.oss-cn-chengdu.aliyuncs.com"
#define DASHBOARD_API_PORT 80
#define DASHBOARD_MANIFEST_PATH "/render/manifest.json"
#define DASHBOARD_FRAME_PATH "/render/eink.bin"
#define ESP32_API_KEY ""
```

The firmware downloads `eink.bin` in chunks with standard HTTP Range headers:

```http
Range: bytes=0-4095
Range: bytes=4096-8191
```

For compatibility, it falls back to the older server query form when Range is
not supported:

```text
/render/eink.bin?offset=0&length=4096
```

## Keep The Frame Fresh

OSS is static storage. Something still needs to publish new frames after local
usage changes:

```text
Mac usage reporter
  -> POST /api/usage to backend
backend/local relay
  -> produces latest render
publish_eink_to_oss.py
  -> uploads latest files to OSS
ESP32
  -> reads OSS
```

The publisher can be run from launchd or cron after the usage reporter.
