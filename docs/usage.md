## Usage Guide

### Overview
- **동기 `/runsync`**: 요청이 완료될 때까지 대기하며 결과를 즉시 반환합니다.
- **비동기 `/run`**: 즉시 Job ID를 반환합니다. 이후 `/status/{jobId}`를 폴링하거나 Webhook을 사용합니다.
- **권장 입력 방식**: 큰 이미지는 `base64` 대신 `s3_url`을 사용하세요. 요청 크기 제한(대략 `/run` 10MB, `/runsync` 20MB)을 회피하고 메모리 사용량/지연을 줄입니다.

### Input Schema

```json
{
  "input": {
    "workflow": { ... },
    "images": [
      {
        "name": "input_image_1.png",
        "image": "data:image/png;base64,..."
      }
    ]
  }
}
```

`images` 항목은 다음 두 방식 중 하나만 사용합니다(서로 배타적).
- `image`: base64 데이터(선택적으로 data URI 프리픽스 허용)
- `s3_url`: 예) `s3://your-bucket/path/image.png`

### Sync Call (/runsync)

```bash
curl -X POST \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{"input":{"workflow":{...},"images":[{"name":"image.png","s3_url":"s3://bucket/path/image.png"}]}}' \
  https://api.runpod.ai/v2/<endpoint_id>/runsync
```

### Async Call (/run + /status)

1) Submit:
```bash
curl -X POST \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{"input":{"workflow":{...}}}' \
  https://api.runpod.ai/v2/<endpoint_id>/run
```

2) Poll status:
```bash
curl -H "Authorization: Bearer <api_key>" \
  https://api.runpod.ai/v2/<endpoint_id>/status/<job_id>
```

상태 값: `IN_QUEUE` | `IN_PROGRESS` | `COMPLETED` | `FAILED`

### Webhook (선택)
비동기 요청에 `webhook` URL을 포함하면 완료 시점에 콜백을 받을 수 있습니다. 자세한 예시는 RunPod 문서를 참고하세요.

### Response Structure (요약)

```json
{
  "id": "...",
  "status": "COMPLETED",
  "output": {
    "images": [
      { "filename": "ComfyUI_00001_.png", "type": "base64", "data": "..." }
    ]
  },
  "performance_summary": { ... }
}
```

### Python Scripts

- `request_runpod.py`: 동기/비동기 호출 및 결과 이미지 저장
  - 동기: `python3 request_runpod.py --endpoint-id <id> --json fixed_input_with_loader.json --out result.png`
  - 비동기: `python3 request_runpod.py --endpoint-id <id> --json fixed_input_with_loader.json --out result.png --async-mode`
- `test_s3_request.py`: S3 URL 입력 예제
- `test_health_check.py`: 헬스체크 요청 예제

### Tips
- 큰 입력 이미지는 S3로 전달하고, 결과도 S3 업로드를 고려하세요.
- `--timeout`은 초기 HTTP 요청 타임아웃(폴링은 별도). 장시간 워크플로우는 비동기를 권장합니다.
- 응답의 `performance_summary`를 활용하여 처리 시간과 시스템 자원을 파악하세요.
