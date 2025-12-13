# NL→SQL 예시 쿼리 모음

## 1. 단순 조회

### 특정 회사 특정 지표
**Q**: KB금융 2024년 3분기 당기순이익은?
```sql
SELECT value, unit FROM financial_metrics
WHERE holding_company = 'KB금융지주'
  AND metric_std = 'net_income'
  AND period = '2024-Q3'
  AND entity = '지주';
```

### 최신 데이터 조회
**Q**: 신한금융 가장 최근 NIM은?
```sql
SELECT period, value * 100 as nim_pct FROM financial_metrics
WHERE holding_company = '신한금융지주'
  AND metric_std = 'nim'
  AND entity = '은행'
  AND is_estimate = FALSE
ORDER BY year DESC, quarter DESC NULLS LAST
LIMIT 1;
```

---

## 2. 회사 간 비교

### 동일 기간 비교
**Q**: 2024년 3분기 4대 금융지주 ROE 비교
```sql
SELECT holding_company, value * 100 as roe_pct
FROM financial_metrics
WHERE metric_std = 'roe'
  AND period = '2024-Q3'
  AND entity = '지주'
  AND is_estimate = FALSE
ORDER BY value DESC;
```

### 순위 조회
**Q**: 총자산 기준 금융지주 순위
```sql
SELECT
    ROW_NUMBER() OVER (ORDER BY value DESC) as rank,
    holding_company,
    value as total_assets_bn
FROM financial_metrics
WHERE metric_std = 'total_assets'
  AND period = '2024-Q3'
  AND entity = '지주'
  AND is_estimate = FALSE;
```

---

## 3. 시계열 분석

### 분기별 추이
**Q**: 하나금융 최근 8분기 순이익 추이
```sql
SELECT period, value as net_income_bn
FROM financial_metrics
WHERE holding_company = '하나금융지주'
  AND metric_std = 'net_income'
  AND entity = '지주'
  AND quarter IS NOT NULL
  AND is_estimate = FALSE
ORDER BY year DESC, quarter DESC
LIMIT 8;
```

### 연도별 평균
**Q**: 우리금융 연도별 평균 NIM
```sql
SELECT year, AVG(value) * 100 as avg_nim_pct
FROM financial_metrics
WHERE holding_company = '우리금융지주'
  AND metric_std = 'nim'
  AND entity = '은행'
  AND quarter IS NOT NULL
GROUP BY year
ORDER BY year;
```

### YoY 비교
**Q**: KB금융 순이익 전년동기 대비
```sql
WITH current_q AS (
    SELECT value FROM financial_metrics
    WHERE holding_company = 'KB금융지주'
      AND metric_std = 'net_income'
      AND period = '2024-Q3'
      AND entity = '지주'
),
prev_q AS (
    SELECT value FROM financial_metrics
    WHERE holding_company = 'KB금융지주'
      AND metric_std = 'net_income'
      AND period = '2023-Q3'
      AND entity = '지주'
)
SELECT
    (SELECT value FROM current_q) as current_val,
    (SELECT value FROM prev_q) as prev_val,
    ((SELECT value FROM current_q) - (SELECT value FROM prev_q)) / (SELECT value FROM prev_q) * 100 as yoy_pct;
```

---

## 4. 건전성 분석

### NPL 비율 비교
**Q**: 4대 금융지주 NPL비율 비교 (낮은 순)
```sql
SELECT holding_company, value * 100 as npl_ratio_pct
FROM financial_metrics
WHERE metric_std = 'npl_ratio'
  AND period = '2024-Q3'
  AND entity = '지주'
  AND is_estimate = FALSE
ORDER BY value ASC;
```

### 자본비율 현황
**Q**: 각 금융지주 BIS비율, Tier1비율, CET1비율
```sql
SELECT
    holding_company,
    MAX(CASE WHEN metric_std = 'bis_ratio' THEN value * 100 END) as bis_pct,
    MAX(CASE WHEN metric_std = 'tier1_ratio' THEN value * 100 END) as tier1_pct,
    MAX(CASE WHEN metric_std = 'cet1_ratio' THEN value * 100 END) as cet1_pct
FROM financial_metrics
WHERE metric_std IN ('bis_ratio', 'tier1_ratio', 'cet1_ratio')
  AND period = '2024-Q3'
  AND entity = '지주'
  AND is_estimate = FALSE
GROUP BY holding_company
ORDER BY holding_company;
```

---

## 5. 부문별 분석

### 은행 vs 카드 비교
**Q**: KB금융 은행/카드 부문 순이익 비교
```sql
SELECT entity, value as net_income_bn
FROM financial_metrics
WHERE holding_company = 'KB금융지주'
  AND metric_std = 'net_income'
  AND entity IN ('은행', '카드')
  AND period = '2024-Q3'
ORDER BY value DESC;
```

### 사업부문 구성
**Q**: 신한금융 부문별 순이익 비중
```sql
WITH total AS (
    SELECT SUM(value) as total_income
    FROM financial_metrics
    WHERE holding_company = '신한금융지주'
      AND metric_std = 'net_income'
      AND period = '2024-Q3'
      AND entity != '지주'
)
SELECT
    entity,
    value as net_income_bn,
    value / (SELECT total_income FROM total) * 100 as pct
FROM financial_metrics
WHERE holding_company = '신한금융지주'
  AND metric_std = 'net_income'
  AND period = '2024-Q3'
  AND entity != '지주'
ORDER BY value DESC;
```

---

## 6. 집계 쿼리

### 평균/합계
**Q**: 4대 금융지주 평균 총자산
```sql
SELECT AVG(value) as avg_total_assets_bn
FROM financial_metrics
WHERE metric_std = 'total_assets'
  AND period = '2024-Q3'
  AND entity = '지주'
  AND is_estimate = FALSE;
```

### 그룹별 통계
**Q**: 연도별 4대 금융지주 합산 순이익
```sql
SELECT year, SUM(value) as total_net_income_bn
FROM financial_metrics
WHERE metric_std = 'net_income'
  AND entity = '지주'
  AND quarter = 3  -- 3분기 기준
  AND is_estimate = FALSE
GROUP BY year
ORDER BY year;
```

---

## 7. 메타 쿼리

### 사용 가능한 지표 목록
```sql
SELECT DISTINCT metric_std, metric_original, unit
FROM financial_metrics
WHERE entity = '지주'
ORDER BY metric_std;
```

### 데이터 범위 확인
```sql
SELECT
    MIN(year) as from_year,
    MAX(year) as to_year,
    COUNT(DISTINCT period) as periods,
    COUNT(*) as total_records
FROM financial_metrics;
```

### 회사별 레코드 수
```sql
SELECT holding_company, COUNT(*) as records
FROM financial_metrics
GROUP BY holding_company
ORDER BY records DESC;
```
