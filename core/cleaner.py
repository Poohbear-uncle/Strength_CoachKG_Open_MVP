# core/cleaner.py
import os
import time
import glob
import logging

# 시스템 로그 설정 (Streamlit 콘솔 및 시스템 로그에서 확인 가능)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GarbageCollector")

def clean_temporary_files(target_dir="/tmp", max_age_seconds=3600):
    """
    지정된 디렉토리 내에서 생성되거나 수정된 지 1시간(기본값)이 지난 임시 파일들을 찾아 안전하게 삭제합니다.
    
    :param target_dir: 분석 대상 임시 디렉토리 경로
    :param max_age_seconds: 파일 보존 기준 시간 (초 단위, 기본값 3600초 = 1시간)
    :return: (삭제 성공 개수, 실패 개수)
    """
    if not os.path.exists(target_dir):
        logger.warning(f"[GC] 대상 디렉토리가 존재하지 않습니다: {target_dir}")
        return 0, 0

    # 소거 대상 파일 패턴 정의 (인수인계서 명세 준수)
    patterns = [
        "temp_graph_*.html",
        "report_*.pdf",
        "temp_mat_*.png"
    ]

    now = time.time()
    deleted_count = 0
    failed_count = 0

    for pattern in patterns:
        search_path = os.path.join(target_dir, pattern)
        # 패턴과 일치하는 파일 목록 순회
        for file_path in glob.glob(search_path):
            try:
                # 파일의 마지막 수정 시간 확인
                file_mtime = os.path.getmtime(file_path)
                age = now - file_mtime

                # 기준 시간(1시간)을 초과한 파일만 선별 삭제
                if age > max_age_seconds:
                    os.remove(file_path)
                    logger.info(f"[GC] 임시 파일이 소거되었습니다: {file_path} (경과 시간: {int(age)}초)")
                    deleted_count += 1
            except FileNotFoundError:
                # 이미 다른 프로세스에 의해 삭제된 경우 예외 방어
                pass
            except Exception as e:
                logger.error(f"[GC] 임시 파일 삭제 중 오류 발생 ({file_path}): {e}")
                failed_count += 1

    return deleted_count, failed_count