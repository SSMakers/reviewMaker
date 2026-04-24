# Server Requirement: Review Image Upload URL Generation

## Issue Title

리뷰 이미지 업로드 및 공개 URL 생성 API 추가

## Background

현재 Review Writer 데스크톱 앱은 엑셀 `하이퍼링크` 컬럼에 이미 준비된 이미지 URL이 있을 때만 Cafe24 게시글 payload의 `image_url`로 전달할 수 있습니다. URL이 없는 로컬 이미지는 사용자가 직접 블로그 등에 업로드한 뒤 URL을 복사해야 하므로 반복 작업이 큽니다.

Cafe24 API에 전달되는 `image_url`은 Cafe24 서버가 접근 가능한 공개 URL이어야 합니다. 따라서 로컬 파일 경로나 앱 내부 임시 경로를 그대로 보낼 수 없습니다.

## Goal

데스크톱 앱이 로컬 이미지 파일을 서버에 업로드하면, 서버가 저장소에 이미지를 저장하고 공개 접근 가능한 HTTPS URL을 반환합니다. 앱은 반환된 URL을 Cafe24 article payload의 `image_url`로 사용합니다.

## Proposed API

### POST `/review-images`

Multipart upload endpoint.

Request:

- `file`: image file, required
- `device_id`: authenticated device UUID, required
- `mall_id`: Cafe24 mall id, required
- `source_row_id`: optional row number or client-generated id for traceability

Response `201 Created`:

```json
{
  "image_id": "img_...",
  "url": "https://cdn.example.com/review-images/{image_id}.jpg",
  "content_type": "image/jpeg",
  "size_bytes": 123456
}
```

Error responses:

- `400`: invalid file, unsupported content type, file too large
- `401` or `403`: unauthorized device or expired contract
- `413`: payload too large
- `429`: upload rate limit exceeded
- `500`: storage failure

## Requirements

- Accept only image MIME types required by the product, at minimum `image/jpeg`, `image/png`, `image/webp`.
- Enforce a configurable max file size.
- Generate collision-resistant object names. Do not trust original filenames as storage keys.
- Return HTTPS URLs that Cafe24 can fetch without app-local authentication.
- Preserve enough metadata for support/debugging: `device_id`, `mall_id`, upload time, original filename, content type, size, object key.
- Validate caller authorization with the same contract/device model used by `/auth/verify`.
- Add rate limiting per device or contract.
- Consider image optimization or normalization if Cafe24 has size/format constraints.
- Define retention/deletion policy. Example: retain while customer contract is active plus N days.

## Client Flow

1. User selects Excel file.
2. User optionally selects image files or an image folder in the desktop app.
3. App maps each review row to either an existing `하이퍼링크` URL or a local image file.
4. For local files, app uploads to `POST /review-images`.
5. App receives `url`.
6. App passes that URL as Cafe24 `image_url` when calling `create_articles`.

## Client Implementation Status

The desktop client is already prepared to test this endpoint.

- UI supports selecting an Excel file and optional image folder.
- Default mapping mode is `URL 우선, 없으면 파일명`.
- Excel column `하이퍼링크` is treated as an existing public URL.
- Excel column `이미지파일명` is resolved inside the selected image folder.
- Local images are uploaded with multipart field name `file`.
- Additional multipart fields sent by the client: `device_id`, `mall_id`, `source_row_id`.
- Upload timeout is configurable with `API_UPLOAD_TIMEOUT_SEC`; default is 60 seconds.

## Acceptance Criteria

- A valid authenticated device can upload a JPEG/PNG/WebP image and receive a public HTTPS URL.
- The returned URL can be fetched from a network outside the user PC.
- Invalid file types are rejected with a clear 400 response.
- Oversized files are rejected with a clear 413 response.
- Unauthorized or expired devices cannot upload images.
- Upload metadata can be inspected by server operators for support.
- Desktop client can safely retry failed uploads without accidentally overwriting another image.

## Open Questions

- Which storage backend should be used: S3, Cloudflare R2, Cafe24 hosting, or existing server disk/CDN?
- Should URLs be permanent, contract-lifetime scoped, or time-limited signed URLs? Cafe24 compatibility likely favors stable public URLs.
- Does Cafe24 require one image URL string or support multiple image URLs per article?
- Should image resizing/compression happen server-side before returning URL?
- How should Excel rows map to local images: filename column, selected folder + filename, drag-and-drop per row, or separate upload table?
