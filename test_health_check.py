#!/usr/bin/env python3
import requests
import json
import os
import sys
# 환경변수 설정을 위한 dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv가 설치되지 않았습니다. 'pip install python-dotenv'로 설치해주세요.")
    sys.exit(1)

def test_health_check(endpoint_id):
    """Health check 테스트"""

    # API 키 확인
    api_key = os.getenv("RUNPOD_API_KEY")
    if not api_key:
        print("❌ RUNPOD_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    # Health check 요청
    url = f"https://api.runpod.ai/v2/{endpoint_id}/run"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "action": "health_check"
    }

    print(f"🔍 Health check 요청 중... ({url})")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print("✅ Health check 성공!")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            # 상태 요약
            status = data.get("status", "unknown")
            services = data.get("services", {})

            print(f"\n📊 상태 요약:")
            print(f"전체 상태: {status}")

            for service_name, service_info in services.items():
                service_status = service_info.get("status", "unknown")
                print(f"  {service_name}: {service_status}")

                if service_status == "error":
                    error = service_info.get("error", "Unknown error")
                    print(f"    오류: {error}")

            # 시스템 리소스 정보
            system = data.get("system", {})
            if system:
                print(f"\n💻 시스템 리소스:")
                memory = system.get("memory", {})
                if memory:
                    print(f"  메모리: {memory.get('percent_used', 0):.1f}% 사용")
                    print(f"    총: {memory.get('total_gb', 0):.1f}GB")
                    print(f"    사용 가능: {memory.get('available_gb', 0):.1f}GB")

                cpu = system.get("cpu", {})
                if cpu:
                    print(f"  CPU: {cpu.get('percent_used', 0):.1f}% 사용")

                disk = system.get("disk", {})
                if disk:
                    print(f"  디스크: {disk.get('percent_used', 0):.1f}% 사용")
                    print(f"    총: {disk.get('total_gb', 0):.1f}GB")
                    print(f"    여유: {disk.get('free_gb', 0):.1f}GB")

        else:
            print(f"❌ Health check 실패: HTTP {response.status_code}")
            print(response.text)

    except requests.RequestException as e:
        print(f"❌ 요청 실패: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("사용법: python3 test_health_check.py <endpoint_id>")
        print("예시: python3 test_health_check.py <your_endpoint_id>")
        sys.exit(1)

    endpoint_id = sys.argv[1]
    test_health_check(endpoint_id)

if __name__ == "__main__":
    main()
