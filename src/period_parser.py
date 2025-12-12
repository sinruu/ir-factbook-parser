"""
기간 형식 파서 모듈

다양한 금융지주사의 기간 표기 형식을 표준 형식(YYYY-QN)으로 변환
"""

import re
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParsedPeriod:
    """파싱된 기간 정보"""
    year: int
    quarter: Optional[int]  # 1-4, None이면 연간
    is_annual: bool
    is_cumulative: bool  # 누적 데이터 여부 (1H, 3Q 누적 등)
    is_estimate: bool  # 추정치 여부
    original: str  # 원본 문자열

    @property
    def standard_format(self) -> str:
        """표준 형식 반환 (YYYY-QN 또는 YYYY-FY)"""
        if self.is_annual:
            return f"{self.year}-FY"
        return f"{self.year}-Q{self.quarter}"

    def to_dict(self) -> dict:
        """딕셔너리 변환 (DB 적재용)"""
        return {
            "period": self.standard_format,
            "year": self.year,
            "quarter": self.quarter,
            "is_annual": self.is_annual,
            "is_cumulative": self.is_cumulative,
            "is_estimate": self.is_estimate,
            "period_original": self.original
        }


# 월 -> 분기 매핑
MONTH_TO_QUARTER = {
    1: 1, 2: 1, 3: 1,
    4: 2, 5: 2, 6: 2,
    7: 3, 8: 3, 9: 3,
    10: 4, 11: 4, 12: 4
}

# 월 이름 -> 숫자 매핑
MONTH_NAME_TO_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12
}


