"""
DuckDB 데이터 적재 모듈

정규화된 FactBook 데이터를 DuckDB에 적재하고 쿼리
"""

import duckdb
from pathlib import Path
from typing import Optional, List, Dict, Any


class FactBookDB:
    """FactBook DuckDB 데이터베이스"""

    def __init__(self, db_path: str = "factbook.duckdb"):
        """
        Args:
            db_path: DuckDB 파일 경로 (":memory:"면 인메모리)
        """
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        """테이블 스키마 초기화"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS financial_metrics (
                id INTEGER PRIMARY KEY,
                holding_company VARCHAR NOT NULL,
                entity VARCHAR,
                category VARCHAR,
                metric_std VARCHAR NOT NULL,
                metric_original VARCHAR,
                period VARCHAR NOT NULL,
                year INTEGER NOT NULL,
                quarter INTEGER,
                value DOUBLE,
                unit VARCHAR,
                is_cumulative BOOLEAN DEFAULT FALSE,
                is_estimate BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 인덱스 생성
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_company
            ON financial_metrics(holding_company)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_metric
            ON financial_metrics(metric_std)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_period
            ON financial_metrics(period)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_year_quarter
            ON financial_metrics(year, quarter)
        """)

    def load_csv(self, csv_path: str, replace: bool = False):
        """
        CSV 파일에서 데이터 로드

        Args:
            csv_path: CSV 파일 경로
            replace: True면 기존 데이터 삭제 후 로드
        """
        if replace:
            self.conn.execute("DELETE FROM financial_metrics")

        # DuckDB는 CSV를 직접 읽을 수 있음
        self.conn.execute(f"""
            INSERT INTO financial_metrics (
                holding_company, entity, category, metric_std,
                metric_original, period, year, quarter, value,
                unit, is_cumulative, is_estimate
            )
            SELECT
                holding_company, entity, category, metric_std,
                metric_original, period, year, quarter, value,
                unit, is_cumulative, is_estimate
            FROM read_csv_auto('{csv_path}')
        """)

        count = self.conn.execute(
            "SELECT COUNT(*) FROM financial_metrics"
        ).fetchone()[0]
        print(f"✓ {count:,}개 레코드 로드 완료")

    def query(self, sql: str) -> List[Dict[str, Any]]:
        """SQL 쿼리 실행"""
        result = self.conn.execute(sql).fetchdf()
        return result.to_dict('records')

    def get_companies(self) -> List[str]:
        """금융지주사 목록"""
        result = self.conn.execute("""
            SELECT DISTINCT holding_company
            FROM financial_metrics
            ORDER BY holding_company
        """).fetchall()
        return [r[0] for r in result]

    def get_metrics(self) -> List[str]:
        """지표 목록"""
        result = self.conn.execute("""
            SELECT DISTINCT metric_std
            FROM financial_metrics
            ORDER BY metric_std
        """).fetchall()
        return [r[0] for r in result]

    def get_metric_by_company(
        self,
        metric: str,
        company: Optional[str] = None,
        start_year: int = 2020,
        entity: str = "지주"
    ):
        """
        특정 지표 조회

        Args:
            metric: 지표명 (예: "total_assets", "npl_ratio")
            company: 금융지주사 (None이면 전체)
            start_year: 시작 연도
            entity: 엔티티 (지주, 은행 등)
        """
        sql = f"""
            SELECT
                holding_company,
                period,
                year,
                quarter,
                value,
                unit
            FROM financial_metrics
            WHERE metric_std = '{metric}'
              AND entity = '{entity}'
              AND year >= {start_year}
              AND is_estimate = FALSE
        """
        if company:
            sql += f" AND holding_company = '{company}'"
        sql += " ORDER BY holding_company, year, quarter"

        return self.conn.execute(sql).fetchdf()

    def compare_companies(
        self,
        metric: str,
        period: str,
        entity: str = "지주"
    ):
        """
        특정 기간의 회사별 지표 비교

        Args:
            metric: 지표명
            period: 기간 (예: "2024-Q3")
            entity: 엔티티
        """
        sql = f"""
            SELECT
                holding_company,
                metric_original,
                value,
                unit
            FROM financial_metrics
            WHERE metric_std = '{metric}'
              AND period = '{period}'
              AND entity = '{entity}'
            ORDER BY value DESC
        """
        return self.conn.execute(sql).fetchdf()

    def get_latest_period(self) -> str:
        """최신 기간 조회"""
        result = self.conn.execute("""
            SELECT period
            FROM financial_metrics
            WHERE is_estimate = FALSE
            ORDER BY year DESC, quarter DESC NULLS LAST
            LIMIT 1
        """).fetchone()
        return result[0] if result else None

    def summary(self):
        """데이터 요약 출력"""
        stats = self.conn.execute("""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT holding_company) as companies,
                COUNT(DISTINCT metric_std) as metrics,
                COUNT(DISTINCT period) as periods,
                MIN(year) as min_year,
                MAX(year) as max_year
            FROM financial_metrics
        """).fetchone()

        print(f"""
╭──────────────────────────────────────╮
│       FactBook DB 요약               │
├──────────────────────────────────────┤
│  총 레코드: {stats[0]:>15,}개        │
│  금융지주사: {stats[1]:>14}개        │
│  지표 수: {stats[2]:>17}개           │
│  기간 수: {stats[3]:>17}개           │
│  데이터 범위: {stats[4]} ~ {stats[5]}         │
╰──────────────────────────────────────╯
        """)

    def close(self):
        """연결 종료"""
        self.conn.close()


def load_to_duckdb(
    csv_path: str,
    db_path: str = "factbook.duckdb",
    replace: bool = True
) -> FactBookDB:
    """
    CSV를 DuckDB에 로드 (편의 함수)

    Args:
        csv_path: CSV 파일 경로
        db_path: DuckDB 파일 경로
        replace: 기존 데이터 교체 여부

    Returns:
        FactBookDB 인스턴스
    """
    db = FactBookDB(db_path)
    db.load_csv(csv_path, replace=replace)
    return db


# CLI로 직접 실행 시
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python db_loader.py <csv_file> [db_file]")
        print("Example: python db_loader.py output/all_normalized.csv factbook.duckdb")
        sys.exit(1)

    csv_file = sys.argv[1]
    db_file = sys.argv[2] if len(sys.argv) > 2 else "factbook.duckdb"

    print(f"CSV: {csv_file}")
    print(f"DB: {db_file}")
    print()

    db = load_to_duckdb(csv_file, db_file)
    db.summary()

    # 샘플 쿼리
    print("\n[샘플] 최신 분기 총자산 비교:")
    latest = db.get_latest_period()
    if latest:
        result = db.compare_companies("total_assets", latest)
        print(result.to_string())

    db.close()
    print(f"\n✓ DB 저장 완료: {db_file}")
