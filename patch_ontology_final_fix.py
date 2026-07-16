import json
import os

def apply_final_typo_fixes():
    """
    온톨로지 내 잘못 교차 참조된 두 개의 코드 오탈자를 일괄 자동 치환합니다.
    - PSTR_PRUDENCE -> STR_PRUDENCE (신중함 정정)
    - STR_CRITIQUE -> PSTR_CRITIQUE (비판적 사고 정정)
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "data", "strengths.json")
    
    if not os.path.exists(json_path):
        print(f"❌ 교정 실패: strengths.json 파일 위치를 확인해 주세요.")
        return
        
    # 파일 읽기
    with open(json_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
        
    # 글로벌 교차 오탈자 일괄 문자열 치환 수행 (참조 오류 완벽 격리)
    fixed_content = file_content.replace('"PSTR_PRUDENCE"', '"STR_PRUDENCE"')
    fixed_content = fixed_content.replace('"STR_CRITIQUE"', '"PSTR_CRITIQUE"')
    
    # 교정본 다시 쓰기
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
        
    print("✅ 온톨로지 참조 오탈자 전수 정정 완료! (무결성 확보 완료)")

if __name__ == "__main__":
    apply_final_typo_fixes()