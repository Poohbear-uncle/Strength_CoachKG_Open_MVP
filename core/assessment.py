import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ONTOLOGY_PATH = os.path.join(DATA_DIR, "strengths.json")

def load_ontology():
    """
    정적 strengths.json 파일로부터 전체 덕목 및 강점 마스터 데이터를 읽어옵니다.
    """
    if not os.path.exists(ONTOLOGY_PATH):
        raise FileNotFoundError(f"온톨로지 데이터를 찾을 수 없습니다: {ONTOLOGY_PATH}")
        
    with open(ONTOLOGY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def calculate_scores(card_sorting, survey_responses):
    """
    card_sorting: {"STR_CREATIVITY": "A", "STR_CURIOSITY": "C", ...}
    survey_responses: {"STR_CREATIVITY": 5, ...} (A그룹으로 선별된 항목만 5점 척도 답변 존재)
    
    [기초 알고리즘 계산 규칙]
    - 기본 가중치 점수 부여: A그룹(대표강점)은 기본 3.0점, B그룹(보완강점)은 기본 2.0점,
      C그룹(일반/미개발)은 1.0점 부여 (3분류 UI 의미를 반영해 A>B>C 우선순위 유지)
    - 리커트 척도 검증 가중치: A그룹 중 슬라이더로 입력받은 검증 점수(1~5점)를 0.4 배율로 정규화 반영
    - 최종 점수 범위: 대표강점(A)은 검증에 따라 3.4 ~ 5.0점, 보완강점(B)은 2.0점 고정, 일반강점(C)은 1.0점 고정
    """
    ontology = load_ontology()
    results = []
    
    # 강점 데이터를 쉽게 매핑하기 위해 리스트를 사전으로 변환
    strength_map = {s["code"]: s for s in ontology["strengths"]}
    
    for code, group in card_sorting.items():
        if code not in strength_map:
            continue
            
        s_info = strength_map[code]
        if group == "A":
            base_score = 3.0
        elif group == "B":
            base_score = 2.0
        else:  # C
            base_score = 1.0
        survey_addon = 0.0
        
        # A그룹 선별 강점 중 설문 응답이 있는 경우 가중치 추가
        if group == "A" and code in survey_responses:
            val = survey_responses[code]
            # 1~5점 입력을 0.4~2.0점 범위의 가중치로 가공 (예: 5점 선택 시 2.0점 합산되어 총점 5.0점 완료)
            survey_addon = float(val) * 0.4
            
        final_score = round(base_score + survey_addon, 2)
        
        results.append({
            "code": code,
            "name": s_info["name"],
            "virtue": s_info.get("virtue_name", "미분류"),
            "virtue_code": s_info.get("virtue_code", "VIR_UNKNOWN"),
            "group": group,
            "final_score": final_score,
            "summary": s_info.get("summary", ""),
            "keywords": s_info.get("keywords", [])
        })
        
    # 최종 연산된 점수를 기준으로 정렬 (내림차순)
    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results