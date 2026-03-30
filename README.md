# worker-comfyui

> [ComfyUI](https://github.com/comfyanonymous/ComfyUI)를 [RunPod](https://www.runpod.io/) 서버리스 API로 실행합니다.

<p align="center">
  <img src="assets/worker_sitting_in_comfy_chair.jpg" title="Worker sitting in comfy chair" />
</p>

[![RunPod](https://api.runpod.io/badge/runpod-workers/worker-comfyui)](https://www.runpod.io/console/hub/runpod-workers/worker-comfyui)

---

ComfyUI 워크플로우를 RunPod 서버리스 엔드포인트로 배포하고, API 호출로 이미지를 생성/수신합니다. 입력 이미지는 `base64` 또는 `S3 URL`로 전달할 수 있습니다.

## 목차

- [빠른 시작](#빠른-시작)
- [API 개요](#api-개요)
- [입력 스키마](#입력-스키마)
- [출력 스키마](#출력-스키마)
- [환경 변수](#환경-변수)
- [사용 예시](#사용-예시)
- [클라이언트 스크립트](#클라이언트-스크립트)
- [워크플로우 JSON 추출](#워크플로우-json-추출)
- [추가 문서](#추가-문서)

---

## 빠른 시작

1. Docker 이미지 선택: `runpod/worker-comfyui:<version>-*` (예: `-sd3`).
2. 배포: `docs/deployment.md`를 참고해 RunPod 템플릿/엔드포인트를 구성합니다.
3. (선택) S3 업로드/모니터링 설정: `docs/configuration.md`의 환경 변수를 설정합니다.
4. 워크플로우 준비: `test_resources/workflows/` 예제를 사용하거나 직접 [워크플로우 JSON 추출](#워크플로우-json-추출).
5. 호출: 아래 [사용 예시](#사용-예시) 또는 [클라이언트 스크립트](#클라이언트-스크립트)로 테스트합니다.

> 참고: Docker 이미지 목록은 도커 허브 `runpod/worker-comfyui`에서 확인하세요.

## API 개요

- 엔드포인트: `/runsync`(동기), `/run`(비동기), `/status/{jobId}`, `/health`
- 권장: 큰 이미지는 `base64` 대신 `S3 URL` 사용
- 요청 크기 제한(참고): `/run` 약 10MB, `/runsync` 약 20MB

## 입력 스키마

```json
{
  "input": {
    "workflow": { ... },
    "images": [
      { "name": "input.png", "image": "data:image/png;base64,..." }
    ]
  }
}
```

- `input.workflow`: ComfyUI에서 Export(API)한 워크플로우 JSON
- `input.images`: 선택. 아래 중 하나만 사용(상호배타)
  - `image`: base64 문자열(선택적 data URI 프리픽스 허용)
  - `s3_url`: `s3://bucket/path/image.png`

## 출력 스키마

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

- `output.images[*].type`: `base64` 또는 `s3_url` (S3 업로드가 활성화된 경우)
- `performance_summary`: 처리 시간, 단계, 시스템 지표(옵션)

## 환경 변수

`.env` 예시:

```bash
# RunPod API
RUNPOD_API_KEY=your_runpod_api_key_here
RUNPOD_ENDPOINT_ID=your_endpoint_id_here

# AWS S3 (선택)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=your-s3-bucket-name

# 성능 모니터링
ENABLE_PERFORMANCE_MONITORING=true

# ComfyUI/네트워크
WEBSOCKET_RECONNECT_ATTEMPTS=5
WEBSOCKET_RECONNECT_DELAY_S=3
REFRESH_WORKER=false
```

## 사용 예시

### 동기 요청(`/runsync`)

```bash
curl -X POST \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{"input":{"workflow":{...}}}' \
  https://api.runpod.ai/v2/<endpoint_id>/runsync
```

S3 URL 입력 사용:

```bash
curl -X POST \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{"input":{"workflow":{...},"images":[{"name":"image.png","s3_url":"s3://bucket/path/image.png"}]}}' \
  https://api.runpod.ai/v2/<endpoint_id>/runsync
```

### 비동기 요청(`/run` + `/status`)

1) 제출
```bash
curl -X POST \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{"input":{"workflow":{...}}}' \
  https://api.runpod.ai/v2/<endpoint_id>/run
```

2) 상태 폴링
```bash
curl -H "Authorization: Bearer <api_key>" \
  https://api.runpod.ai/v2/<endpoint_id>/status/<job_id>
```

### 헬스체크

```bash
curl -X POST \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{"input":{"action":"health_check"}}' \
  https://api.runpod.ai/v2/<endpoint_id>/run
```

## 클라이언트 스크립트

`request_runpod.py` (동기):
```bash
export RUNPOD_API_KEY=your_runpod_api_key
python3 request_runpod.py --endpoint-id <endpoint_id> --json fixed_input_with_loader.json --out result_sync.png
```

`request_runpod.py` (비동기):
```bash
export RUNPOD_API_KEY=your_runpod_api_key
python3 request_runpod.py --endpoint-id <endpoint_id> --json fixed_input_with_loader.json --out result_async.png --async-mode
```

`test_health_check.py`:
```bash
export RUNPOD_API_KEY=your_runpod_api_key
python3 test_health_check.py <endpoint_id>
```

> 팁
> - `--timeout`은 초기 POST 타임아웃입니다(폴링은 별도). 긴 작업은 비동기 권장.
> - 큰 입력 이미지는 `S3 URL` 사용을 권장합니다.

## 워크플로우 JSON 추출

1. 브라우저에서 ComfyUI 열기
2. 상단 `Workflow > Export (API)` 선택
3. 내려받은 `workflow.json` 내용을 `input.workflow`로 사용

## 추가 문서

- `docs/deployment.md`: RunPod 배포 가이드
- `docs/configuration.md`: 환경 변수/설정(S3 포함)
- `docs/customization.md`: 모델/노드 커스터마이즈
- `docs/development.md`: 로컬 개발/테스트
- `docs/ci-cd.md`: CI/CD 파이프라인