class PeriodParser:
    """기간 형식 파서"""

    # 파싱 패턴 정의 (우선순위 순)
    PATTERNS = [
        # FY2024 3Q (우리금융, 하나금융)
        (r"FY(\d{4})\s*(\d)Q", "woori_hana_quarterly"),

        # FY2024 (연간)
        (r"FY(\d{4})$", "annual_full"),

        # FY25 (연간, 2자리 연도)
        (r"FY(\d{2})$", "annual_short"),

        # 3Q24 (KB금융, 신한금융)
        (r"(\d)Q(\d{2})(?:\(E\))?", "kb_shinhan_quarterly"),

        # 1H25 (반기, 신한금융)
        (r"(\d)H(\d{2})", "half_year"),

        # 2024.09 또는 2024.9 (월별)
        (r"(\d{4})\.(\d{1,2})", "year_month_full"),

        # '24.9 또는 '24.09 (월별, 2자리 연도)
        (r"'(\d{2})\.(\d{1,2})", "year_month_short"),

        # Sep. 24 또는 Sep 24 (KB금융 월별)
        (r"([A-Za-z]{3})\.?\s*(\d{2})", "month_name_year"),

        # 2024.0 (연간, KB금융)
        (r"(\d{4})\.0", "annual_decimal"),

        # 2024 (연간, 숫자만)
        (r"^(\d{4})$", "annual_only"),
    ]

    def __init__(self):
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in self.PATTERNS
        ]

    def parse(self, period_str: str) -> Optional[ParsedPeriod]:
        """
        기간 문자열을 파싱하여 표준 형식으로 변환

        Args:
            period_str: 원본 기간 문자열

        Returns:
            ParsedPeriod 객체 또는 None (파싱 실패 시)
        """
        if not period_str:
            return None

        # 문자열 정리
        period_str = str(period_str).strip()

        # 추정치 마커 확인
        is_estimate = "(E)" in period_str.upper()

        # IFRS-17 마커 제거 (신한금융)
        clean_str = re.sub(r'\(IFRS-17\)', '', period_str).strip()
        clean_str = re.sub(r'\n.*', '', clean_str).strip()  # 줄바꿈 이후 제거

        for pattern, pattern_name in self._compiled_patterns:
            match = pattern.search(clean_str)
            if match:
                result = self._parse_by_pattern(match, pattern_name, period_str, is_estimate)
                if result:
                    return result

        return None

    def _parse_by_pattern(
        self,
        match: re.Match,
        pattern_name: str,
        original: str,
        is_estimate: bool
    ) -> Optional[ParsedPeriod]:
        """패턴별 파싱 로직"""

        if pattern_name == "woori_hana_quarterly":
            # FY2024 3Q
            year = int(match.group(1))
            quarter = int(match.group(2))
            return ParsedPeriod(
                year=year,
                quarter=quarter,
                is_annual=False,
                is_cumulative=False,
                is_estimate=is_estimate,
                original=original
            )

        elif pattern_name == "annual_full":
            # FY2024
            year = int(match.group(1))
            return ParsedPeriod(
                year=year,
                quarter=None,
                is_annual=True,
                is_cumulative=False,
                is_estimate=is_estimate,
                original=original
            )

        elif pattern_name == "annual_short":
            # FY25 -> 2025
            year = 2000 + int(match.group(1))
            return ParsedPeriod(
                year=year,
                quarter=None,
                is_annual=True,
                is_cumulative=False,
                is_estimate=is_estimate,
                original=original
            )

        elif pattern_name == "kb_shinhan_quarterly":
            # 3Q24 -> 2024-Q3
            quarter = int(match.group(1))
            year = 2000 + int(match.group(2))
            return ParsedPeriod(
                year=year,
                quarter=quarter,
                is_annual=False,
                is_cumulative=False,
                is_estimate=is_estimate,
                original=original
            )

        elif pattern_name == "half_year":
            # 1H25 -> 반기 (누적)
            half = int(match.group(1))
            year = 2000 + int(match.group(2))
            # 반기를 분기로 변환 (1H -> Q2, 2H -> Q4)
            quarter = half * 2
            return ParsedPeriod(
                year=year,
                quarter=quarter,
                is_annual=False,
                is_cumulative=True,  # 반기는 누적 데이터
                is_estimate=is_estimate,
                original=original
            )

        elif pattern_name == "year_month_full":
            # 2024.09 -> 2024-Q3
            year = int(match.group(1))
            month = int(match.group(2))
            quarter = MONTH_TO_QUARTER.get(month)
            if quarter:
                return ParsedPeriod(
                    year=year,
                    quarter=quarter,
                    is_annual=False,
                    is_cumulative=False,
                    is_estimate=is_estimate,
                    original=original
                )

        elif pattern_name == "year_month_short":
            # '24.9 -> 2024-Q3
            year = 2000 + int(match.group(1))
            month = int(match.group(2))
            quarter = MONTH_TO_QUARTER.get(month)
            if quarter:
                return ParsedPeriod(
                    year=year,
                    quarter=quarter,
                    is_annual=False,
                    is_cumulative=False,
                    is_estimate=is_estimate,
                    original=original
                )

        elif pattern_name == "month_name_year":
            # Sep. 24 -> 2024-Q3
            month_name = match.group(1).lower()
            year = 2000 + int(match.group(2))
            month = MONTH_NAME_TO_NUM.get(month_name)
            if month:
                quarter = MONTH_TO_QUARTER.get(month)
                return ParsedPeriod(
                    year=year,
                    quarter=quarter,
                    is_annual=False,
                    is_cumulative=False,
                    is_estimate=is_estimate,
                    original=original
                )

        elif pattern_name == "annual_decimal":
            # 2024.0 -> 2024-FY
            year = int(match.group(1))
            return ParsedPeriod(
                year=year,
                quarter=None,
                is_annual=True,
                is_cumulative=False,
                is_estimate=is_estimate,
                original=original
            )

        elif pattern_name == "annual_only":
            # 2024 -> 2024-FY
            year = int(match.group(1))
            return ParsedPeriod(
                year=year,
                quarter=None,
                is_annual=True,
                is_cumulative=False,
                is_estimate=is_estimate,
                original=original
            )

        return None

    def is_skip_column(self, col_name: str) -> bool:
        """건너뛸 컬럼인지 확인 (QoQ, YoY 등)"""
        if not col_name:
            return True

        skip_patterns = [
            r"^QoQ",
            r"^YoY",
            r"^%",
            r"증감",
            r"변동",
        ]

        col_str = str(col_name).strip()
        for pattern in skip_patterns:
            if re.search(pattern, col_str, re.IGNORECASE):
                return True

        return False


# 모듈 레벨 인스턴스
_parser = PeriodParser()


def parse_period(period_str: str) -> Optional[ParsedPeriod]:
    """기간 문자열 파싱 (편의 함수)"""
    return _parser.parse(period_str)


def is_skip_column(col_name: str) -> bool:
    """건너뛸 컬럼인지 확인 (편의 함수)"""
    return _parser.is_skip_column(col_name)
