"""
LLM 연동 모듈 (Ollama)

자연어 질문을 SQL로 변환하고 DuckDB에서 실행
"""

import json
import requests
import duckdb
from pathlib import Path
from typing import Optional


# NL→SQL 시스템 프롬프트
SYSTEM_PROMPT = """You are a SQL query generator for a financial metrics database. Convert Korean natural language questions into DuckDB SQL queries.

## Database Schema

```sql
CREATE TABLE financial_metrics (
    holding_company VARCHAR,   -- 금융지주사: "KB금융지주", "신한금융지주", "하나금융지주", "우리금융지주"
    entity VARCHAR,            -- 법인: "지주", "은행", "카드", "증권"
    category VARCHAR,          -- 분류: "Income Statement", "Balance Sheet", "Asset Quality" 등
    metric_std VARCHAR,        -- 표준지표명 (영문 snake_case)
    metric_original VARCHAR,   -- 원본지표명
    period VARCHAR,            -- 기간: "2024-Q3" (분기), "2024-FY" (연간)
    year INTEGER,              -- 연도
    quarter INTEGER,           -- 분기 (1-4, NULL=연간)
    value DOUBLE,              -- 수치값
    unit VARCHAR,              -- 단위: "KRW_billion", "percent"
    is_cumulative BOOLEAN,     -- 누적여부
    is_estimate BOOLEAN        -- 추정치여부
);
```

## Key Metrics (metric_std)
- net_income: 당기순이익 (KRW_billion)
- total_assets: 총자산 (KRW_billion)
- npl_ratio: NPL비율 (percent, 값이 0.01이면 1%)
- nim: 순이자마진 NIM (percent)
- bis_ratio: BIS비율 (percent)
- roe: 자기자본이익률 (percent)

## Company Names
- KB금융지주 (KB, 국민)
- 신한금융지주 (신한)
- 하나금융지주 (하나)
- 우리금융지주 (우리)

## Rules
1. Default entity = '지주' unless asking about bank/card
2. Use GROUP BY with MAX() to avoid duplicates
3. For percent values, multiply by 100 for display
4. Return ONLY the SQL query, no explanation
5. Use Korean company names exactly as shown above

## Examples

Q: KB금융 2024년 3분기 순이익
```sql
SELECT holding_company, period, value as net_income_bn
FROM financial_metrics
WHERE holding_company = 'KB금융지주' AND metric_std = 'net_income' AND period = '2024-Q3' AND entity = '지주';
```

Q: 4대 금융지주 총자산 비교
```sql
SELECT holding_company, MAX(value) as total_assets_bn
FROM financial_metrics
WHERE metric_std IN ('total_assets', 'total_assets_excl_trust_asset') AND period = '2024-Q3' AND entity = '지주'
GROUP BY holding_company
ORDER BY total_assets_bn DESC;
```

Q: 신한금융 NIM 추이
```sql
SELECT period, value * 100 as nim_pct
FROM financial_metrics
WHERE holding_company = '신한금융지주' AND metric_std = 'nim' AND entity = '은행' AND year >= 2023
ORDER BY year, quarter;
```
"""


class FinancialAssistant:
    """금융 데이터 LLM 어시스턴트"""

    def __init__(
        self,
        db_path: str = "ir_factbook.duckdb",
        model: str = "qwen2.5:7b",
        ollama_url: str = "http://localhost:11434"
    ):
        self.db_path = db_path
        self.model = model
        self.ollama_url = ollama_url
        self.conn = duckdb.connect(db_path, read_only=True)

    def generate_sql(self, question: str) -> str:
        """자연어 질문을 SQL로 변환"""
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": self.model,
                "prompt": f"{SYSTEM_PROMPT}\n\nQ: {question}\nSQL:",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 500
                }
            }
        )

        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.text}")

        result = response.json()["response"]

        # 디버그 출력
        # print(f"[DEBUG] Raw response: {result[:200]}...")

        # SQL 추출
        sql = result.strip()

        # ```sql ... ``` 블록에서 추출
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0]
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0] if sql.count("```") >= 2 else sql.split("```")[0]

        sql = sql.strip()

        # SELECT 문 찾기
        if not sql.upper().startswith("SELECT"):
            lines = sql.split("\n")
            for i, line in enumerate(lines):
                if line.strip().upper().startswith("SELECT"):
                    # SELECT부터 끝까지 합치기
                    sql = "\n".join(lines[i:])
                    # 세미콜론에서 자르기
                    if ";" in sql:
                        sql = sql.split(";")[0] + ";"
                    break

        return sql.strip()

    def execute_query(self, sql: str):
        """SQL 실행"""
        if not sql or not sql.strip():
            return "Error: SQL이 생성되지 않았습니다"
        try:
            return self.conn.execute(sql).fetchdf()
        except Exception as e:
            return f"Error: {e}"

    def ask(self, question: str) -> dict:
        """질문에 답변"""
        print(f"\n🔍 질문: {question}")

        # SQL 생성
        print("⏳ SQL 생성 중...")
        sql = self.generate_sql(question)
        print(f"📝 SQL:\n{sql}\n")

        # 실행
        print("⏳ 쿼리 실행 중...")
        result = self.execute_query(sql)

        if isinstance(result, str) and result.startswith("Error"):
            print(f"❌ {result}")
        else:
            print(f"✅ 결과:\n{result}")

        return {"question": question, "sql": sql, "result": result}

    def chat(self):
        """대화형 모드"""
        print("=" * 50)
        print("💬 금융 데이터 어시스턴트")
        print("=" * 50)
        print("자연어로 질문하세요. 종료하려면 'exit' 입력\n")

        while True:
            try:
                question = input("👤 질문: ").strip()
                if question.lower() in ("exit", "quit", "종료"):
                    print("👋 종료합니다.")
                    break
                if not question:
                    continue

                self.ask(question)
                print()

            except KeyboardInterrupt:
                print("\n👋 종료합니다.")
                break

    def close(self):
        """연결 종료"""
        self.conn.close()


def main():
    """CLI 엔트리포인트"""
    import sys

    db_path = "ir_factbook.duckdb"
    model = "qwen2.5:7b"

    # 인자 처리
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("Usage: python llm_query.py [question]")
            print("       python llm_query.py  # 대화형 모드")
            return
        question = " ".join(sys.argv[1:])
    else:
        question = None

    # 어시스턴트 초기화
    assistant = FinancialAssistant(db_path=db_path, model=model)

    try:
        if question:
            assistant.ask(question)
        else:
            assistant.chat()
    finally:
        assistant.close()


if __name__ == "__main__":
    main()
