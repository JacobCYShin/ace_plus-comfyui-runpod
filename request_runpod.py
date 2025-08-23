#!/usr/bin/env python3
import argparse
import json
import os
import sys
import base64
import time
from pathlib import Path
import requests

def main():
    parser = argparse.ArgumentParser(
        description="RunPod runsync/run 호출 후 응답의 첫 번째 이미지를 파일로 저장"
    )
    parser.add_argument("--endpoint-id", "-e", required=True, help="RunPod Endpoint ID (예: a5co0krxjchyvq)")
    parser.add_argument("--api-key", "-k", default=None, help="RunPod API Key. 미지정 시 환경변수 RUNPOD_API_KEY 사용")
    parser.add_argument("--json", "-j", default="fixed_input_with_loader.json", help="요청 페이로드 JSON 경로")
    parser.add_argument("--out", "-o", default="result.png", help="저장할 이미지 파일명 (기본: result.png)")
    parser.add_argument("--timeout", "-t", type=int, default=600, help="HTTP 타임아웃(초) 기본 600")
    parser.add_argument("--async-mode", action="store_true", help="비동기 /run 엔드포인트 사용 (기본: 동기 /runsync)")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("RUNPOD_API_KEY")
    if not api_key:
        print("❌ API Key가 필요합니다. --api-key 또는 환경변수 RUNPOD_API_KEY를 설정하세요.")
        sys.exit(1)

    json_path = Path(args.json)
    if not json_path.exists():
        print(f"❌ JSON 파일을 찾을 수 없습니다: {json_path}")
        sys.exit(1)

    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ JSON 로드 실패: {e}")
        sys.exit(1)

    # 엔드포인트 선택
    if args.async_mode:
        url = f"https://api.runpod.ai/v2/{args.endpoint_id}/run"
        print("🔄 비동기 모드: /run 엔드포인트 사용")
    else:
        url = f"https://api.runpod.ai/v2/{args.endpoint_id}/runsync"
        print("⚡ 동기 모드: /runsync 엔드포인트 사용")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print(f"🚀 요청 전송 중... ({url})")
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=args.timeout)
    except requests.RequestException as e:
        print(f"❌ 요청 실패: {e}")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"❌ 요청 실패: HTTP {resp.status_code}")
        print(resp.text[:2000])
        sys.exit(1)

    try:
        data = resp.json()
    except ValueError:
        print("❌ 서버에서 JSON이 아닌 응답을 반환했습니다.")
        print(resp.text[:2000])
        sys.exit(1)

    print("📦 전체 응답:")
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # 비동기 모드인 경우 job ID를 받아서 상태를 폴링
    if args.async_mode:
        try:
            job_id = data["id"]
            print(f"🔄 Job ID: {job_id}")
        except KeyError:
            print("❌ 비동기 응답에서 job ID를 찾을 수 없습니다.")
            sys.exit(1)

        # 상태 폴링
        status_url = f"https://api.runpod.ai/v2/{args.endpoint_id}/status/{job_id}"
        print("⏳ 작업 완료 대기 중...")
        
        while True:
            try:
                status_resp = requests.get(status_url, headers=headers, timeout=30)
                if status_resp.status_code != 200:
                    print(f"❌ 상태 확인 실패: HTTP {status_resp.status_code}")
                    sys.exit(1)
                
                status_data = status_resp.json()
                status = status_data.get("status", "UNKNOWN")
                print(f"📊 현재 상태: {status}")
                
                if status == "COMPLETED":
                    data = status_data
                    break
                elif status == "FAILED":
                    print("❌ 작업이 실패했습니다.")
                    print(json.dumps(status_data, ensure_ascii=False, indent=2))
                    sys.exit(1)
                elif status in ["IN_QUEUE", "IN_PROGRESS"]:
                    time.sleep(5)  # 5초 대기
                else:
                    print(f"❌ 알 수 없는 상태: {status}")
                    sys.exit(1)
                    
            except requests.RequestException as e:
                print(f"❌ 상태 확인 중 오류: {e}")
                sys.exit(1)

    # 다양한 응답 포맷 방어 처리
    try:
        images = data["output"]["images"]
    except (KeyError, TypeError):
        print("❌ 'output.images'가 응답에 없습니다. 워크플로우에 PreviewImage 노드가 있는지 확인하세요.")
        sys.exit(1)

    if not isinstance(images, list) or len(images) == 0:
        print("❌ 'output.images'가 비어 있습니다.")
        sys.exit(1)

    first = images[0]
    if isinstance(first, dict):
        if "data" in first:
            b64 = first["data"]              # 순수 base64
        elif "image" in first and isinstance(first["image"], str):
            # data URI 형태일 수 있음
            val = first["image"]
            b64 = val.split(",", 1)[-1] if val.startswith("data:") else val
        else:
            print("❌ 예상한 이미지 키('data' 또는 'image')를 찾지 못했습니다.")
            sys.exit(1)
    elif isinstance(first, str):
        b64 = first.split(",", 1)[-1] if first.startswith("data:") else first
    else:
        print("❌ 알 수 없는 이미지 응답 형식입니다.")
        sys.exit(1)

    out_path = Path(args.out)
    try:
        out_path.write_bytes(base64.b64decode(b64))
    except Exception as e:
        print(f"❌ base64 디코딩/저장 실패: {e}")
        sys.exit(1)

    print(f"✅ 이미지 저장 완료: {out_path}")

if __name__ == "__main__":
    main()
