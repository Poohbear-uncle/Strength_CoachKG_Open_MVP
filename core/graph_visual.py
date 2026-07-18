# core/graph_visual.py
import os
import tempfile
import traceback
import matplotlib
matplotlib.use('Agg')  # 가상 GUI 서버가 없는 환경을 위한 강제 설정
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D
import networkx as nx
from core.assessment import load_ontology

def build_pyvis_graph(session_id, top_5, depth=1):
    """
    [최종 근본적 해결책] 브라우저의 Sandbox 및 자바스크립트 보안 차단을 우회하기 위해,
    서버사이드에서 Matplotlib과 NetworkX로 고품격 지도를 즉시 드로잉하여 
    보안에 저항 없는 초고해상도 PNG 이미지 경로를 반환합니다.
    """
    print(f"\n[GRAPH-STATIC] 🪐 서버사이드 고화질 지형망 드로잉 개시 (Depth: {depth})")
    
    try:
        # 1. 온톨로지 마스터 정보 및 폰트 획득
        ontology = load_ontology()
        s_map = {s["code"]: s for s in ontology["strengths"]}
        v_map = {v["code"]: v for v in ontology["virtues"]}
        virtue_name_to_code = {v["name"]: v["code"] for v in ontology["virtues"]}
        
        core_codes = [r["code"] for r in top_5]
        
        # 2. NetworkX 그래프 인스턴스 설계 및 BFS 탐색
        G = nx.Graph()
        node_colors = []
        node_labels = {}
        nodes_to_add = {}
        edges_to_add = set()
        
        # [Level 0] 핵심 5대 강점 및 대덕목
        for r in top_5:
            code = r["code"]
            if code in s_map:
                nodes_to_add[code] = {"level": 0, "type": "Strength"}
                v_name = s_map[code].get("virtue_name")
                v_code = virtue_name_to_code.get(v_name)
                
                if v_code:
                    nodes_to_add[v_code] = {"level": 0, "type": "Virtue"}
                    edges_to_add.add((code, v_code, "BELONGS_TO"))

        # [Level 1 & 2] 탐색 깊이에 따른 연계 강점 확장
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

        # G 노드 주입 및 색상 정보 바인딩
        for code, meta in nodes_to_add.items():
            G.add_node(code)
            if meta["type"] == "Virtue":
                node_colors.append('#9b5de5')  # Amethyst 보라 (대덕목)
                node_labels[code] = v_map.get(code, {}).get("name", code)
            else:
                lvl = meta["level"]
                node_labels[code] = s_map.get(code, {}).get("name", code)
                if lvl == 0:
                    node_colors.append('#2ecc71')  # Emerald 초록 (핵심 5대)
                elif lvl == 1:
                    node_colors.append('#dfe6e9')  # Slate 이웃 (1차 연계)
                else:
                    node_colors.append('#f1f2f6')  # Cloud 연회색 (2차 간접 연계)

        # G 엣지 주입 및 관계선 스타일 바인딩
        for source, target, rel_type in edges_to_add:
            color = '#bdc3c7'
            style = 'solid'
            if rel_type == "BELONGS_TO":
                color = '#e2e8f0'
            elif rel_type == "SYNERGY_WITH":
                color = '#2ecc71'
            elif rel_type == "BALANCES":
                color = '#e67e22'
                style = 'dashed'
            elif rel_type == "CONFLICTS_WITH":
                color = '#e74c3c'
                style = 'dotted'
            G.add_edge(source, target, color=color, style=style)

        # 3. 한글 나눔고딕 물리 폰트 안정 확보
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        FONT_BOLD_PATH = os.path.join(project_root, "data", "fonts", "NanumGothic-Bold.ttf")
        SYSTEM_FONT_BOLD = "/usr/share/fonts/truetype/nanum/NanumGothic-Bold.ttf"
        
        font_path = None
        if os.path.exists(SYSTEM_FONT_BOLD):
            font_path = SYSTEM_FONT_BOLD
        elif os.path.exists(FONT_BOLD_PATH):
            font_path = FONT_BOLD_PATH
            
        if font_path:
            font_prop_node = fm.FontProperties(fname=font_path, size=7.5)
            font_prop_title = fm.FontProperties(fname=font_path, size=11)
        else:
            font_prop_node = fm.FontProperties(family="sans-serif", size=7.5)
            font_prop_title = fm.FontProperties(family="sans-serif", size=11)

        # 4. Matplotlib 기반 초고화질 드로잉 프로세스
        fig = plt.figure(figsize=(7.5, 7.5), dpi=300)
        plt.rcParams['axes.unicode_minus'] = False
        
        # 선의 겹침을 최소화하는 수학적 Kamada-Kawai 레이아웃 실행
        pos = nx.kamada_kawai_layout(G)
        
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=600)
        
        # 텍스트 노드 매핑
        for node, (x, y) in pos.items():
            if node in node_labels:
                plt.text(
                    x, y, 
                    node_labels[node], 
                    fontproperties=font_prop_node, 
                    ha='center', 
                    va='center',
                    zorder=10
                )
                
        # 엣지 렌더링
        edges = G.edges(data=True)
        for u, v, d in edges:
            color = d.get('color', '#bdc3c7')
            style = d.get('style', 'solid')
            nx.draw_networkx_edges(
                G, pos, 
                edgelist=[(u, v)], 
                edge_color=color, 
                style=style, 
                width=1.3
            )
            
        plt.title("CoachKG 강점 시너제틱 지형망", fontproperties=font_prop_title, pad=15)
        plt.axis('off')
        
        # 고품격 범례 레이어 주입
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#2ecc71', markersize=8, label='대표 강점 (Group A)'),
            Line2D([0], [0], marker='^', color='w', markerfacecolor='#9b5de5', markersize=8, label='상위 대덕목 (Virtues)'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#dfe6e9', markersize=8, label='1차 이웃 강점'),
            Line2D([0], [0], color='#2ecc71', lw=1.5, label='시너지 효과 (Synergy)'),
            Line2D([0], [0], color='#e67e22', lw=1.5, linestyle='--', label='상호보완 균형 (Balances)'),
            Line2D([0], [0], color='#e74c3c', lw=1.5, linestyle=':', label='주의필요 상충 (Conflicts)')
        ]
        
        if depth == 2:
            legend_elements.insert(3, Line2D([0], [0], marker='o', color='w', markerfacecolor='#f1f2f6', markersize=8, label='2차 간접 강점'))
            
        plt.legend(handles=legend_elements, loc='lower center', ncol=2, prop=font_prop_node, bbox_to_anchor=(0.5, -0.12))
        plt.tight_layout()
        
        # 고화질 이미지 디렉토리 저장
        temp_img_name = f"temp_mat_web_{session_id}.png"
        temp_img_path = os.path.join(tempfile.gettempdir(), temp_img_name)
        plt.savefig(temp_img_path, format="png", bbox_inches='tight')
        plt.close()
        
        print(f"[GRAPH-STATIC] 🪐 [성공] 서버사이드 지형망 렌더링 무결 완료! (경로: {temp_img_path})")
        return temp_img_path
        
    except Exception as e:
        print(f"[GRAPH-STATIC] ❌ 서버사이드 렌더링 과정에서 예외 감지: {e}")
        traceback.print_exc()
        return None