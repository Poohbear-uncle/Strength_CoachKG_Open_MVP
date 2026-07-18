# core/graph_visual.py
import os
import json
import tempfile
from pyvis.network import Network
from core.assessment import load_ontology

def build_pyvis_graph(session_id, top_5, depth=1):
    """
    사용자의 상위 5대 강점을 기반으로 온톨로지 관계망 지도를 빌드하여 HTML 파일 경로를 반환합니다.
    모든 모듈에 예외 안전장치를 적용하여 에러가 발생해도 전체 렌더링이 중단되지 않도록 보호합니다.
    """
    print(f"\n[DEBUG_GRAPH] ===============================================")
    print(f"[DEBUG_GRAPH] 🧭 [1단계] build_pyvis_graph 진입 (Session: {session_id})")
    
    output_folder = tempfile.gettempdir()
    output_path = os.path.join(output_folder, f"temp_graph_{session_id}.html")
    
    try:
        # 1. 온톨로지 파일 로드 검증
        print(f"[DEBUG_GRAPH] 🧭 [2단계] 온톨로지 데이터 로드 중...")
        ontology = load_ontology()
        s_map = {s["code"]: s for s in ontology["strengths"]}
        v_map = {v["code"]: v for v in ontology["virtues"]}
        virtue_name_to_code = {v["name"]: v["code"] for v in ontology["virtues"]}
        
        core_codes = [r["code"] for r in top_5]
        
        # 2. 너비 우선 탐색 (BFS) 연산
        print(f"[DEBUG_GRAPH] 🧭 [3단계] 관계망 BFS 연산 수행 중...")
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

        # 3. PyVis Network 객체 생성
        print(f"[DEBUG_GRAPH] 🧭 [4단계] PyVis Network 초기화 중...")
        net = Network(
            height="550px", 
            width="100%", 
            bgcolor="#ffffff", 
            font_color="#2c3e50",
            cdn_resources="remote"
        )
        
        # 4. 물리엔진 정합성 설정 (버전 호환용 예외 처리 탑재)
        print(f"[DEBUG_GRAPH] 🧭 [5단계] 물리엔진 옵션 주입 중...")
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
            # set_options가 버전에 따라 실패하더라도 그래프 생성은 중단되지 않도록 폴백
            print(f"[DEBUG_GRAPH] ⚠️ 경고: set_options 설정 중 예외가 발생했으나 기본 스타일로 속행합니다. ({opt_err})")

        # 5. 수집된 노드 주입
        print(f"[DEBUG_GRAPH] 🧭 [6단계] 노드 주입 중... (총 {len(nodes_to_add)}개)")
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
                # n_id를 명시적으로 파라미터 분리하여 버전 호환성 완벽 확보
                net.add_node(code, **node_style)
            except Exception as node_err:
                print(f"[DEBUG_GRAPH] ⚠️ 경고: 노드 [{code}] 주입 실패: {node_err}")

        # 6. 수집된 엣지 주입
        print(f"[DEBUG_GRAPH] 🧭 [7단계] 엣지 주입 중... (총 {len(edges_to_add)}개)")
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
                print(f"[DEBUG_GRAPH] ⚠️ 경고: 엣지 [{source} -> {target}] 주입 실패: {edge_err}")

        # 7. 파일 저장 (임시 디렉토리 보안 및 호환성 확보)
        print(f"[DEBUG_GRAPH] 🧭 [8단계] 임시 파일 보관소 저장 중... ({output_path})")
        net.save_graph(output_path)

        # 8. HTML 템플릿의 로컬 상대 참조 복구
        print(f"[DEBUG_GRAPH] 🧭 [9단계] HTML 내 로컬 의존성 복구 및 보정 중...")
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 버그 유발 요인이었던 utils.js 교체 코드를 안전하게 격리 제거했습니다.
            html_content = html_content.replace(
                'lib/vis-10.1.0/vis-network.min.js',
                'https://unpkg.com/vis-network/standalone/umd/vis-network.min.js'
            )
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        print(f"[DEBUG_GRAPH] 🪐 [성공] build_pyvis_graph가 아무 사고 없이 최종 완료되었습니다.\n")
        return output_path

    except Exception as fatal_error:
        # 치명적인 에러가 나서 빌드가 완전히 붕괴되었을 때의 방어막 폴백
        print(f"[DEBUG_GRAPH] ❌ 치명적 붕괴 감지: {fatal_error}")
        print(f"[DEBUG_GRAPH] 🛡️ [방어 조치] 사용자 화면 보호용 임시 안전 HTML을 대체 생성합니다.")
        
        try:
            fallback_html = f"""
            <html>
            <body style="font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; color: #7f8c8d; background-color: #f8f9fa;">
                <div style="text-align: center; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: white;">
                    <p style="font-size: 32px; margin: 0;">🧭</p>
                    <h3 style="color: #2c3e50; margin: 10px 0;">관계 지도 생성 일시 지연</h3>
                    <p style="font-size: 13px; line-height: 1.5;">현재 사용하시는 환경의 웹 라이브러리(PyVis) 로드 과정에서 충돌이 감지되었습니다.<br>
                    우측의 <b>상세 역동성 해석 정보</b> 및 하단의 <b>PDF 보고서</b> 기능은 정상 확인하실 수 있습니다.</p>
                    <p style="font-size: 10px; color: #cbd5e1; margin-top: 15px;">Error: {str(fatal_error)}</p>
                </div>
            </body>
            </html>
            """
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(fallback_html)
            return output_path
        except Exception as file_err:
            print(f"[DEBUG_GRAPH] 🚨 폴백 파일 생성조차 실패: {file_err}")
            return None