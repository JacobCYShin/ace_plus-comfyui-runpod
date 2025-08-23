#!/usr/bin/env python3
import argparse
import json
import base64
import mimetypes
from pathlib import Path
import sys

def to_data_uri(image_path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(image_path))
    if mime is None:
        mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"

def main():
    parser = argparse.ArgumentParser(
        description="fixed_input_with_loader.json의 input.images[index].image 값을 base64(Data URI)로 교체"
    )
    parser.add_argument("--image", "-i", required=True, help="교체할 이미지 경로 (png/jpg/jpeg)")
    parser.add_argument("--json", "-j", default="fixed_input_with_loader.json", help="수정할 JSON 경로")
    parser.add_argument("--index", "-n", type=int, default=0, help="input.images 배열에서 교체할 인덱스 (기본 0)")
    args = parser.parse_args()

    image_path = Path(args.image)
    json_path = Path(args.json)

    if not image_path.exists():
        print(f"❌ 이미지 파일을 찾을 수 없습니다: {image_path}")
        sys.exit(1)
    if not json_path.exists():
        print(f"❌ JSON 파일을 찾을 수 없습니다: {json_path}")
        sys.exit(1)

    data_uri = to_data_uri(image_path)

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ JSON 로드 실패: {e}")
        sys.exit(1)

    try:
        images = data["input"]["images"]
    except (KeyError, TypeError):
        print("❌ JSON에 data['input']['images'] 경로가 없습니다.")
        sys.exit(1)

    if not isinstance(images, list) or len(images) == 0:
        print("❌ data['input']['images']는 비어있지 않은 리스트여야 합니다.")
        sys.exit(1)

    idx = args.index
    if idx < 0 or idx >= len(images):
        print(f"❌ 인덱스 범위를 벗어났습니다. 길이={len(images)}, 요청={idx}")
        sys.exit(1)

    if not isinstance(images[idx], dict):
        print("❌ images[index]는 객체여야 합니다.")
        sys.exit(1)

    images[idx]["image"] = data_uri

    # 백업 1회 생성
    backup_path = json_path.with_suffix(json_path.suffix + ".bak")
    if not backup_path.exists():
        backup_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 덮어쓰기 저장
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Base64 교체 완료 -> {json_path}")

if __name__ == "__main__":
    main()
