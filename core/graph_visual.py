import os
import tempfile
from pyvis.network import Network
from core.assessment import load_ontology

def build_pyvis_graph(session_token, top_results):
    """
    session_token: 사용자의 고유 브라우저 세션 식별 토큰
    top_results: 사용자의 상위 대표 강점 5개 리스트
    
    PyVis를 활용해 강점과 소속 덕목 간의 관계 맵을 동적 HTML로 내보냅니다.
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
    net.force_atlas_2based(gravity=-50, central_gravity=0.01, spring_length=100)
    
    # 3. 온톨로지 로드
    ontology = load_ontology()
    strength_map = {s["code"]: s for s in ontology["strengths"]}
    
    top_codes = [r["code"] for r in top_results]
    added_virtues = set()
    
    # =========================================================================
    # [패스 1] 모든 노드(강점 노드 및 소속 덕목 노드)를 선제적으로 전체 등록합니다.
    # =========================================================================
    for item in top_results:
        code = item["code"]
        name = item["name"]
        score = item["final_score"]
        virtue_name = item["virtue"]
        
        # 1) 강점 노드 추가 (파란색 계열, 점수에 비례한 크기 제공)
        net.add_node(
            code, 
            label=name, 
            title=f"강점: {name}<br>분석 점수: {score}점", 
            color="#2ecc71", # 부드러운 초록
            size=int(score * 5) + 10, # 점수가 높을수록 노드 크기 증가
            shape="dot"
        )
        
        # 2) 소속 덕목 노드 추가 (보라색 계열, 고정 크기)
        if virtue_name not in added_virtues:
            net.add_node(
                virtue_name, 
                label=virtue_name, 
                title=f"상위 덕목: {virtue_name}", 
                color="#9b5de5", # 우아한 보라색
                size=28, 
                shape="triangle"
            )
            added_virtues.add(virtue_name)

    # =========================================================================
    # [패스 2] 모든 노드가 존재하는 것이 100% 보장된 상태에서 안전하게 간선을 연결합니다.
    # =========================================================================
    for item in top_results:
        code = item["code"]
        virtue_name = item["virtue"]
        
        # 1) 강점 -> 소속 덕목 간의 기본 소속 관계 간선(BELONGS_TO) 추가
        net.add_edge(code, virtue_name, value=2, color="#bdc3c7", title="소속됨")
        
        # 2) 온톨로지 상의 상호 관계성 탐색 및 연계 간선 추가 (Top 5 강점들끼리만 연결)
        if code in strength_map:
            s_detail = strength_map[code]
            
            # 시너지 관계선 (녹색 실선)
            for syn in s_detail.get("synergy_with", []):
                if syn in top_codes:
                    if syn in net.get_nodes(): # 혹시 모를 안전 장치 작동
                        net.add_edge(code, syn, value=1.5, color="#2ecc71", title="상호 시너지")
                    
            # 보완/균형 관계선 (주황색 대시선)
            for bal in s_detail.get("balances", []):
                if bal in top_codes:
                    if bal in net.get_nodes():
                        net.add_edge(code, bal, value=1.5, color="#e67e22", dashes=True, title="상호 보완적 균형")
                    
            # 충돌/대립 관계선 (빨간색 점선)
            for con in s_detail.get("conflicts_with", []):
                if con in top_codes:
                    if con in net.get_nodes():
                        net.add_edge(code, con, value=1.0, color="#e74c3c", dashes=[5, 5], title="주의가 필요한 상충")

    # 5. 로컬 물리적 파일로 빌드 저장
    net.write_html(output_path)
    
    return output_path