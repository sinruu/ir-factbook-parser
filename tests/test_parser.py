"""
IR FactBook Parser 테스트
"""

import pytest
from pathlib import Path
import sys

# 상위 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.period_parser import PeriodParser, parse_period, is_skip_column
from src.normalizer import Normalizer, NormalizedRecord
from src.validators import DataValidator, ValidationReport


class TestPeriodParser:
    """기간 파서 테스트"""

    def setup_method(self):
        self.parser = PeriodParser()

    # ----- 우리금융/하나금융 형식 테스트 -----
    def test_woori_hana_quarterly(self):
        """FY2024 3Q 형식 테스트"""
        result = parse_period("FY2024 3Q")
        assert result is not None
        assert result.year == 2024
        assert result.quarter == 3
        assert result.is_annual is False
        assert result.standard_format == "2024-Q3"

    def test_woori_hana_annual(self):
        """FY2024 형식 테스트"""
        result = parse_period("FY2024")
        assert result is not None
        assert result.year == 2024
        assert result.quarter is None
        assert result.is_annual is True
        assert result.standard_format == "2024-FY"

    # ----- KB금융/신한금융 형식 테스트 -----
    def test_kb_shinhan_quarterly(self):
        """3Q24 형식 테스트"""
        result = parse_period("3Q24")
        assert result is not None
        assert result.year == 2024
        assert result.quarter == 3
        assert result.standard_format == "2024-Q3"

    def test_kb_estimate(self):
        """3Q25(E) 추정치 형식 테스트"""
        result = parse_period("3Q25(E)")
        assert result is not None
        assert result.year == 2025
        assert result.quarter == 3
        assert result.is_estimate is True

    # ----- 신한금융 반기 형식 테스트 -----
    def test_shinhan_half_year(self):
        """1H25 반기 형식 테스트"""
        result = parse_period("1H25")
        assert result is not None
        assert result.year == 2025
        assert result.quarter == 2  # 1H -> Q2
        assert result.is_cumulative is True

    # ----- 월별 형식 테스트 -----
    def test_year_month_full(self):
        """2024.09 형식 테스트"""
        result = parse_period("2024.09")
        assert result is not None
        assert result.year == 2024
        assert result.quarter == 3
        assert result.standard_format == "2024-Q3"

    def test_year_month_short(self):
        """'24.9 형식 테스트"""
        result = parse_period("'24.9")
        assert result is not None
        assert result.year == 2024
        assert result.quarter == 3

    def test_month_name_year(self):
        """Sep. 24 형식 테스트"""
        result = parse_period("Sep. 24")
        assert result is not None
        assert result.year == 2024
        assert result.quarter == 3

    # ----- 연간 형식 테스트 -----
    def test_annual_decimal(self):
        """2024.0 형식 테스트 (KB금융 연간)"""
        result = parse_period("2024.0")
        assert result is not None
        assert result.year == 2024
        assert result.is_annual is True

    def test_annual_short(self):
        """FY25 형식 테스트"""
        result = parse_period("FY25")
        assert result is not None
        assert result.year == 2025
        assert result.is_annual is True

    # ----- IFRS-17 마커 테스트 -----
    def test_ifrs17_marker(self):
        """IFRS-17 마커 처리 테스트"""
        result = parse_period("1Q22\n(IFRS-17)")
        assert result is not None
        assert result.year == 2022
        assert result.quarter == 1

    # ----- 스킵 컬럼 테스트 -----
    def test_skip_column_qoq(self):
        """QoQ 컬럼 스킵 테스트"""
        assert is_skip_column("QoQ") is True
        assert is_skip_column("YoY") is True
        assert is_skip_column("% 증감") is True

    def test_valid_column(self):
        """유효한 컬럼 테스트"""
        assert is_skip_column("3Q24") is False
        assert is_skip_column("FY2024") is False


class TestNormalizer:
    """정규화 변환기 테스트"""

    def setup_method(self):
        config_dir = Path(__file__).parent.parent / "config"
        self.normalizer = Normalizer(config_dir)

    def test_company_name(self):
        """회사명 변환 테스트"""
        assert self.normalizer.get_company_name("woori") == "우리금융지주"
        assert self.normalizer.get_company_name("kb") == "KB금융지주"
        assert self.normalizer.get_company_name("shinhan") == "신한금융지주"
        assert self.normalizer.get_company_name("hana") == "하나금융지주"

    def test_metric_mapping_woori(self):
        """우리금융 지표 매핑 테스트"""
        std_name, category, unit = self.normalizer.map_metric("Total Assets", "woori")
        assert std_name == "total_assets"
        assert category == "Balance Sheet"
        assert unit == "KRW_billion"

    def test_metric_mapping_kb(self):
        """KB금융 지표 매핑 테스트"""
        std_name, category, unit = self.normalizer.map_metric(
            "Net Income (attributable to controlling interests)", "kb"
        )
        assert std_name == "net_income_controlling"
        assert category == "Income Statement"

    def test_metric_mapping_shinhan(self):
        """신한금융 지표 매핑 테스트 (다른 표현)"""
        std_name, category, unit = self.normalizer.map_metric("Bad loan ratio", "shinhan")
        assert std_name == "npl_ratio"
        assert category == "Asset Quality"
        assert unit == "percent"

    def test_unmapped_metric(self):
        """매핑되지 않은 지표 테스트"""
        std_name, category, unit = self.normalizer.map_metric("Some Random Metric", "woori")
        assert std_name == "some_random_metric"
        assert category == "Other"

    def test_parse_number(self):
        """숫자 파싱 테스트"""
        assert self.normalizer.parse_number(100) == 100.0
        assert self.normalizer.parse_number("1,234.56") == 1234.56
        assert self.normalizer.parse_number("(100)") == -100.0
        assert self.normalizer.parse_number("-") is None
        assert self.normalizer.parse_number("") is None
        assert self.normalizer.parse_number("N/A") is None

    def test_normalize_record(self):
        """레코드 정규화 테스트"""
        record = self.normalizer.normalize_record(
            company_code="woori",
            entity="지주",
            category="Balance Sheet",
            metric_original="Total Assets",
            period="2024-Q3",
            year=2024,
            quarter=3,
            value="1,234,567.89",
            unit=None,
            is_cumulative=False
        )

        assert record.holding_company == "우리금융지주"
        assert record.metric_std == "total_assets"
        assert record.value == 1234567.89
        assert record.unit == "KRW_billion"


