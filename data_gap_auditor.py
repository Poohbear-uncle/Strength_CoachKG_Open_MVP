import json
import os

def audit_strengths_ontology(json_path=None):
    """
    50대 강점 온톨로지의 데이터 공백 및 참조 무결성(Referential Integrity) 정밀 검사
    """
    if json_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "data", "strengths.json")
        
    if not os.path.exists(json_path):
        print(f"❌ 분석 실패: 온톨로지 파일을 지정된 경로에서 찾을 수 없습니다.")
        print(f"🔍 확인 시도한 경로: {json_path}")
        return []
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    strengths = data.get("strengths", [])
    
    # [수정] 보이지 않는 앞뒤 공백으로 인한 매칭 실패를 방지하기 위해 strip() 처리 적용
    all_codes = {s["code"].strip() for s in strengths}
    
    audit_report = []
    
    for s in strengths:
        code = s.get("code", "").strip()
        name = s.get("name")
        
        missing_fields = []
        if not s.get("overuse"): 
            missing_fields.append("overuse(과사용 위험성)")
        if not s.get("synergy_with"): 
            missing_fields.append("synergy_with(시너지 관계)")
        if not s.get("balances"): 
            missing_fields.append("balances(보완 균형)")
        if not s.get("conflicts_with"): 
            missing_fields.append("conflicts_with(대립/상충)")
            
        # 참조 무결성 검사 (참조 코드도 양끝 공백을 제거하고 대조)
        invalid_references = []
        raw_relations = s.get("synergy_with", []) + s.get("balances", []) + s.get("conflicts_with", [])
        for ref_code in raw_relations:
            clean_ref = ref_code.strip()
            if clean_ref not in all_codes:
                invalid_references.append(clean_ref)
                
        if missing_fields or invalid_references:
            audit_report.append({
                "code": code,
                "name": name,
                "missing_fields": missing_fields,
                "invalid_references": invalid_references
            })
            
    print(f"📊 전수 조사 결과: 전체 {len(strengths)}개 강점 중 {len(audit_report)}개 항목에서 데이터 공백 및 무효 참조 발견")
    return audit_report

if __name__ == "__main__":
    report = audit_strengths_ontology()
    if report:
        print("\n=== 🚨 데이터 공백 및 무효 참조 코드 정밀 진단 결과 ===")
        for item in report:
            print(f"❌ [{item['name']} ({item['code']})]")
            if item['missing_fields']:
                print(f"   ㄴ 누락 속성: {', '.join(item['missing_fields'])}")
            if item['invalid_references']:
                # [디버그 출력 추가] 어떤 참조 코드가 실제 존재하지 않는지 명확하게 규명합니다.
                print(f"   ㄴ ⚠️ 무효한 코드 참조(존재하지 않는 코드): {', '.join(item['invalid_references'])}")
    else:
        print("\n✅ 축하합니다! 온톨로지 파일의 무결성이 완벽하며 데이터 공백이 전혀 발견되지 않았습니다.")