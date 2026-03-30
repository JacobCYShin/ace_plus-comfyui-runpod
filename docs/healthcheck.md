## Health Check Guide

### 목적
배포된 워커의 상태(ComfyUI, S3 연결, 시스템 자원)를 빠르게 점검합니다.

### 요청 방법

비동기 `/run` 호출로 `action: health_check`를 전달합니다.

```bash
curl -X POST \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{"input":{"action":"health_check"}}' \
  https://api.runpod.ai/v2/<endpoint_id>/run
```

또는 파이썬 스크립트 사용:

```bash
export RUNPOD_API_KEY=your_runpod_api_key
python3 test_health_check.py <endpoint_id>
```

### 응답 예시(요약)

```json
{
  "status": "COMPLETED",
  "output": {
    "health": {
      "comfyui": { "ok": true, "detail": "pong" },
      "s3": { "ok": true, "bucket": "your-bucket" },
      "system": {
        "cpu_percent": 12.3,
        "memory_percent": 45.6,
        "disk_percent": 70.1
      }
    }
  }
}
```

### 항목 해석
- **comfyui.ok**: ComfyUI API 기본 핑 성공 여부
- **s3.ok**: 환경변수에 따른 S3 클라이언트/버킷 접근 가능 여부
- **system.cpu_percent**: 현재 CPU 사용률(논블로킹 측정)
- **system.memory_percent**: 시스템 메모리 사용률
- **system.disk_percent**: 루트 볼륨 디스크 사용률

### 트러블슈팅 체크리스트
- ComfyUI 실패: 워커 포트/프로세스 상태 확인, 네트워킹/방화벽, ComfyUI 로그 확인
- S3 실패: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `S3_BUCKET_NAME` 확인
- 리소스 과다: 워크플로우 파라미터 축소, 인스턴스 타입 상향, 동시 작업 제한
