# core/graph_visual.py
import os
import json
import tempfile
import traceback
from core.assessment import load_ontology

def build_pyvis_graph(session_id, top_5, depth=1):
    """
    파이썬 네이티브 데이터(JSON)와 cdnjs의 초고속 CDN을 결합하여 지도를 그립니다.
    브라우저 콘솔(F12)에서 실행 상태를 실시간 추적할 수 있도록 자체 로깅 코드가 내장되어 있습니다.
    """
    print("\n" + "="*60)
    print("[GRAPH-NATIVE] 1. 커스텀 지형도 엔진 기동 시작")
    print(f"[GRAPH-NATIVE] 세션 식별자: {session_id} | 탐색 깊이: {depth}")
    
    try:
        # 1. 데이터 온톨로지 정합성 로딩
        print("[GRAPH-NATIVE] 2. 온톨로지 파일 로드 중...")
        ontology = load_ontology()
        s_map = {s["code"]: s for s in ontology["strengths"]}
        v_map = {v["code"]: v for v in ontology["virtues"]}
        virtue_name_to_code = {v["name"]: v["code"] for v in ontology["virtues"]}
        
        core_codes = [r["code"] for r in top_5]
        
        # 2. 관계망 BFS 연산
        print("[GRAPH-NATIVE] 3. 지형 네트워크 관계망 BFS 연산 중...")
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

        # 3. 노드 스타일링 매핑
        print("[GRAPH-NATIVE] 4. 노드 데이터 스타일링 매핑 중...")
        nodes_data = []
        for code, meta in nodes_to_add.items():
            lvl = meta["level"]
            ntype = meta["type"]
            
            node_style = {
                "id": code,
                "label": code,
                "size": 15,
                "color": "#bdc3c7",
                "shape": "dot",
                "font": {"size": 12, "color": "#2c3e50"}
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
            nodes_data.append(node_style)

        # 4. 엣지 스타일링 매핑
        print("[GRAPH-NATIVE] 5. 엣지 데이터 스타일링 매핑 중...")
        edges_data = []
        for source, target, rel_type in edges_to_add:
            edge_style = {
                "from": source,
                "to": target,
                "width": 1.2,
                "color": {"color": "#bdc3c7", "highlight": "#95a5a6"}
            }
            if rel_type == "BELONGS_TO":
                edge_style.update({"width": 0.8, "color": {"color": "#e2e8f0"}})
            elif rel_type == "SYNERGY_WITH":
                edge_style.update({"width": 1.8, "color": {"color": "#2ecc71"}})
            elif rel_type == "BALANCES":
                edge_style.update({"width": 1.5, "color": {"color": "#e67e22"}, "dashes": True})
            elif rel_type == "CONFLICTS_WITH":
                edge_style.update({"width": 1.5, "color": {"color": "#e74c3c"}, "dashes": [2, 8]})
            edges_data.append(edge_style)

        graph_options = {
          "nodes": { "borderWidth": 1.5, "borderWidthSelected": 3, "font": { "multi": True } },
          "edges": { "smooth": { "type": "continuous", "forceDirection": "none" } },
          "physics": {
            "barnesHut": { "gravitationalConstant": -6000, "centralGravity": 0.35, "springLength": 95, "springConstant": 0.04 },
            "minVelocity": 0.75
          }
        }

        # 5. 무결성 HTML 템플릿 컴파일 및 브라우저 디버깅 추적 코드 내장
        print("[GRAPH-NATIVE] 6. 무결성 가상 HTML 컴파일 및 JS 진단 기능 주입 중...")
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>CoachKG Network Graph</title>
            <!-- unpkg의 보안 장벽을 우회하기 위해 가장 신뢰성이 높은 Cloudflare cdnjs 절대 경로 라이브러리 사용 -->
            <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/standalone/umd/vis-network.min.js"></script>
            <style type="text/css">
                #mynetwork {{
                    width: 100%;
                    height: 550px;
                    border: none;
                    background-color: #ffffff;
                }}
                body {{
                    margin: 0;
                    padding: 0;
                    background-color: #ffffff;
                    overflow: hidden;
                }}
            </style>
        </head>
        <body>
        <div id="mynetwork"></div>
        <script type="text/javascript">
            console.log("[GRAPH-JS] 🪐 자바스크립트 엔진 기동을 시작합니다.");
            
            try {{
                var rawNodes = {json.dumps(nodes_data, ensure_ascii=False)};
                var rawEdges = {json.dumps(edges_data, ensure_ascii=False)};
                
                console.log("[GRAPH-JS] 전달된 노드 데이터 개수: " + rawNodes.length);
                console.log("[GRAPH-JS] 전달된 엣지 데이터 개수: " + rawEdges.length);
                
                var nodes = new vis.DataSet(rawNodes);
                var edges = new vis.DataSet(rawEdges);
                var container = document.getElementById('mynetwork');
                
                var data = {{
                    nodes: nodes,
                    edges: edges
                }};
                
                var options = {json.dumps(graph_options, ensure_ascii=False)};
                
                console.log("[GRAPH-JS] vis.Network 인스턴스 생성을 시도합니다...");
                var network = new vis.Network(container, data, options);
                console.log("[GRAPH-JS] ✅ 지도가 브라우저 화면에 성공적으로 안착했습니다!");
                
            }} catch (js_err) {{
                console.error("[GRAPH-JS] ❌ 지도를 그리는 도중 내부 런타임 에러가 감지되었습니다: ", js_err);
            }}
        </script>
        </body>
        </html>
        """

        # 6. 디렉토리 표준 보관소 저장
        output_folder = tempfile.gettempdir()
        output_path = os.path.join(output_folder, f"temp_graph_{session_id}.html")
        
        print(f"[GRAPH-NATIVE] 7. 디스크 파일 쓰기 시작 ({output_path})")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
            
        print("[GRAPH-NATIVE] 🪐 [성공] 무결성 지형망 및 진단 모듈 컴파일 완료!")
        print("="*60 + "\n")
        return output_path

    except Exception as e:
        print("\n" + "!"*60)
        print(f"[GRAPH-NATIVE] ❌ 엔진 내부 치명적 크래시 발생: {e}")
        traceback.print_exc()
        print("!"*60 + "\n")
        return None