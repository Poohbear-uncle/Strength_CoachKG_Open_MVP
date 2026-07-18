import json
import os

# 50대 강점 전체의 음과 양(과사용, 시너지, 보완, 상충) 학술 연구 및 코칭 명세 데이터
PATCH_DATA = {
    # 1. 성취 덕목군
    "STR_PERSEVERANCE": {
        "overuse": "중단해야 할 무의미한 목표에 집착하여 시간과 자원을 낭비하는 무모한 고집으로 변질될 수 있습니다.",
        "synergy_with": ["PSTR_ACHIEVEMENT_ORIENTED"], "balances": ["PSTR_FLEXIBILITY"], "conflicts_with": ["PSTR_FLEXIBILITY"]
    },
    "STR_PRUDENCE": {
        "overuse": "지나친 위험 회피 성향으로 인해 행동을 결단하지 못하고 기회를 놓치는 우유부단함으로 이어집니다.",
        "synergy_with": ["PSTR_ANALYTICAL_THINKING"], "balances": ["PSTR_INITIATIVE", "PSTR_ADVENTURE"], "conflicts_with": ["PSTR_ADVENTURE"]
    },
    "PSTR_ACTION": {
        "overuse": "충분한 숙고나 계획 없이 성급하게 행동에 옮겨 예상치 못한 리스크를 초래할 수 있습니다.",
        "synergy_with": ["PSTR_INITIATIVE"], "balances": ["STR_PRUDENCE"], "conflicts_with": ["STR_PRUDENCE"]
    },
    "PSTR_HARDWORK": {
        "overuse": "자신의 체력적 한계를 무시하고 일에 매몰되어 일과 삶의 균형을 잃고 번아웃에 빠질 위험이 큽니다.",
        "synergy_with": ["STR_PERSEVERANCE"], "balances": ["STR_ZEST", "STR_SELF_REGULATION"], "conflicts_with": ["STR_HUMOR"]
    },
    "PSTR_RESPONSIBILITY": {
        "overuse": "타인의 몫까지 과도하게 책임지려 하여 스스로 감당하기 어려운 무거운 중압감에 시달릴 수 있습니다.",
        "synergy_with": ["PSTR_HARDWORK"], "balances": ["PSTR_DIPLOMACY"], "conflicts_with": ["PSTR_FLEXIBILITY"]
    },
    "PSTR_TIME_OPTIMIZATION": {
        "overuse": "모든 일정을 지나치게 통제하려 하여 함께 협업하는 동료들에게 강박적인 압박감을 줄 수 있습니다.",
        "synergy_with": ["PSTR_DETAIL"], "balances": ["PSTR_ADAPTABILITY"], "conflicts_with": ["PSTR_ADAPTABILITY"]
    },
    "PSTR_DETAIL": {
        "overuse": "작은 미시적 디테일에만 너무 집착한 나머지, 숲을 보지 못하고 전체의 큰 흐름(대안)을 놓칠 수 있습니다.",
        "synergy_with": ["PSTR_ANALYTICAL_THINKING"], "balances": ["STR_PERSPECTIVE"], "conflicts_with": ["PSTR_STRATEGIC_THINKING"]
    },
    "PSTR_ACHIEVEMENT_ORIENTED": {
        "overuse": "오직 정량적 성과와 목표 달성에만 매몰되어 과정에서의 인간적 가치와 배려를 간과하기 쉽습니다.",
        "synergy_with": ["PSTR_HARDWORK"], "balances": ["STR_KINDNESS", "PSTR_EMPATHY"], "conflicts_with": ["PSTR_EMPATHY"]
    },
    "PSTR_STRATEGIC_THINKING": {
        "overuse": "현실적인 실행 방안보다는 상위 기획과 분석에만 에너지를 쏟아 탁상공론에 그칠 우려가 있습니다.",
        "synergy_with": ["STR_PERSPECTIVE"], "balances": ["PSTR_ACTION"], "conflicts_with": ["PSTR_DETAIL"]
    },
    "PSTR_IMPROVEMENT": {
        "overuse": "지속적인 개선과 완벽주의에만 집착하여 현재의 성과에 만족하지 못하고 끊임없는 불안감을 느낍니다.",
        "synergy_with": ["STR_LOVE_OF_LEARNING"], "balances": ["STR_GRATITUDE"], "conflicts_with": ["STR_SELF_REGULATION"]
    },
    "PSTR_COMPETITION": {
        "overuse": "동료를 협력자가 아닌 오직 이겨야 할 적으로 보아 조직 내 불필요한 적대감과 갈등을 부추길 수 있습니다.",
        "synergy_with": ["PSTR_ACHIEVEMENT_ORIENTED"], "balances": ["STR_TEAMWORK"], "conflicts_with": ["STR_TEAMWORK"]
    },

    # 2. 관계 덕목군
    "STR_KINDNESS": {
        "overuse": "자신의 정서적 욕구를 무시한 채 타인의 요구를 거절하지 못해 만성 피로와 감정적 소모를 겪게 됩니다.",
        "synergy_with": ["PSTR_EMPATHY"], "balances": ["STR_SELF_REGULATION", "STR_BRAVERY"], "conflicts_with": ["PSTR_CRITIQUE"]
    },
    "STR_TEAMWORK": {
        "overuse": "집단의 의견에 맹목적으로 동조하여 개인의 독립적이고 주체적인 비판 목소리를 내지 못하게 됩니다.",
        "synergy_with": ["PSTR_HARMONY"], "balances": ["STR_BRAVERY", "PSTR_CRITIQUE"], "conflicts_with": ["PSTR_INITIATIVE"]
    },
    "STR_LEADERSHIP": {
        "overuse": "강력한 주도력의 과용으로 인해 구성원들의 자율성을 침해하고 독단적인 지배 성향을 띨 수 있습니다.",
        "synergy_with": ["PSTR_PERSUASION"], "balances": ["STR_HUMILITY"], "conflicts_with": ["STR_HUMILITY"]
    },
    "STR_FAIRNESS": {
        "overuse": "규정과 기계적 형평성에만 과하게 집착하여 개별 구성원이 처한 특수한 사정과 맥락을 참작하지 못합니다.",
        "synergy_with": ["PSTR_CRITIQUE"], "balances": ["PSTR_EMPATHY", "STR_FORGIVENESS"], "conflicts_with": ["STR_FORGIVENESS"]
    },
    "STR_FORGIVENESS": {
        "overuse": "해를 끼친 타인에게 무조건적인 용서를 반복하여 상대방의 부조리한 행동을 학습 및 방조하는 결과를 낳습니다.",
        "synergy_with": ["STR_KINDNESS"], "balances": ["STR_FAIRNESS"], "conflicts_with": ["PSTR_CRITIQUE"]
    },
    "STR_SOCIAL_INTELLIGENCE": {
        "overuse": "상황에 맞춰 지나치게 처세를 조율하다 보니, 타인에게 기회주의적이거나 가식적인 사람으로 비칠 수 있습니다.",
        "synergy_with": ["PSTR_DIPLOMACY"], "balances": ["STR_HONESTY"], "conflicts_with": ["STR_HONESTY"]
    },
    "PSTR_EMPATHY": {
        "overuse": "타인의 감정적 고통과 슬픔을 지나치게 투사하여 흡수함으로써 심각한 정서적 피로와 우울감에 노출됩니다.",
        "synergy_with": ["STR_KINDNESS"], "balances": ["PSTR_ANALYTICAL_THINKING"], "conflicts_with": ["PSTR_CRITIQUE"]
    },
    "PSTR_SOCIABILITY": {
        "overuse": "넓은 인맥 구축에만 과도하게 에너지를 써 정작 깊이 있는 소수와의 신뢰 관계를 다지지 못할 수 있습니다.",
        "synergy_with": ["PSTR_COMMUNICATION"], "balances": ["STR_SELF_REGULATION"], "conflicts_with": ["PSTR_CRITIQUE"]
    },
    "PSTR_ACTIVE_LISTENING": {
        "overuse": "수용과 경청에만 집중하여 정작 본인의 확고한 입장이나 필요한 주장을 확실히 관철하지 못합니다.",
        "synergy_with": ["PSTR_EMPATHY"], "balances": ["PSTR_PERSUASION"], "conflicts_with": ["PSTR_PERSUASION"]
    },
    "PSTR_DIPLOMACY": {
        "overuse": "대립을 지나치게 회피하려다 보니 중요한 논쟁 국면에서 지나치게 모호한 중립적 입장만 고수하게 됩니다.",
        "synergy_with": ["STR_SOCIAL_INTELLIGENCE"], "balances": ["STR_HONESTY"], "conflicts_with": ["STR_HONESTY"]
    },
    "PSTR_RECOGNITION": {
        "overuse": "칭찬과 조율을 남발하여 정작 엄격한 피드백과 객관적인 평가가 무뎌지는 결과를 초래할 수 있습니다.",
        "synergy_with": ["STR_KINDNESS"], "balances": ["PSTR_CRITIQUE"], "conflicts_with": ["PSTR_CRITIQUE"]
    },
    "PSTR_HARMONY": {
        "overuse": "평화와 타협만을 강요하여, 조직의 건강한 성장을 위해 필수적인 건설적 파괴와 논쟁을 억압하게 됩니다.",
        "synergy_with": ["STR_TEAMWORK"], "balances": ["STR_BRAVERY", "PSTR_INITIATIVE"], "conflicts_with": ["PSTR_INITIATIVE"]
    },
    "PSTR_COMMUNICATION": {
        "overuse": "자신의 생각과 표현을 지나치게 쏟아내어 타인의 발언권을 침해하거나 불필요한 구설을 만들 수 있습니다.",
        "synergy_with": ["PSTR_SOCIABILITY"], "balances": ["PSTR_ACTIVE_LISTENING"], "conflicts_with": ["PSTR_ACTIVE_LISTENING"]
    },
    "PSTR_PERSUASION": {
        "overuse": "상대방의 입장을 무시하고 자신의 의견 관철만을 요구하는 고집스러운 독선이나 강요로 흐를 우려가 큽니다.",
        "synergy_with": ["STR_LEADERSHIP"], "balances": ["PSTR_ACTIVE_LISTENING"], "conflicts_with": ["PSTR_ACTIVE_LISTENING"]
    },

    # 3. 주도성 덕목군
    "STR_ZEST": {
        "overuse": "지나치게 하이텐션을 유지하여 정적이고 차분한 성찰이 필요한 환경에서 산만함을 야기할 수 있습니다.",
        "synergy_with": ["PSTR_OPTIMISM"], "balances": ["STR_SELF_REGULATION", "STR_PRUDENCE"], "conflicts_with": ["STR_PRUDENCE"]
    },
    "STR_HUMOR": {
        "overuse": "진지하고 엄숙한 격식이 필요한 상황에서도 가벼운 농담을 던져 분위기를 그르치거나 품위를 해칩니다.",
        "synergy_with": ["PSTR_SOCIABILITY"], "balances": ["STR_PRUDENCE"], "conflicts_with": ["PSTR_PRUDENCE"]
    },
    "PSTR_OPTIMISM": {
        "overuse": "대책 없는 장밋빛 전망에 기대어 실존하는 중대한 위험이나 구조적 경고 신호를 애써 외면할 우려가 있습니다.",
        "synergy_with": ["STR_ZEST"], "balances": ["STR_PRUDENCE", "PSTR_ANALYTICAL_THINKING"], "conflicts_with": ["STR_PRUDENCE"]
    },
    "PSTR_INITIATIVE": {
        "overuse": "상황에 대한 주도권을 억지로 독점하려 하여 주변 동료들의 팔로워십 의지를 꺾고 피로감을 줍니다.",
        "synergy_with": ["PSTR_ACTION"], "balances": ["STR_HUMILITY"], "conflicts_with": ["STR_HUMILITY"]
    },
    "PSTR_FLEXIBILITY": {
        "overuse": "일관성 있는 원칙이나 단단한 기준 없이 상황에 따라 너무 쉽게 흔들려 신뢰를 잃을 수 있습니다.",
        "synergy_with": ["PSTR_ADAPTABILITY"], "balances": ["STR_PERSEVERANCE"], "conflicts_with": ["STR_PERSEVERANCE"]
    },
    "PSTR_RESILIENCE": {
        "overuse": "심각한 좌절과 슬픔조차 애써 쿨하게 넘기려 감정을 억압하다 정서적인 병리 현상을 마주할 수 있습니다.",
        "synergy_with": ["PSTR_OPTIMISM"], "balances": ["PSTR_SELF_AWARENESS"], "conflicts_with": ["PSTR_EMPATHY"]
    },
    "PSTR_ADAPTABILITY": {
        "overuse": "외부 환경의 변화에 무조건 영합하여, 정작 주체적인 혁신이나 본인 고유의 고집을 지키지 못합니다.",
        "synergy_with": ["PSTR_FLEXIBILITY"], "balances": ["STR_PERSEVERANCE"], "conflicts_with": ["STR_PERSEVERANCE"]
    },
    "PSTR_ADVENTURE": {
        "overuse": "스릴과 새로운 자극에 중독되어 현실적인 안전장치나 리스크 한계를 넘어서는 위험한 배팅을 일삼습니다.",
        "synergy_with": ["PSTR_INITIATIVE"], "balances": ["STR_PRUDENCE"], "conflicts_with": ["STR_PRUDENCE"]
    },

    # 4. 탐구 덕목군
    "STR_LOVE_OF_LEARNING": {
        "overuse": "지식을 탐구하고 습득하는 과정 자체에만 몰두하여 실질적인 실행과 성과 도출을 외면할 위험이 있습니다.",
        "synergy_with": ["STR_CURIOSITY"], "balances": ["PSTR_ACTION"], "conflicts_with": ["PSTR_ACTION"]
    },
    "STR_CREATIVITY": {
        "overuse": "기존에 검증되어 작동하고 있는 전통적이고 표준적인 프로토콜마저 부정하여 비효율을 자초합니다.",
        "synergy_with": ["STR_CURIOSITY"], "balances": ["STR_PRUDENCE", "PSTR_DETAIL"], "conflicts_with": ["STR_SELF_REGULATION"]
    },
    "STR_CURIOSITY": {
        "overuse": "업무와 관련 없는 무관한 호기심에 한눈을 팔아 정작 몰입해야 할 일의 마감을 그르치기 쉽습니다.",
        "synergy_with": ["STR_LOVE_OF_LEARNING"], "balances": ["STR_SELF_REGULATION"], "conflicts_with": ["PSTR_DETAIL"]
    },
    "STR_PERSPECTIVE": {
        "overuse": "전체적이고 본질적인 흐름만 조망하려다 보니 당장 실행해야 할 구체적인 실무 디테일들을 간과하게 됩니다.",
        "synergy_with": ["PSTR_STRATEGIC_THINKING"], "balances": ["PSTR_DETAIL"], "conflicts_with": ["PSTR_DETAIL"]
    },
    "STR_APPRECIATION_BEAUTY": {
        "overuse": "지나친 탐미주의적 가치에 경도되어 차갑고 냉혹한 기성 현실 세계에 대한 괴리감과 무력감에 빠집니다.",
        "synergy_with": ["STR_SPIRITUALITY"], "balances": ["PSTR_ANALYTICAL_THINKING"], "conflicts_with": ["PSTR_ANALYTICAL_THINKING"]
    },
    "STR_SPIRITUALITY": {
        "overuse": "현실적 원인 분석이나 합리적인 논증을 건너뛰고 모든 상황을 명리나 영적 운명론으로 해석하려 듭니다.",
        "synergy_with": ["STR_APPRECIATION_BEAUTY"], "balances": ["PSTR_ANALYTICAL_THINKING"], "conflicts_with": ["PSTR_ANALYTICAL_THINKING"]
    },
    "PSTR_ANALYTICAL_THINKING": {
        "overuse": "분석 마비(Analysis Paralysis)에 빠져 모든 데이터가 다 모일 때까지 한 걸음도 전진하지 못합니다.",
        "synergy_with": ["PSTR_DETAIL"], "balances": ["PSTR_ACTION", "PSTR_OPTIMISM"], "conflicts_with": ["PSTR_OPTIMISM"]
    },
    "PSTR_OPEN_MINDEDNESS": {
        "overuse": "모든 주장과 가치관을 무조건 다 수용하느라 본인만의 확고한 가치 철학이나 주관을 상실하게 됩니다.",
        "synergy_with": ["STR_CURIOSITY"], "balances": ["PSTR_CRITIQUE"], "conflicts_with": ["STR_CRITIQUE"]
    },
    "PSTR_SOLUTION": {
        "overuse": "문제 해결 자체에 과집착하여, 당장 해결할 필요가 없는 가벼운 과제들까지 일을 키워 에너지를 낭비합니다.",
        "synergy_with": ["PSTR_ANALYTICAL_THINKING"], "balances": ["STR_FORGIVENESS"], "conflicts_with": ["PSTR_HARMONY"]
    },
    "PSTR_CRITIQUE": {
        "overuse": "매사 부정적인 트집을 잡거나 냉소적인 비판을 쏟아내어 주변 동료들의 의욕과 동기를 심각하게 훼손합니다.",
        "synergy_with": ["PSTR_ANALYTICAL_THINKING"], "balances": ["STR_KINDNESS", "PSTR_RECOGNITION"], "conflicts_with": ["PSTR_RECOGNITION"]
    },

    # 5. 자치 덕목군
    "STR_SELF_REGULATION": {
        "overuse": "자기 감정과 욕구를 한 치의 오차도 없이 통제하려 하여 인간적인 자연스러움과 활력을 완전히 억압합니다.",
        "synergy_with": ["STR_PRUDENCE"], "balances": ["STR_ZEST", "STR_HUMOR"], "conflicts_with": ["STR_ZEST"]
    },
    "STR_BRAVERY": {
        "overuse": "자신의 능력을 과신하여 무리하게 위험한 상황에 정면으로 돌진해 만성적인 피해를 자초할 우려가 큽니다.",
        "synergy_with": ["PSTR_INITIATIVE"], "balances": ["STR_PRUDENCE"], "conflicts_with": ["STR_PRUDENCE"]
    },
    "STR_HONESTY": {
        "overuse": "상대방의 감정 상태나 상황 맥락을 참작하지 않고 지나치게 날 선 진실을 쏟아내어 깊은 상처를 줍니다.",
        "synergy_with": ["STR_BRAVERY"], "balances": ["PSTR_DIPLOMACY", "STR_SOCIAL_INTELLIGENCE"], "conflicts_with": ["PSTR_DIPLOMACY"]
    },
    "STR_GRATITUDE": {
        "overuse": "부조리하고 억압적인 착취 환경조차도 세상을 향한 과도한 감사 기도로 승화시켜 현실 개선의 동기를 상실합니다.",
        "synergy_with": ["PSTR_OPTIMISM"], "balances": ["PSTR_CRITIQUE"], "conflicts_with": ["PSTR_CRITIQUE"]
    },
    "STR_HUMILITY": {
        "overuse": "지나친 자기비하적 겸손으로 일관하여 정당한 본인의 업적과 성과 공로마저 가려버리는 피해를 입게 됩니다.",
        "synergy_with": ["STR_SELF_REGULATION"], "balances": ["PSTR_SELF_ESTEEM", "STR_BRAVERY"], "conflicts_with": ["PSTR_INITIATIVE"]
    },
    "PSTR_SELF_ESTEEM": {
        "overuse": "자신에 대한 자존적 우월감이 도를 넘어 타인의 조언이나 충고를 거만하게 묵살하는 아집으로 고착됩니다.",
        "synergy_with": ["PSTR_INITIATIVE"], "balances": ["STR_HUMILITY"], "conflicts_with": ["STR_HUMILITY"]
    },
    "PSTR_SELF_AWARENESS": {
        "overuse": "자신의 내부 상태에만 과도하게 성찰 초점을 맞추느라, 정작 외부 환경의 변화나 동향을 감지하지 못합니다.",
        "synergy_with": ["STR_PERSPECTIVE"], "balances": ["STR_SOCIAL_INTELLIGENCE"], "conflicts_with": ["PSTR_SOCIABILITY"]
    }
}

