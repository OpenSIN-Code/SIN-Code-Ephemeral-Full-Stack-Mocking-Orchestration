# services/storage.py

Mock S3-like object storage.

## What it does

Per-bucket in-memory key/value store. The shared gateway exposes:

- `PUT    /storage/{bucket}/{key:path}` — store bytes
- `GET    /storage/{bucket}/{key:path}` — fetch bytes (raw body)
- `GET    /storage/{bucket}`            — list keys in a bucket
- `GET    /storage/`                    — list buckets
- `DELETE /storage/{bucket}/{key:path}` — delete one object

`reset()` wipes every bucket. The content type is captured on PUT
and returned as the response `media_type` on GET.

## Dependencies

- `threading` (stdlib) for the buckets lock
- `fastapi`

## Public API

| Symbol | Purpose |
|--------|---------|
| `StorageService` | The service class (`name="storage"`, `prefix="/storage"`) |
| `put_object(bucket, key, data, content_type)` | Store; returns metadata dict |
| `get_object(bucket, key)` | Fetch metadata+data or `None` |
| `list_objects(bucket)` / `list_buckets()` | Listing helpers |
| `delete_object(bucket, key)` | Returns `True` if removed, `False` if not found |

## Defaults

- `content_type` defaults to `application/octet-stream` on PUT.
- Strings passed to `put_object` are encoded as UTF-8 before
  storage; bytes are stored as-is.

## Known caveats

- No multipart uploads, no presigned URLs, no versioning — this
  is a mock for tests, not a real S3 replacement.
- The dict-of-dicts grows without bound until `reset()`.
- Content-type is set on PUT; subsequent GETs return whatever was
  stored, even if the client sets a different `Accept` header.
