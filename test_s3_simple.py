#!/usr/bin/env python3
"""
S3 연결 테스트 스크립트
"""
import os
import boto3
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_s3_connection():
    """S3 연결 테스트"""
    try:
        # 환경변수 확인
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_region = os.environ.get('AWS_DEFAULT_REGION', 'ap-northeast-2')
        s3_bucket = os.environ.get('S3_BUCKET_NAME')

        logger.info("=== S3 연결 테스트 ===")
        logger.info(f"AWS_ACCESS_KEY_ID: {'SET' if aws_access_key else 'NOT SET'}")
        logger.info(f"AWS_SECRET_ACCESS_KEY: {'SET' if aws_secret_key else 'NOT SET'}")
        logger.info(f"AWS_DEFAULT_REGION: {aws_region}")
        logger.info(f"S3_BUCKET_NAME: {s3_bucket}")

        if not aws_access_key or not aws_secret_key:
            logger.error("AWS 자격 증명이 설정되지 않았습니다.")
            return False

        # S3 클라이언트 생성
        logger.info("S3 클라이언트 생성 중...")
        s3_client = boto3.client(
            's3',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )

        # 버킷 목록 조회
        logger.info("버킷 목록 조회 중...")
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        logger.info(f"사용 가능한 버킷: {buckets}")

        # 특정 버킷 접근 테스트
        if s3_bucket:
            logger.info(f"버킷 '{s3_bucket}' 접근 테스트 중...")
            try:
                response = s3_client.list_objects_v2(Bucket=s3_bucket, MaxKeys=5)
                objects = [obj['Key'] for obj in response.get('Contents', [])]
                logger.info(f"버킷 '{s3_bucket}'의 객체들: {objects}")
            except Exception as e:
                logger.error(f"버킷 '{s3_bucket}' 접근 실패: {e}")
                return False

        logger.info("S3 연결 테스트 성공!")
        return True

    except Exception as e:
        logger.error(f"S3 연결 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_s3_connection()
