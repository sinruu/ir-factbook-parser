# Financial Metrics Database Schema

## 테이블: `financial_metrics`

4대 금융지주(우리, KB, 신한, 하나)의 IR FactBook에서 추출한 정규화된 재무 데이터

### 컬럼 정의

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `holding_company` | VARCHAR | 금융지주사명 | "KB금융지주", "우리금융지주" |
| `entity` | VARCHAR | 법인/사업부문 | "지주", "은행", "카드", "증권" |
| `category` | VARCHAR | 지표 대분류 | "Income Statement", "Balance Sheet" |
| `metric_std` | VARCHAR | 표준화된 지표명 (영문) | "total_assets", "npl_ratio" |
| `metric_original` | VARCHAR | 원본 지표명 | "Total Assets", "NPL Ratio" |
| `period` | VARCHAR | 기간 (YYYY-QN 형식) | "2024-Q3", "2024-FY" |
| `year` | INTEGER | 연도 | 2024 |
| `quarter` | INTEGER | 분기 (1-4, NULL=연간) | 3 |
| `value` | DOUBLE | 수치 값 | 500000.0 |
| `unit` | VARCHAR | 단위 | "KRW_billion", "percent" |
| `is_cumulative` | BOOLEAN | 누적 데이터 여부 | FALSE |
| `is_estimate` | BOOLEAN | 추정치 여부 | FALSE |

---

## 금융지주사 (holding_company)

| 값 | 설명 |
|----|------|
| KB금융지주 | KB Financial Group |
| 신한금융지주 | Shinhan Financial Group |
| 하나금융지주 | Hana Financial Group |
| 우리금융지주 | Woori Financial Group |

---

## 법인/사업부문 (entity)

| 값 | 설명 |
|----|------|
| 지주 | 금융지주 연결 기준 |
| 은행 | 은행 부문 (KB국민은행, 신한은행 등) |
| 카드 | 카드 부문 |
| 증권 | 증권 부문 |
| 생명보험 | 생명보험 부문 |
| 손해보험 | 손해보험 부문 |
| 캐피탈 | 캐피탈/리스 부문 |

---

## 지표 대분류 (category)

| 값 | 설명 |
|----|------|
| Financial Highlights | 주요 재무지표 요약 |
| Income Statement | 손익계산서 |
| Balance Sheet | 재무상태표 |
| Interest Income | 이자이익 관련 |
| Non-Interest Income | 비이자이익 관련 |
| Asset Quality | 자산건전성 |
| Capital Adequacy | 자본적정성 |
| Loans | 여신/대출 |
| Deposits | 수신/예금 |
| Provision | 충당금/대손 |
| Delinquency | 연체 |
| G&A Expense | 판관비 |

---

## 주요 표준 지표 (metric_std)

### 수익성 지표
| 지표명 | 설명 | 단위 |
|--------|------|------|
| net_income | 당기순이익 | KRW_billion |
| net_income_controlling | 지배주주순이익 | KRW_billion |
| roe | 자기자본이익률 | percent |
| roa | 총자산이익률 | percent |

### 규모 지표
| 지표명 | 설명 | 단위 |
|--------|------|------|
| total_assets | 총자산 | KRW_billion |
| total_equity | 자기자본 | KRW_billion |
| total_loans | 총여신 | KRW_billion |

### 이자이익 지표
| 지표명 | 설명 | 단위 |
|--------|------|------|
| net_interest_income | 순이자이익 | KRW_billion |
| nim | 순이자마진 (NIM) | percent |
| nis | 순이자스프레드 (NIS) | percent |

### 자산건전성 지표
| 지표명 | 설명 | 단위 |
|--------|------|------|
| npl | 고정이하여신 (NPL) | KRW_billion |
| npl_ratio | NPL비율 | percent |
| substandard_and_below_ratio | 요주의이하비율 | percent |

### 자본적정성 지표
| 지표명 | 설명 | 단위 |
|--------|------|------|
| bis_ratio | BIS자기자본비율 | percent |
| tier1_ratio | Tier1 비율 | percent |
| cet1_ratio | CET1 비율 | percent |

---

## 단위 (unit)

| 값 | 설명 |
|----|------|
| KRW_billion | 십억원 (10억원) |
| KRW_trillion | 조원 |
| percent | 퍼센트 (소수점, 예: 0.15 = 15%) |
| bps | 베이시스포인트 |
| ratio | 비율 |
| count | 개수/인원 |

---

## 기간 형식 (period)

- **분기**: `YYYY-QN` (예: 2024-Q3 = 2024년 3분기)
- **연간**: `YYYY-FY` (예: 2024-FY = 2024년 연간)

---

## 데이터 범위

- **기간**: 2012년 ~ 2025년 (회사별 상이)
- **레코드 수**: 약 111,250개
- **업데이트**: 분기별 IR FactBook 발표 시
