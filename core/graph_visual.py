# core/graph_visual.py
import os
import json
import tempfile
import traceback
from pyvis.network import Network
from core.assessment import load_ontology

def build_pyvis_graph(session_id, top_5, depth=1):
    """
    사용자의 상위 5대 강점을 기반으로 온톨로지 관계망 지도를 빌드하여 HTML 파일 경로를 반환합니다.
    절대로 예외를 밖으로 던지지 않고, 실패 시 None을 반환하여 메인 프로세스를 보호합니다.
    """
    print("\n" + "="*60)
    print("[GRAPH] 1. build_pyvis_graph 진입 및 초기화 시작")
    print(f"[GRAPH] Session ID: {session_id} | Depth: {depth}")
    
    try:
        # Step 1: 온톨로지 로드
        print("[GRAPH] 2. 온톨로지 데이터(strengths.json) 로딩 중...")
        ontology = load_ontology()
        s_map = {s["code"]: s for s in ontology["strengths"]}
        v_map = {v["code"]: v for v in ontology["virtues"]}
        virtue_name_to_code = {v["name"]: v["code"] for v in ontology["virtues"]}
        
        core_codes = [r["code"] for r in top_5]
        
        # Step 2: BFS 탐색 연산
        print("[GRAPH] 3. BFS 그래프 서브셋 탐색 수행 중...")
        nodes_to_add = {}
        edges_to_add = set()
        
        for r in top_5:
            code = r["code"]
            if code in s_map:
                nodes_to_add[code] = {"level": 0, "type": "Strength"}
                v_name = s_map[code].get("virtue_name")
                v_code = virtue_name_to_code.get(v_name)
                
                if v_code:
                    nodes_to_add[v_code] = {"level": 0, "type": "Virtue"}
                    edges_to_add.add((code, v_code, "BELONGS_TO"))

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

        # Step 3: PyVis Network 인스턴스 생성
        print("[GRAPH] 4. PyVis Network 객체 생성 중...")
        net = Network(
            height="550px", 
            width="100%", 
            bgcolor="#ffffff", 
            font_color="#2c3e50",
            cdn_resources="remote"
        )
        
        # Step 4: 세부 렌더링 옵션 제어 (예외 수용형 설계)
        print("[GRAPH] 5. set_options 물리 주입 수행 중...")
        graph_options = {
          "nodes": { "borderWidth": 1.5, "borderWidthSelected": 3 },
          "edges": { "smooth": { "type": "continuous", "forceDirection": "none" } },
          "physics": {
            "barnesHut": { "gravitationalConstant": -6000, "centralGravity": 0.35, "springLength": 95, "springConstant": 0.04 },
            "minVelocity": 0.75
          }
        }
        try:
            net.set_options(json.dumps(graph_options))
        except Exception as opt_err:
            print(f"[GRAPH] ⚠️ [Warning] set_options 무시됨: {opt_err}")

        # Step 5: 노드 수립 및 추가
        print(f"[GRAPH] 6. Network 노드 정의 및 바인딩 중... (총 {len(nodes_to_add)}개)")
        for code, meta in nodes_to_add.items():
            lvl = meta["level"]
            ntype = meta["type"]
            
            node_style = {
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
                    node_style.update({"size": 26, "color": "#2ecc71"})
                elif lvl == 1:
                    node_style.update({"size": 16, "color": "#34495e"})
                elif lvl == 2:
                    node_style.update({"size": 10, "color": "#d1d5db"})
            
            try:
                net.add_node(code, **node_style)
            except Exception as node_err:
                print(f"[GRAPH] ⚠️ [Warning] 노드 주입 실패 ({code}): {node_err}")

        # Step 6: 엣지 수립 및 추가
        print(f"[GRAPH] 7. Network 엣지 관계 정의 중... (총 {len(edges_to_add)}개)")
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
            
            try:
                net.add_edge(**edge_style)
            except Exception as edge_err:
                print(f"[GRAPH] ⚠️ [Warning] 엣지 결합 실패 ({source}->{target}): {edge_err}")

        # Step 7: 임시 물리 디렉토리에 파일 라이팅
        print("[GRAPH] 8. 임시 보관 폴더에 PyVis 물리 디스크 라이팅 중...")
        output_folder = tempfile.gettempdir()
        output_path = os.path.join(output_folder, f"temp_graph_{session_id}.html")
        
        net.save_graph(output_path)
        
        if not os.path.exists(output_path):
            raise RuntimeError(f"물리 HTML 파일 생성이 무시되었거나 실패했습니다: {output_path}")

        # Step 8: HTML 후처리 패치
        print("[GRAPH] 9. HTML 로컬 CDN 주소 맵 변경 및 패치 중...")
        with open(output_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        html_content = html_content.replace(
            'lib/vis-10.1.0/vis-network.min.js',
            'https://unpkg.com/vis-network/standalone/umd/vis-network.min.js'
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print("[GRAPH] 10. 지식 지도 생성 전 과정 정상 완료!")
        print("="*60 + "\n")
        return output_path

    except Exception as fatal_err:
        # 어떠한 최악의 오류가 나더라도 절대로 위로 Exception을 던지지 않고 로그만 남기고 차단합니다.
        print("\n" + "!"*60)
        print("[GRAPH] ❌ [치명적 붕괴] build_pyvis_graph가 비정상적으로 종료되었습니다.")
        traceback.print_exc()
        print("!"*60 + "\n")
        return None