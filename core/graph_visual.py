import os
import tempfile
from pyvis.network import Network
from core.assessment import load_ontology

def build_pyvis_graph(session_token, top_results):
    """
    session_token: 사용자의 고유 브라우저 세션 식별 토큰
    top_results: 사용자의 상위 대표 강점 5개 리스트
    
    PyVis를 활용해 강점과 소속 덕목, 그리고 주변부 연계 강점들까지 확장하여 
    풍부한 온톨로지 지식망 HTML을 내보냅니다.
    """
    # 1. 고유 파일명 지정 및 시스템 임시 경로(Temp) 정의
    output_filename = f"temp_graph_{session_token}.html"
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, output_filename)
    
    # 2. PyVis 네트워크 객체 정의 (원격 CDN 설정 활성화)
    net = Network(
        height="400px", 
        width="100%", 
        bgcolor="#fdfdfd", 
        font_color="#2c3e50",
        cdn_resources='remote'
    )
    
    # 그래프 조작 제어 도구 숨김 및 노드 스프링 탄력성 강화
    net.toggle_physics(True)
    net.force_atlas_2based(gravity=-60, central_gravity=0.01, spring_length=120)
    
    # 3. 온톨로지 로드
    ontology = load_ontology()
    strength_map = {s["code"]: s for s in ontology["strengths"]}
    
    top_codes = [r["code"] for r in top_results]
    added_nodes = set(top_codes) # 추적용 노드 세트 (중복 추가 방지)
    added_virtues = set()
    
    # =========================================================================
    # [패스 1] 핵심 노드 등록 (나의 대표 5대 강점 및 상위 덕목 노드)
    # =========================================================================
    for item in top_results:
        code = item["code"]
        name = item["name"]
        score = item["final_score"]
        virtue_name = item["virtue"]
        
        # 1) 나의 5대 핵심 강점 노드 (초록색 원, 점수에 비례한 크기 제공)
        net.add_node(
            code, 
            label=name, 
            title=f"대표 강점: {name}<br>분석 점수: {score}점", 
            color="#2ecc71", 
            size=int(score * 5) + 12, 
            shape="dot"
        )
        
        # 2) 소속 덕목 노드 (보라색 삼각형)
        if virtue_name not in added_virtues:
            net.add_node(
                virtue_name, 
                label=virtue_name, 
                title=f"상위 덕목: {virtue_name}", 
                color="#9b5de5", 
                size=28, 
                shape="triangle"
            )
            added_virtues.add(virtue_name)

    # =========================================================================
    # [패스 2 - 풍부성 확장] 나의 대표 강점과 연계되어 있는 주변부 관계망 노드 자동 탐색 및 생성
    # =========================================================================
    for item in top_results:
        code = item["code"]
        if code in strength_map:
            s_detail = strength_map[code]
            # 해당 대표 강점과 엮여 있는 시너지, 보완, 상충 강점 코드 리스트 수집
            related_candidates = (
                s_detail.get("synergy_with", []) + 
                s_detail.get("balances", []) + 
                s_detail.get("conflicts_with", [])
            )
            
            for rel_code in related_candidates:
                if rel_code not in added_nodes and rel_code in strength_map:
                    rel_name = strength_map[rel_code]["name"]
                    # 주변부 보완/연계 영역 노드 (작은 회색 원) 등록
                    net.add_node(
                        rel_code,
                        label=rel_name,
                        title=f"연계 강점: {rel_name}<br>(성장을 돕는 대표 잠재 영역)",
                        color="#dfe6e9", # 부드러운 밝은 회색
                        size=15,
                        shape="dot"
                    )
                    added_nodes.add(rel_code)

    # =========================================================================
    # [패스 3] 전원 안전 지대 확보 완료 상태에서 온톨로지 간선(Edge) 매핑
    # =========================================================================
    for item in top_results:
        code = item["code"]
        virtue_name = item["virtue"]
        
        # 1) 기본 소속선 관계 추가 (회색 실선)
        net.add_edge(code, virtue_name, value=2, color="#bdc3c7", title="소속됨")
        
        # 2) 유기적 관계선 추가 (보조 확장 노드까지 포함하여 연결)
        if code in strength_map:
            s_detail = strength_map[code]
            
            # 시너지 관계선 (초록색 실선)
            for syn in s_detail.get("synergy_with", []):
                if syn in added_nodes:
                    if syn in net.get_nodes():
                        net.add_edge(code, syn, value=1.5, color="#2ecc71", title="상호 시너지 효과")
                    
            # 보완/균형 관계선 (주황색 대시선)
            for bal in s_detail.get("balances", []):
                if bal in added_nodes:
                    if bal in net.get_nodes():
                        net.add_edge(code, bal, value=1.5, color="#e67e22", dashes=True, title="상호 보완 균형 조화")
                    
            # 충돌/대립 관계선 (빨간색 점선)
            for con in s_detail.get("conflicts_with", []):
                if con in added_nodes:
                    if con in net.get_nodes():
                        net.add_edge(code, con, value=1.0, color="#e74c3c", dashes=[4, 4], title="주의가 필요한 성향적 대립")

    # 5. 로컬 물리적 파일로 빌드 저장
    net.write_html(output_path)
    return output_path