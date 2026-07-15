import os
from neo4j import GraphDatabase

def sync_to_neo4j_safely(email, name, top_5_strengths):
    """
    top_5_strengths: [{"code": "STR_CREATIVITY", "final_score": 4.8}, ...]
    
    AuraDB 혹은 Sandbox 환경 정보를 읽어 비동기 형태의 무중단 그래프 동기화를 시도합니다.
    환경 변수가 없거나 네트워크가 오프라인이어도 예외를 로그에만 남기고 조용히 True/False를 반환합니다.
    """
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    # DB 접속 변수가 한 개라도 없으면 즉시 동기화 패스 (Offline-First 보장)
    if not uri or not password:
        print("[Neo4j Sync Bypass] DB 환경 변수가 감지되지 않아 싱크를 건너뜁니다.")
        return False
        
    # 기존 관계를 제거하고 새로운 가중치로 맵을 갱신하는 멱등성 보장 쿼리
    cypher_query = """
    MERGE (p:Person {email: $email})
    SET p.name = $name
    WITH p
    OPTIONAL MATCH (p)-[r:HAS_STRENGTH]->()
    DELETE r
    WITH p
    UNWIND $strengths AS s_data
    MATCH (s:Strength {code: s_data.code})
    MERGE (p)-[h:HAS_STRENGTH]->(s)
    SET h.score = s_data.final_score
    """
    
    try:
        # 커넥션 맺기 타임아웃을 3초로 짧게 주어 메인 스레드 지연을 철저히 차단합니다.
        with GraphDatabase.driver(uri, auth=(user, password), connection_timeout=3.0) as driver:
            with driver.session() as session:
                session.run(cypher_query, email=email, name=name, strengths=top_5_strengths)
        print(f"[{name} 님] Neo4j 지식지도 동기화 완료")
        return True
    except Exception as e:
        # 사용자단에는 일절 노출시키지 않고 터미널/콘솔에 내부 안전 기록만 남기고 복귀합니다.
        print(f"[Neo4j Sync Bypass] Connection Offline: {e}")
        return False