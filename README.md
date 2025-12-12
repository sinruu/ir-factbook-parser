# IR FactBook Parser

4대 금융지주(우리, KB, 신한, 하나)의 IR FactBook을 정규화된 데이터로 변환하는 파서

## 프로젝트 목표

1. 각 금융지주사의 IR FactBook(Excel)을 파싱
2. 공통 정규화 스키마로 변환
3. 관계형 DB 적재 및 LLM 파이프라인 연동에 적합한 형태로 출력

## Quick Start

```bash
# 설치
pip install -r requirements.txt

# 단일 파일 파싱
python -m src.cli parse data/woori_factbook.xlsx -o output/woori.csv

# 여러 파일 일괄 처리
python -m src.cli batch data/*.xlsx -o output/all_normalized.csv

# 데이터 검증만
python -m src.cli validate data/woori_factbook.xlsx

# 지원 정보 확인
python -m src.cli info
```

## 디렉토리 구조

```
ir-factbook-parser/
├── README.md
├── requirements.txt
├── setup.py
├── config/
│   ├── schema.yaml           # 공통 정규화 스키마
│   ├── woori.yaml            # 우리금융 파싱 규칙
│   ├── kb.yaml               # KB금융 파싱 규칙
│   ├── shinhan.yaml          # 신한금융 파싱 규칙
│   └── hana.yaml             # 하나금융 파싱 규칙
├── src/
│   ├── __init__.py
│   ├── parser.py             # 메인 파서
│   ├── normalizer.py         # 정규화 변환
│   ├── period_parser.py      # 기간 형식 파서
│   ├── validators.py         # 데이터 검증
│   └── cli.py                # CLI 인터페이스
├── output/
│   └── .gitkeep
├── data/
│   └── .gitkeep
└── tests/
    ├── __init__.py
    └── test_parser.py
```

## 지원 금융지주사

| 회사 | 파일 패턴 | 시트 수 | 상태 |
|------|----------|--------|------|
| 우리금융 | `*woori*.xlsx` | 25 | ✅ |
| KB금융 | `*KB*Factbook*.xlsx` | 51 | ✅ |
| 신한금융 | `*SFG*FactBook*.xlsx` | 40 | ✅ |
| 하나금융 | `*HFG*Databook*.xlsx` | 24 | ✅ |

## 출력 스키마

```csv
holding_company,entity,category,metric_std,metric_original,period,year,quarter,value,unit,is_cumulative,is_estimate
우리금융지주,지주,Asset Quality,npl_ratio,NPL Ratio,2024-Q3,2024,3,0.0069,percent,false,false
KB금융지주,지주,Income Statement,net_income,Net Income,2024-Q3,2024,3,1655.2,KRW_billion,false,false
```

### 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| holding_company | string | 금융지주사명 |
| entity | string | 법인/자회사 (지주, 은행, 카드, 증권 등) |
| category | string | 지표 대분류 |
| metric_std | string | 표준화된 지표명 (영문 snake_case) |
| metric_original | string | 원본 지표명 |
| period | string | 기간 (YYYY-QN 형식) |
| year | int | 연도 |
| quarter | int | 분기 (1-4, null이면 연간) |
| value | float | 수치 값 |
| unit | string | 단위 (KRW_billion, percent, bps 등) |
| is_cumulative | boolean | 누적 여부 |
| is_estimate | boolean | 추정치 여부 |

## Python API 사용법

```python
from src.parser import parse_factbook, export_to_csv, export_to_json
from src.validators import validate_records

# 파싱
records = parse_factbook("data/woori_factbook.xlsx")

# 검증
report = validate_records(records)
print(f"총 {report.total_records}개 레코드, {report.error_count}개 오류")

# 내보내기
export_to_csv(records, "output/normalized.csv")
export_to_json(records, "output/normalized.json")
```

## DB 적재 예시

```python
import pandas as pd
from sqlalchemy import create_engine
from src.parser import parse_factbook

# 파싱
records = parse_factbook("data/woori_factbook.xlsx")

# DataFrame 변환
df = pd.DataFrame([r.to_dict() for r in records])

# DB 적재
engine = create_engine("postgresql://user:pass@localhost/factbook")
df.to_sql("financial_metrics", engine, if_exists="append", index=False)
```

## 테스트

```bash
# 테스트 실행
pytest tests/ -v

# 커버리지 포함
pytest tests/ --cov=src --cov-report=html
```

## 주요 고려사항

### 신한금융 특이사항
- IFRS-17 이중 컬럼: 2022년부터 IFRS-17 적용 전/후 데이터가 병존
- 누적 데이터: IS 데이터가 분기가 아닌 누적 형태 (1Q, 1H, 3Q, FY)

### KB금융 특이사항
- 시트 수 최다 (51개): 가장 상세한 자회사별 데이터
- 날짜 형식 혼재: `3Q24` (분기) + `Sep. 24` (월별)

### 우리/하나 유사성
- 기간 형식 동일: `FY2024 3Q`
- 시트 구조 유사: 파싱 로직 공유 가능

## 라이선스

MIT License
