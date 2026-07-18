# core/graph_visual.py
import os
import json
from pyvis.network import Network
from core.assessment import load_ontology

def build_pyvis_graph(session_id, top_5, depth=1):
    """
    사용자의 상위 5대 강점을 기반으로 온톨로지 관계망 지도를 빌드하여 HTML 파일 경로를 반환합니다.
    (Streamlit Base64 Iframe 환경에서 안정적으로 동작하도록 CDN 강제 주입 모델을 사용합니다.)
    
    :param session_id: 세션별 파일 격리를 위한 ID
    :param top_5: 분석 점수가 가장 높은 상위 5개 강점 객체 리스트
    :param depth: 탐색 깊이 (1: 직접 연계만 보기, 2: 간접 연계 강점들까지 확장)
    """
    # 1. 온톨로지 단일 공급원 로드
    ontology = load_ontology()
    s_map = {s["code"]: s for s in ontology["strengths"]}
    v_map = {v["code"]: v for v in ontology["virtues"]}
    
    # strengths.json의 역매핑 사전 구축 (덕목 이름 -> 덕목 코드)
    virtue_name_to_code = {v["name"]: v["code"] for v in ontology["virtues"]}
    
    core_codes = [r["code"] for r in top_5]
    
    # 2. 너비 우선 탐색(BFS) 기반 노드 및 엣지 수집
    nodes_to_add = {}  # {code: {'level': 0/1/2, 'type': 'Strength/Virtue'}}
    edges_to_add = set()  # {(source, target, rel_type)}
    
    # [Level 0] 핵심 5대 강점 및 소속 덕목 기본 배치
    for r in top_5:
        code = r["code"]
        if code in s_map:
            nodes_to_add[code] = {"level": 0, "type": "Strength"}
            
            # 역매핑 사전을 이용해 안전하게 대덕목 노드 추출 및 배치
            v_name = s_map[code].get("virtue_name")
            v_code = virtue_name_to_code.get(v_name)
            
            if v_code:
                nodes_to_add[v_code] = {"level": 0, "type": "Virtue"}
                edges_to_add.add((code, v_code, "BELONGS_TO"))

    # [Level 1 & 2] 깊이(depth)에 따라 유기적 이웃 관계 탐색
    current_frontier = set(core_codes)
    
    for current_depth in range(1, depth + 1):
        next_frontier = set()
        for code in current_frontier:
            if code not in s_map:
                continue
                
            s_detail = s_map[code]
            relations = {
                "SYNERGY_WITH": s_detail.get("synergy_with", []),
                "BALANCES": s_detail.get("balances", []),
                "CONFLICTS_WITH": s_detail.get("conflicts_with", [])
            }
            
            for rel_type, targets in relations.items():
                for t_code in targets:
                    if t_code in s_map:
                        if t_code not in nodes_to_add:
                            nodes_to_add[t_code] = {"level": current_depth, "type": "Strength"}
                            next_frontier.add(t_code)
                        
                        edge_key = (min(code, t_code), max(code, t_code), rel_type)
                        edges_to_add.add(edge_key)
                        
        current_frontier = next_frontier

    # 3. PyVis 네트워크 생성 (cdn_resources='remote' 옵션으로 로컬 의존성 차단)
    net = Network(
        height="550px", 
        width="100%", 
        bgcolor="#ffffff", 
        font_color="#2c3e50",
        cdn_resources="remote"  # 절대 경로 CDN 사용 지시
    )
    
    # 4. 물리엔진 정합성 설정 (딕셔너리 정형화 주입으로 문법 오류 원천 방지)
    graph_options = {
      "nodes": {
        "borderWidth": 1.5,
        "borderWidthSelected": 3
      },
      "edges": {
        "smooth": {
          "type": "continuous",
          "forceDirection": "none"
        }
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -6000,
          "centralGravity": 0.35,
          "springLength": 95,
          "springConstant": 0.04
        },
        "minVelocity": 0.75
      }
    }
    net.set_options(json.dumps(graph_options))
    
    # 5. 수집된 노드 PyVis에 등록
    for code, meta in nodes_to_add.items():
        lvl = meta["level"]
        ntype = meta["type"]
        
        node_style = {
            "id": code,
            "label": code,
            "size": 15,
            "color": "#bdc3c7",
            "shape": "dot"
        }
        
        if ntype == "Virtue":
            node_style.update({
                "label": v_map.get(code, {}).get("name", code),
                "size": 22,
                "color": "#9b59b6",
                "shape": "triangle"
            })
        else:
            name = s_map.get(code, {}).get("name", code)
            node_style["label"] = name
            
            if lvl == 0:
                node_style.update({
                    "size": 26,
                    "color": "#2ecc71",
                    "shape": "dot"
                })
            elif lvl == 1:
                node_style.update({
                    "size": 16,
                    "color": "#34495e",
                    "shape": "dot"
                })
            elif lvl == 2:
                node_style.update({
                    "size": 10,
                    "color": "#d1d5db",
                    "shape": "dot"
                })
                
        # pyvis Network.add_node()의 첫 인자명은 'n_id'이지 'id'가 아니므로
        # 딕셔너리를 그대로 언패킹하면 TypeError(n_id 누락)가 발생함.
        net.add_node(node_style.pop("id"), **node_style)

    # 6. 수집된 엣지 PyVis에 등록
    for source, target, rel_type in edges_to_add:
        edge_style = {
            "source": source,
            "to": target,
            "width": 1,
            "color": "#bdc3c7"
        }
        
        if rel_type == "BELONGS_TO":
            edge_style.update({"width": 0.8, "color": "#e2e8f0"})
        elif rel_type == "SYNERGY_WITH":
            edge_style.update({"width": 1.8, "color": "#2ecc71"})
        elif rel_type == "BALANCES":
            edge_style.update({"width": 1.5, "color": "#e67e22", "dashes": True})
        elif rel_type == "CONFLICTS_WITH":
            edge_style.update({"width": 1.5, "color": "#e74c3c", "dashes": [2, 8]})
            
        net.add_edge(**edge_style)

    # 7. 파일 저장 및 Streamlit 절대 경로 반환
    output_folder = "/tmp"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    output_path = os.path.join(output_folder, f"temp_graph_{session_id}.html")
    net.save_graph(output_path)
    
    # [이중 방어막] PyVis가 간혹 저장 템플릿 내부에 남겨놓는 로컬 상대 경로 링크를 온라인 CDN 주소로 강제 교정합니다.
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 상대 경로 자바스크립트 참조를 무조건 절대 경로(CDN)로 변환
        html_content = html_content.replace(
            'lib/vis-10.1.0/vis-network.min.js',
            'https://unpkg.com/vis-network/standalone/umd/vis-network.min.js'
        ).replace(
            'lib/bindings/utils.js',
            'https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js'
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
    return output_path