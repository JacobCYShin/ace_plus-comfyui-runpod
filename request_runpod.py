#!/usr/bin/env python3
import argparse
import json
import os
import sys
import base64
import time
import mimetypes
from pathlib import Path
import requests
from PIL import Image
import io
# 환경변수 설정을 위한 dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv가 설치되지 않았습니다. 'pip install python-dotenv'로 설치해주세요.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="RunPod runsync/run 호출 후 응답의 첫 번째 이미지를 파일로 저장"
    )
    parser.add_argument("--endpoint-id", "-e", default=None, help="RunPod Endpoint ID (예: a5co0krxjchyvq). 미지정 시 환경변수 RUNPOD_ENDPOINT_ID 사용")
    parser.add_argument("--api-key", "-k", default=None, help="RunPod API Key. 미지정 시 환경변수 RUNPOD_API_KEY 사용")
    parser.add_argument("--json", "-j", default="fixed_input_with_loader.json", help="요청 페이로드 JSON 경로")
    parser.add_argument("--out", "-o", default="result.png", help="저장할 이미지 파일명 (기본: result.png)")
    parser.add_argument("--timeout", "-t", type=int, default=600, help="HTTP 타임아웃(초) 기본 600")
    parser.add_argument("--async-mode", action="store_true", help="비동기 /run 엔드포인트 사용 (기본: 동기 /runsync)")
    parser.add_argument("--image-index", type=int, default=-1, help="저장할 이미지 인덱스 (기본: -1 = 마지막 이미지)")
    # 입력 이미지 주입 옵션(상호 배타)
    parser.add_argument("--input-image-path", help="요청 페이로드에 주입할 로컬 이미지 경로 (base64 Data URI로 변환)")
    parser.add_argument("--input-s3-url", help="요청 페이로드에 주입할 S3 URL (예: s3://bucket/key.png)")
    parser.add_argument("--input-image-index", type=int, default=0, help="input.images에 주입할 인덱스 (기본 0, 없으면 생성)")
    # 텍스트 프롬프트 주입 옵션
    parser.add_argument("--prompt-node", help="텍스트를 변경할 노드 ID (예: 147)")
    parser.add_argument("--prompt-text", help="주입할 텍스트 프롬프트")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("RUNPOD_API_KEY")
    if not api_key:
        print("❌ API Key가 필요합니다. --api-key 또는 환경변수 RUNPOD_API_KEY를 설정하세요.")
        sys.exit(1)


    endpoint_id = args.endpoint_id or os.getenv("RUNPOD_ENDPOINT_ID")
    if not endpoint_id:
        print("❌ Endpoint ID가 필요합니다. --endpoint-id 또는 환경변수 RUNPOD_ENDPOINT_ID를 설정하세요.")
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

    # 입력 이미지 주입 전 상호 배타성 체크
    if args.input_image_path and args.input_s3_url:
        print("❌ --input-image-path 와 --input-s3-url 은 동시에 사용할 수 없습니다.")
        sys.exit(1)

    # 입력 이미지 주입 로직
    if args.input_image_path or args.input_s3_url:
        # ensure structure
        if not isinstance(payload, dict):
            print("❌ 페이로드 루트가 객체가 아닙니다.")
            sys.exit(1)
        payload.setdefault("input", {})
        if not isinstance(payload["input"], dict):
            print("❌ payload['input'] 가 객체가 아닙니다.")
            sys.exit(1)
        images = payload["input"].get("images")
        if images is None or not isinstance(images, list):
            images = []
            payload["input"]["images"] = images

        # 보장: 리스트 길이를 index+1 까지 확장
        idx = args.input_image_index
        if idx < 0:
            print("❌ --input-image-index 는 0 이상의 정수여야 합니다.")
            sys.exit(1)
        while len(images) <= idx:
            images.append({})
        if not isinstance(images[idx], dict):
            images[idx] = {}

        target = images[idx]
        # 주입 타입별 처리
        if args.input_image_path:
            img_path = Path(args.input_image_path)
            if not img_path.exists():
                print(f"❌ 입력 이미지 파일이 없습니다: {img_path}")
                sys.exit(1)
            mime, _ = mimetypes.guess_type(str(img_path))
            if mime is None:
                mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
            encoded = base64.b64encode(img_path.read_bytes()).decode("utf-8")
            data_uri = f"data:{mime};base64,{encoded}"
            target["image"] = data_uri
            # name 기본값 세팅(비어있으면)
            target.setdefault("name", img_path.name)
            # s3_url과 상호 배타
            if "s3_url" in target:
                del target["s3_url"]
        elif args.input_s3_url:
            target["s3_url"] = args.input_s3_url
            # name 기본값 세팅(비어있으면)
            target.setdefault("name", "input_image.png")
            # image와 상호 배타
            if "image" in target:
                del target["image"]

    # 텍스트 프롬프트 주입 로직
    if args.prompt_node and args.prompt_text:
        workflow = payload.get("input", {}).get("workflow", {})
        if not isinstance(workflow, dict):
            print("❌ payload['input']['workflow']가 객체가 아닙니다.")
            sys.exit(1)

        node_id = args.prompt_node
        if node_id not in workflow:
            print(f"❌ 노드 ID '{node_id}'를 워크플로우에서 찾을 수 없습니다.")
            sys.exit(1)

        node = workflow[node_id]
        if not isinstance(node, dict):
            print(f"❌ 노드 '{node_id}'가 객체가 아닙니다.")
            sys.exit(1)

        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            print(f"❌ 노드 '{node_id}'의 inputs가 객체가 아닙니다.")
            sys.exit(1)

        # text 입력이 있는지 확인하고 업데이트
        if "text" in inputs:
            inputs["text"] = args.prompt_text
            print(f"✅ 노드 '{node_id}'의 텍스트 프롬프트를 업데이트했습니다.")
        else:
            print(f"⚠️ 노드 '{node_id}'에 'text' 입력이 없습니다. 사용 가능한 입력: {list(inputs.keys())}")
    elif args.prompt_node or args.prompt_text:
        print("❌ --prompt-node와 --prompt-text는 함께 사용해야 합니다.")
        sys.exit(1)

    # 엔드포인트 선택
    if args.async_mode:
        url = f"https://api.runpod.ai/v2/{endpoint_id}/run"
        print("🔄 비동기 모드: /run 엔드포인트 사용")
    else:
        url = f"https://api.runpod.ai/v2/{endpoint_id}/runsync"
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
        status_url = f"https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}"
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

    # 저장할 이미지 선택 (기본: 마지막 이미지)
    try:
        selected = images[args.image_index]
    except Exception:
        print(f"❌ 이미지 인덱스 선택 실패: index={args.image_index}, images_len={len(images)}")
        sys.exit(1)
    if isinstance(selected, dict):
        if "data" in selected:
            b64 = selected["data"]              # 순수 base64
        elif "image" in selected and isinstance(selected["image"], str):
            # data URI 형태일 수 있음
            val = selected["image"]
            b64 = val.split(",", 1)[-1] if val.startswith("data:") else val
        else:
            print("❌ 예상한 이미지 키('data' 또는 'image')를 찾지 못했습니다.")
            sys.exit(1)
    elif isinstance(selected, str):
        b64 = selected.split(",", 1)[-1] if selected.startswith("data:") else selected
    else:
        print("❌ 알 수 없는 이미지 응답 형식입니다.")
        sys.exit(1)

    out_path = Path(args.out)
    try:
        # base64 디코딩
        image_data = base64.b64decode(b64)

        # PIL로 이미지 로드
        image = Image.open(io.BytesIO(image_data))

        # 이미지 크기 확인
        width, height = image.size
        print(f"📏 원본 이미지 크기: {width}x{height}")

        # 우측 절반만 잘라내기
        right_half = image.crop((width//2, 0, width, height))

        # 잘라낸 이미지 저장
        right_half.save(out_path)

    except Exception as e:
        print(f"❌ 이미지 처리/저장 실패: {e}")
        sys.exit(1)

    print(f"✅ 우측 절반 이미지 저장 완료: {out_path}")

if __name__ == "__main__":
    main()
