#!/usr/bin/env python3
import requests
import json
import os
import sys
import time
from pathlib import Path

def test_s3_request(endpoint_id, json_file, output_file="result_s3.png", timeout=600):
    """S3 URL을 사용하는 요청 테스트"""
    
    # API 키 확인
    api_key = os.getenv("RUNPOD_API_KEY")
    if not api_key:
        print("❌ RUNPOD_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    # JSON 파일 확인
    json_path = Path(json_file)
    if not json_path.exists():
        print(f"❌ JSON 파일을 찾을 수 없습니다: {json_path}")
        sys.exit(1)
    
    # JSON 로드
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
    except Exception as e:
        print(f"❌ JSON 로드 실패: {e}")
        sys.exit(1)
    
    # S3 설정 확인
    if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
        print("⚠️  AWS 자격 증명이 설정되지 않았습니다. S3 기능이 제한될 수 있습니다.")
    
    if not os.getenv("S3_BUCKET_NAME"):
        print("⚠️  S3_BUCKET_NAME이 설정되지 않았습니다.")
    
    # 요청 URL
    url = f"https://api.runpod.ai/v2/{endpoint_id}/runsync"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print(f"🚀 S3 URL 요청 시작...")
    print(f"   엔드포인트: {endpoint_id}")
    print(f"   JSON 파일: {json_file}")
    print(f"   출력 파일: {output_file}")
    print(f"   타임아웃: {timeout}초")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  요청 완료 (소요시간: {duration:.2f}초)")
        
        if response.status_code == 200:
            data = response.json()
            
            # 성능 정보 출력
            performance = data.get("performance", {})
            if performance:
                print(f"\n📊 성능 정보:")
                print(f"  총 소요시간: {performance.get('total_duration_seconds', 0):.2f}초")
                print(f"  처리 단계 수: {performance.get('total_steps', 0)}")
                
                # 메모리 사용량
                memory = performance.get("memory_usage", {})
                if memory:
                    print(f"  메모리 사용량:")
                    print(f"    최대: {memory.get('max_percent', 0):.1f}%")
                    print(f"    평균: {memory.get('avg_percent', 0):.1f}%")
                
                # CPU 사용량
                cpu = performance.get("cpu_usage", {})
                if cpu:
                    print(f"  CPU 사용량:")
                    print(f"    최대: {cpu.get('max_percent', 0):.1f}%")
                    print(f"    평균: {cpu.get('avg_percent', 0):.1f}%")
                
                # 처리 단계별 상세 정보
                steps = performance.get("processing_steps", [])
                if steps:
                    print(f"\n🔧 처리 단계:")
                    for step in steps:
                        step_name = step.get("step", "unknown")
                        step_duration = step.get("duration")
                        if step_duration:
                            print(f"  {step_name}: {step_duration:.2f}초")
                        else:
                            print(f"  {step_name}")
            
            # 이미지 저장
            images = data.get("images", [])
            if images:
                print(f"\n🖼️  {len(images)}개 이미지 생성됨")
                
                for i, image_data in enumerate(images):
                    if i == 0:  # 첫 번째 이미지만 저장
                        try:
                            # Base64 디코딩
                            if "data:image" in image_data:
                                base64_data = image_data.split(",", 1)[1]
                            else:
                                base64_data = image_data
                            
                            import base64
                            image_bytes = base64.b64decode(base64_data)
                            
                            # 파일 저장
                            with open(output_file, "wb") as f:
                                f.write(image_bytes)
                            
                            print(f"✅ 이미지 저장됨: {output_file}")
                            
                        except Exception as e:
                            print(f"❌ 이미지 저장 실패: {e}")
            else:
                print("⚠️  생성된 이미지가 없습니다.")
                
                # 오류 정보 확인
                errors = data.get("errors", [])
                if errors:
                    print(f"❌ 오류 발생:")
                    for error in errors:
                        print(f"  - {error}")
            
            return data
            
        else:
            print(f"❌ 요청 실패: HTTP {response.status_code}")
            print(response.text)
            return None
            
    except requests.Timeout:
        print(f"❌ 요청 타임아웃 ({timeout}초 초과)")
        return None
    except requests.RequestException as e:
        print(f"❌ 요청 실패: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("사용법: python3 test_s3_request.py <endpoint_id> [json_file] [output_file]")
        print("예시: python3 test_s3_request.py jp60la4hhbubj4 test_s3_input.json result_s3.png")
        sys.exit(1)
    
    endpoint_id = sys.argv[1]
    json_file = sys.argv[2] if len(sys.argv) > 2 else "test_s3_input.json"
    output_file = sys.argv[3] if len(sys.argv) > 3 else "result_s3.png"
    
    test_s3_request(endpoint_id, json_file, output_file)

if __name__ == "__main__":
    main()
