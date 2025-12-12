# 4대 금융지주 IR FactBook 구조 분석 결과

## 분석 대상

| 회사 | 파일명 | 시트 수 | 기준일 |
|------|--------|--------|--------|
| 우리금융 | 202510300310445000.xlsx | 25개 | 2025년 3분기 |
| KB금융 | 2025_3Q_Factbook.xlsx | 51개 | 2025년 3분기 |
| 신한금융 | SFG_FactBook_3Q25.xlsx | 40개 | 2025년 3분기 |
| 하나금융 | HFG_IR_Databook_3Q25.xlsx | 24개 | 2025년 3분기 |

---

## 1. 구조 비교

### 1.1 시트 명명 규칙

| 회사 | 패턴 | 예시 |
|------|------|------|
| 우리금융 | `{Category}_{Entity}` | `Asset Quality_Group`, `Loans_Bank` |
| KB금융 | `{Entity}_{Category}` | `G_IS`, `B_AQ`, `C_BS` |
| 신한금융 | `{Category}_{Entity}` | `IS_SHB`, `Asset Quality_SHB` |
| 하나금융 | `{Category}_{Entity}` | `Asset Quality_G`, `Loan&Dep_Hana Bank` |

### 1.2 헤더 위치 (0-indexed)

| 회사 | 헤더 행 | 데이터 시작 행 | 지표 열 | 데이터 시작 열 |
|------|---------|---------------|---------|---------------|
| 우리금융 | 3 | 6 | 3-6 (계층적) | 7 |
| KB금융 | 7-8 | 8-10 | 7 | 8 |
| 신한금융 | 2 | 3 | 3-4 | 8 |
| 하나금융 | 3 | 5 | 3 | 7 |

### 1.3 기간 표기 형식

| 회사 | 분기 형식 | 연간 형식 | 예시 |
|------|----------|----------|------|
| 우리금융 | `FY{YYYY} {N}Q` | `FY{YYYY}` | FY2024 3Q, FY2024 |
| KB금융 | `{N}Q{YY}` | `{YYYY}.0` | 3Q24, 2024.0 |
| 신한금융 | `{N}Q{YY}` or `'{YY}.{MM}` | `FY{YY}` | 3Q25, '25.09, FY25 |
| 하나금융 | `FY{YYYY} {N}Q` | `FY{YYYY}` | FY2024 3Q, FY2024 |

---

## 2. 주요 차이점

### 2.1 신한금융 특이사항
- **IFRS-17 이중 컬럼**: 2022년부터 IFRS-17 적용 전/후 데이터가 병존
  - 예: `1Q22`, `1Q22\n(IFRS-17)`
- **누적 데이터**: IS 데이터가 분기가 아닌 누적 형태 (1Q, 1H, 3Q, FY)
- 파서 설계 시 누적→분기 변환 로직 필요

### 2.2 KB금융 특이사항
- **시트 수 최다** (51개): 가장 상세한 자회사별 데이터 제공
- **엔티티 접두사**: G_, B_, S_, I_, C_, L_ 로 체계적 구분
- **날짜 형식 혼재**: `3Q24` (분기) + `Sep. 24` (월별) 혼용

### 2.3 우리/하나 유사성
- 기간 형식 동일: `FY{YYYY} {N}Q`
- 시트 구조 유사
- 파싱 로직 공유 가능

---

## 3. 공통 지표 매핑

### 3.1 핵심 재무지표

| 표준명 | 우리 | KB | 신한 | 하나 |
|--------|------|-----|------|------|
| 총자산 | Total Assets | Total Assets | Total Assets | Total Assets |
| 순이익 | Net Income | Net Income | Net Income (Accumulated) | Net Income |
| 지배주주순이익 | Net Income (Controlling Interest) | Net Income (attributable to controlling interests) | Net income attributable to controlling interest | Net Income (Controlling Interest) |
| 자기자본 | Total Equity | Total Equity | Shareholders' equity | Total Equity |

### 3.2 이자이익 지표

| 표준명 | 우리 | KB | 신한 | 하나 |
|--------|------|-----|------|------|
| 순이자이익 | Interest Income | Net interest income | Interest Income (b) | Net Interest Income |
| NIM | NIM | NIM | NIM | NIM |
| NIS | NIS | NIS | NIS | NIS |

### 3.3 자산건전성 지표

| 표준명 | 우리 | KB | 신한 | 하나 |
|--------|------|-----|------|------|
| 총여신 | Total Credit * | Total Outstanding Credits | Total | Total Credit* |
| NPL | NPL** | NPL (A) | Substandard & below | NPL |
| NPL비율 | NPL Ratio | NPL Ratio | Bad loan ratio | NPL ratio |
| 요주의이하비율 | Precautionary & Below | Precautionary & Below Ratio | Precautionary & below ratio | Precautionary & below ratio |

### 3.4 자본적정성 지표

| 표준명 | 우리 | KB | 신한 | 하나 |
|--------|------|-----|------|------|
| BIS비율 | BIS Ratio | BIS Ratio | BIS capital ratio(SFG)* | BIS Ratio |
| Tier1비율 | Tier 1 Ratio | Tier 1 Capital Ratio | (TierⅠ ratio)* | Tier1 Ratio |
| CET1비율 | CET1 Ratio | CET1 Ratio | (Common Equity Tier Ⅰ Ratio)* | CET1 Ratio |

---

## 4. 정규화 출력 형식

### 4.1 스키마

```csv
holding_company,entity,category,metric_std,metric_original,period,value,unit,is_cumulative
우리금융지주,지주,Asset Quality,npl_ratio,NPL Ratio,2024-Q3,0.0069,percent,false
KB금융지주,지주,Income Statement,net_income,Net Income,2024-Q3,1655.2,KRW_billion,false
신한금융지주,지주,Income Statement,net_income,Net Income (Accumulated),2024-Q3,4044.079389,KRW_billion,true
하나금융지주,은행,Interest Income,nim,NIM,2024-Q3,0.0154,percent,false
```

### 4.2 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| holding_company | string | 금융지주사명 |
| entity | string | 법인 (지주/은행/카드/증권 등) |
| category | string | 지표 대분류 |
| metric_std | string | 표준화된 지표명 (영문 snake_case) |
| metric_original | string | 원본 지표명 |
| period | string | 기간 (YYYY-QN 형식) |
| value | float | 수치 |
| unit | string | 단위 (KRW_billion/percent/bps 등) |
| is_cumulative | boolean | 누적 여부 |

---

## 5. 파싱 우선순위 권장

1. **우리금융 + 하나금융** (구조 유사, 먼저 구현)
2. **KB금융** (시트 수 많지만 규칙적)
3. **신한금융** (IFRS-17, 누적 데이터 처리 필요)

---

## 6. 다음 단계

1. ✅ 구조 분석 완료
2. ✅ 공통 스키마 설계
3. ✅ 회사별 파싱 규칙 정의
4. ⬜ 파서 프로토타입 구현
5. ⬜ 샘플 데이터로 검증
6. ⬜ 에러 핸들링 추가
7. ⬜ GitHub 레포지토리 구성
