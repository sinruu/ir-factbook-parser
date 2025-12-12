# IR FactBook Parser

4대 금융지주(우리, KB, 신한, 하나)의 IR FactBook을 정규화된 데이터로 변환하는 파서

## 프로젝트 목표

1. 각 금융지주사의 IR FactBook(Excel)을 파싱
2. 공통 정규화 스키마로 변환
3. 에이전트가 쿼리하기 쉬운 형태로 출력

## Quick Start

```bash
# 설치
pip install -r requirements.txt

# 실행
python src/parser.py --input data/woori_factbook.xlsx --output output/woori_normalized.csv
```

## 디렉토리 구조

```
ir-factbook-parser/
├── README.md
├── requirements.txt
├── config/
│   ├── schema.yaml           # 공통 정규화 스키마
│   ├── woori.yaml            # 우리금융 파싱 규칙
│   ├── kb.yaml               # KB금융 파싱 규칙
│   ├── shinhan.yaml          # 신한금융 파싱 규칙
│   └── hana.yaml             # 하나금융 파싱 규칙
├── src/
│   ├── parser.py             # 메인 파서
│   ├── normalizer.py         # 정규화 변환
│   ├── period_parser.py      # 기간 형식 파서
│   └── validators.py         # 데이터 검증
├── output/
│   └── .gitkeep
└── tests/
    └── test_parser.py
```

## 지원 금융지주사

| 회사 | 파일 패턴 | 시트 수 | 상태 |
|------|----------|--------|------|
| 우리금융 | `*woori*.xlsx` | 25 | ✅ |
| KB금융 | `*KB*Factbook*.xlsx` | 51 | ✅ |
| 신한금융 | `*SFG*FactBook*.xlsx` | 40 | ✅ |
| 하나금융 | `*HFG*Databook*.xlsx` | 24 | ✅ |
