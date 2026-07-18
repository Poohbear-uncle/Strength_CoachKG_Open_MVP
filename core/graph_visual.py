# core/graph_visual.py
import os
import json
from pyvis.network import Network
from core.assessment import load_ontology

def build_pyvis_graph(session_id, top_5, depth=1):
    """
    사용자의 상위 5대 강점을 기반으로 온톨로지 관계망 지도를 빌드하여 HTML 파일 경로를 반환합니다.
    
    :param session_id: 세션별 파일 격리를 위한 ID
    :param top_5: 분석 점수가 가장 높은 상위 5개 강점 객체 리스트
    :param depth: 탐색 깊이 (1: 직접 연계만 보기, 2: 간접 연계 강점들까지 확장)
    """
    # 1. 온톨로지 단일 공급원 로드
    ontology = load_ontology()
    s_map = {s["code"]: s for s in ontology["strengths"]}
    v_map = {v["code"]: v for v in ontology["virtues"]}
    
    core_codes = [r["code"] for r in top_5]
    
    # 2. 너비 우선 탐색(BFS) 기반 노드 및 엣지 수집
    nodes_to_add = {}  # {code: {'level': 0/1/2, 'type': 'Strength/Virtue'}}
    edges_to_add = set()  # {(source, target, rel_type)}
    
    # [Level 0] 핵심 5대 강점 및 소속 덕목 기본 배치
    for r in top_5:
        code = r["code"]
        if code in s_map:
            nodes_to_add[code] = {"level": 0, "type": "Strength"}
            # 소속 덕목 노드 및 소속(BELONGS_TO) 엣지 추가
            v_code = s_map[code].get("virtue_code")
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
            # 온톨로지 관계 유형 분류
            relations = {
                "SYNERGY_WITH": s_detail.get("synergy_with", []),
                "BALANCES": s_detail.get("balances", []),
                "CONFLICTS_WITH": s_detail.get("conflicts_with", [])
            }
            
            for rel_type, targets in relations.items():
                for t_code in targets:
                    if t_code in s_map:
                        # 아직 발견되지 않은 노드인 경우에만 레벨 부여
                        if t_code not in nodes_to_add:
                            nodes_to_add[t_code] = {"level": current_depth, "type": "Strength"}
                            next_frontier.add(t_code)
                        
                        # 무방향성 엣지 중복 방지 정렬하여 엣지 수집
                        edge_key = (min(code, t_code), max(code, t_code), rel_type)
                        edges_to_add.add(edge_key)
                        
        current_frontier = next_frontier

    # 3. PyVis 네트워크 그래프 생성 및 설정
    net = Network(height="550px", width="100%", bgcolor="#ffffff", font_color="#2c3e50")
    
    # 그래프 렌더링에 필요한 물리 시뮬레이션 옵션 최적화 (진동 방지 및 밀집 억제)
    net.set_options("""
    var options = {
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
    """)
    
    # 4. 수집된 노드 PyVis에 등록 (계층별 스타일 디테일링 차등화)
    for code, meta in nodes_to_add.items():
        lvl = meta["level"]
        ntype = meta["type"]
        
        # 기본 스타일셋 정의
        node_style = {
            "id": code,
            "label": code,
            "size": 15,
            "color": "#bdc3c7",
            "shape": "dot"
        }
        
        if ntype == "Virtue":
            # 대덕목 노드 스타일링 (Amethyst Purple)
            node_style.update({
                "label": v_map.get(code, {}).get("name", code),
                "size": 22,
                "color": "#9b59b6",
                "shape": "triangle"
            })
        else:
            # 강점 노드 레벨별 시각 위계 정의
            name = s_map.get(code, {}).get("name", code)
            node_style["label"] = name
            
            if lvl == 0:
                # 상위 5대 핵심 강점 (Emerald Green, 크게 노출)
                node_style.update({
                    "size": 26,
                    "color": "#2ecc71",
                    "shape": "dot"
                })
            elif lvl == 1:
                # 1차 이웃 관계 강점 (Slate Blue, 중간 노출)
                node_style.update({
                    "size": 16,
                    "color": "#34495e",
                    "shape": "dot"
                })
            elif lvl == 2:
                # 2차 이웃 확장 강점 (Silver Grey, 작고 투명하게 조정하여 시각 노이즈 차단)
                node_style.update({
                    "size": 10,
                    "color": "#d1d5db",
                    "shape": "dot"
                })
                
        net.add_node(**node_style)

    # 5. 수집된 엣지 PyVis에 등록
    for source, target, rel_type in edges_to_add:
        edge_style = {
            "source": source,
            "to": target,
            "width": 1,
            "color": "#bdc3c7"
        }
        
        if rel_type == "BELONGS_TO":
            # 덕목 귀속선 (실선, 가늘게 표현)
            edge_style.update({"width": 0.8, "color": "#e2e8f0"})
        elif rel_type == "SYNERGY_WITH":
            # 시너지 관계 (선명한 초록색 실선)
            edge_style.update({"width": 1.8, "color": "#2ecc71"})
        elif rel_type == "BALANCES":
            # 보완 균형 관계 (주황색 대시선)
            edge_style.update({"width": 1.5, "color": "#e67e22", "dashes": True})
        elif rel_type == "CONFLICTS_WITH":
            # 대립 상충 관계 (빨간색 점선)
            edge_style.update({"width": 1.5, "color": "#e74c3c", "dashes": [2, 8]})
            
        net.add_edge(**edge_style)

    # 6. 임시 저장 및 절대 경로 반환
    output_folder = "/tmp"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    output_path = os.path.join(output_folder, f"temp_graph_{session_id}.html")
    net.save_graph(output_path)
    
    return output_path