class TestValidator:
    """데이터 검증기 테스트"""

    def setup_method(self):
        config_dir = Path(__file__).parent.parent / "config"
        self.validator = DataValidator(config_dir)

    def test_valid_record(self):
        """유효한 레코드 테스트"""
        record = NormalizedRecord(
            holding_company="우리금융지주",
            entity="지주",
            category="Balance Sheet",
            metric_std="total_assets",
            metric_original="Total Assets",
            period="2024-Q3",
            year=2024,
            quarter=3,
            value=500000.0,
            unit="KRW_billion",
            is_cumulative=False
        )

        issues = self.validator.validate_record(record)
        errors = [i for i in issues if i.severity.value == "error"]
        assert len(errors) == 0

    def test_missing_company(self):
        """회사명 누락 테스트"""
        record = NormalizedRecord(
            holding_company="",
            entity="지주",
            category="Balance Sheet",
            metric_std="total_assets",
            metric_original="Total Assets",
            period="2024-Q3",
            year=2024,
            quarter=3,
            value=500000.0,
            unit="KRW_billion",
            is_cumulative=False
        )

        issues = self.validator.validate_record(record)
        error_codes = [i.code for i in issues if i.severity.value == "error"]
        assert "MISSING_COMPANY" in error_codes

    def test_invalid_quarter(self):
        """잘못된 분기 테스트"""
        record = NormalizedRecord(
            holding_company="우리금융지주",
            entity="지주",
            category="Balance Sheet",
            metric_std="total_assets",
            metric_original="Total Assets",
            period="2024-Q5",
            year=2024,
            quarter=5,  # 잘못된 분기
            value=500000.0,
            unit="KRW_billion",
            is_cumulative=False
        )

        issues = self.validator.validate_record(record)
        error_codes = [i.code for i in issues if i.severity.value == "error"]
        assert "INVALID_QUARTER" in error_codes

    def test_value_range_warning(self):
        """값 범위 경고 테스트"""
        record = NormalizedRecord(
            holding_company="우리금융지주",
            entity="지주",
            category="Asset Quality",
            metric_std="npl_ratio",
            metric_original="NPL Ratio",
            period="2024-Q3",
            year=2024,
            quarter=3,
            value=0.8,  # 80% - 너무 높음
            unit="percent",
            is_cumulative=False
        )

        issues = self.validator.validate_record(record)
        warning_codes = [i.code for i in issues if i.severity.value == "warning"]
        assert "VALUE_ABOVE_MAX" in warning_codes

    def test_validation_report(self):
        """검증 보고서 테스트"""
        records = [
            NormalizedRecord(
                holding_company="우리금융지주",
                entity="지주",
                category="Balance Sheet",
                metric_std="total_assets",
                metric_original="Total Assets",
                period="2024-Q3",
                year=2024,
                quarter=3,
                value=500000.0,
                unit="KRW_billion",
                is_cumulative=False
            ),
            NormalizedRecord(
                holding_company="KB금융지주",
                entity="지주",
                category="Income Statement",
                metric_std="net_income",
                metric_original="Net Income",
                period="2024-Q3",
                year=2024,
                quarter=3,
                value=1500.0,
                unit="KRW_billion",
                is_cumulative=False
            )
        ]

        report = self.validator.validate_records(records)

        assert report.total_records == 2
        assert report.valid_records == 2
        assert "우리금융지주" in report.by_company
        assert "KB금융지주" in report.by_company


class TestIntegration:
    """통합 테스트"""

    def test_end_to_end_flow(self):
        """전체 흐름 테스트 (파싱 없이 변환만)"""
        from src.normalizer import get_normalizer
        from src.validators import validate_records

        normalizer = get_normalizer()

        # 테스트 데이터
        test_data = [
            ("woori", "Total Assets", 500000),
            ("kb", "Net Income", 1500),
            ("shinhan", "BIS capital ratio(SFG)*", 0.14),
            ("hana", "NIM", 0.015),
        ]

        records = []
        for company, metric, value in test_data:
            record = normalizer.normalize_record(
                company_code=company,
                entity="지주",
                category="",
                metric_original=metric,
                period="2024-Q3",
                year=2024,
                quarter=3,
                value=value
            )
            records.append(record)

        # 검증
        report = validate_records(records)

        assert report.total_records == 4
        assert len(report.by_company) == 4
        assert "total_assets" in report.metrics_found


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
