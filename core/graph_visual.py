import os
import tempfile  # [보완] 안전한 시스템 임시 경로 활용을 위해 추가
from pyvis.network import Network
from core.assessment import load_ontology

def build_pyvis_graph(session_token, top_results):
    """
    session_token: 사용자의 고유 브라우저 세션 식별 토큰
    top_results: 사용자의 상위 대표 강점 5개 리스트
    
    PyVis를 활용해 강점과 소속 덕목 간의 관계 맵을 3D 형태의 동적 HTML로 내보냅니다.
    """
    # 1. 고유 파일명 지정 및 시스템 임시 경로(Temp) 정의
    output_filename = f"temp_graph_{session_token}.html"
    
    # [보완] Streamlit Cloud의 파일 쓰기 제한을 회피하기 위해 시스템 공식 임시 디렉터리 경로 활용
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, output_filename)
    
    # 2. PyVis 네트워크 객체 정의 (안정적인 물리 엔진 세팅)
    # [핵심 보완] cdn_resources='remote' 설정을 추가하여 로컬 'lib/' 폴더 생성을 원천 차단하고 원격 HTTPS CDN을 사용합니다.
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
    
    # 4. 노드 추가 규칙
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
            color="#2ecc71", 
            size=int(score * 5) + 10, 
            shape="dot"
        )
        
        # 2) 소속 덕목 노드 추가 (보라색 계열, 고정 크기)
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
            
        # 3) 강점 -> 소속 덕목 간의 기본 소속 관계 간선(BELONGS_TO) 추가
        net.add_edge(code, virtue_name, value=2, color="#bdc3c7", title="소속됨")
        
        # 4) 온톨로지 상의 관계성 탐색 및 연계 간선 추가 (Top 5 강점들끼리의 연계성 위주로 매핑)
        if code in strength_map:
            s_detail = strength_map[code]
            
            # 시너지 관계선 (녹색 실선)
            for syn in s_detail.get("synergy_with", []):
                if syn in top_codes:
                    net.add_edge(code, syn, value=1.5, color="#2ecc71", title="상호 시너지")
                    
            # 보완/균형 관계선 (주황색 대시선)
            for bal in s_detail.get("balances", []):
                if bal in top_codes:
                    net.add_edge(code, bal, value=1.5, color="#e67e22", dashes=True, title="상호 보완적 균형")
                    
            # 충돌/대립 관계선 (빨간색 점선)
            for con in s_detail.get("conflicts_with", []):
                if con in top_codes:
                    net.add_edge(code, con, value=1.0, color="#e74c3c", dashes=[5, 5], title="주의가 필요한 상충")

    # 5. 로컬 물리적 파일로 빌드 저장
    net.write_html(output_path)
    
    return output_path