def patch_strengths_ontology():
    """
    기존 data/strengths.json 파일을 정밀 읽기하여,
    비어 있던 50대 강점의 overuse, synergy_with, balances, conflicts_with 데이터를
    학술적 역동성 명세에 맞추어 100% 완전 복원 및 주입합니다.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "data", "strengths.json")
    
    if not os.path.exists(json_path):
        print(f"❌ 복원 실패: 온톨로지 파일 위치를 확인해 주세요. (조회 경로: {json_path})")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    strengths = data.get("strengths", [])
    patched_count = 0
    
    # 루프를 돌며 비어있던 속성 일괄 복원 및 업데이트
    for s in strengths:
        code = s.get("code")
        if code in PATCH_DATA:
            patch = PATCH_DATA[code]
            
            # 음과 양의 완전 복원 매핑
            s["overuse"] = patch["overuse"]
            s["synergy_with"] = patch["synergy_with"]
            s["balances"] = patch["balances"]
            s["conflicts_with"] = patch["conflicts_with"]
            patched_count += 1
            
    # 정규화 가공된 데이터를 다시 strengths.json에 단일 진실 공급원(SoT)으로 갱신 적재
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 온톨로지 전수 복원 완료! 총 {patched_count}개 강점의 음-양(과사용/관계성) 데이터가 완벽 수렴 적재되었습니다.")

if __name__ == "__main__":
    patch_strengths_ontology()