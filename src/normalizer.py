"""
정규화 변환 모듈

회사별 지표명을 표준 지표명으로 매핑하고, 단위를 통일
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class NormalizedRecord:
    """정규화된 데이터 레코드"""
    holding_company: str
    entity: str
    category: str
    metric_std: str
    metric_original: str
    period: str
    year: int
    quarter: Optional[int]
    value: Optional[float]
    unit: str
    is_cumulative: bool
    is_estimate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환 (DB 적재용)"""
        return {
            "holding_company": self.holding_company,
            "entity": self.entity,
            "category": self.category,
            "metric_std": self.metric_std,
            "metric_original": self.metric_original,
            "period": self.period,
            "year": self.year,
            "quarter": self.quarter,
            "value": self.value,
            "unit": self.unit,
            "is_cumulative": self.is_cumulative,
            "is_estimate": self.is_estimate
        }


@dataclass
class MetricMapping:
    """지표 매핑 정보"""
    std_name: str
    category: str
    unit: str
    company_mappings: Dict[str, str] = field(default_factory=dict)


class Normalizer:
    """정규화 변환기"""

    # 회사 코드 -> 정식 명칭
    COMPANY_NAMES = {
        "woori": "우리금융지주",
        "kb": "KB금융지주",
        "shinhan": "신한금융지주",
        "hana": "하나금융지주"
    }

    # 단위 패턴
    UNIT_PATTERNS = [
        (r"KRW in billion|bn Won|Wbn|십억원|억원", "KRW_billion"),
        (r"KRW in trillion|조원", "KRW_trillion"),
        (r"%|percent|비율", "percent"),
        (r"bps|bp", "bps"),
        (r"Won|원", "won"),
        (r"명|인|employees", "count"),
    ]

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Args:
            config_dir: 설정 파일 디렉토리 경로
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"
        self.config_dir = Path(config_dir)

        self.schema: Dict[str, Any] = {}
        self.metric_mappings: Dict[str, MetricMapping] = {}
        self._reverse_mappings: Dict[str, Dict[str, str]] = {}  # 회사별 역방향 매핑

        self._load_schema()

    def _load_schema(self):
        """스키마 설정 로드"""
        schema_path = self.config_dir / "schema.yaml"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = yaml.safe_load(f)

        # 지표 매핑 로드
        if "metric_mappings" in self.schema:
            for std_name, info in self.schema["metric_mappings"].items():
                mapping = MetricMapping(
                    std_name=std_name,
                    category=info.get("category", ""),
                    unit=info.get("unit", "KRW_billion"),
                    company_mappings=info.get("mappings", {})
                )
                self.metric_mappings[std_name] = mapping

                # 역방향 매핑 구축 (회사별 원본명 -> 표준명)
                for company, original_name in mapping.company_mappings.items():
                    if company not in self._reverse_mappings:
                        self._reverse_mappings[company] = {}
                    # 정규화된 키 사용 (소문자, 공백 제거)
                    normalized_key = self._normalize_metric_name(original_name)
                    self._reverse_mappings[company][normalized_key] = std_name

    def _normalize_metric_name(self, name: str) -> str:
        """지표명 정규화 (비교용)"""
        if not name:
            return ""
        # 소문자 변환, 특수문자 제거, 공백 통일
        normalized = str(name).lower().strip()
        normalized = re.sub(r'[*\(\)\[\]]+', '', normalized)  # 특수문자 제거
        normalized = re.sub(r'\s+', ' ', normalized)  # 공백 통일
        return normalized

    def get_company_name(self, company_code: str) -> str:
        """회사 코드를 정식 명칭으로 변환"""
        return self.COMPANY_NAMES.get(company_code.lower(), company_code)

    def map_metric(
        self,
        original_name: str,
        company_code: str
    ) -> tuple[str, str, str]:
        """
        원본 지표명을 표준 지표명으로 매핑

        Args:
            original_name: 원본 지표명
            company_code: 회사 코드 (woori, kb, shinhan, hana)

        Returns:
            (표준 지표명, 카테고리, 단위) 튜플
            매핑되지 않은 경우 원본명을 snake_case로 변환
        """
        if not original_name:
            return ("unknown", "Unknown", "KRW_billion")

        # 회사명 정규화
        company_key = self._get_company_key(company_code)

        # 역방향 매핑에서 찾기
        normalized_name = self._normalize_metric_name(original_name)
        if company_key in self._reverse_mappings:
            std_name = self._reverse_mappings[company_key].get(normalized_name)
            if std_name and std_name in self.metric_mappings:
                mapping = self.metric_mappings[std_name]
                return (std_name, mapping.category, mapping.unit)

        # 매핑되지 않은 경우: 원본명을 snake_case로 변환
        std_name = self._to_snake_case(original_name)
        return (std_name, "Other", "KRW_billion")

    def _get_company_key(self, company_code: str) -> str:
        """회사 코드를 매핑 키로 변환"""
        code_mapping = {
            "woori": "우리금융",
            "kb": "KB금융",
            "shinhan": "신한금융",
            "hana": "하나금융"
        }
        code = company_code.lower()
        return code_mapping.get(code, code)

    def _to_snake_case(self, name: str) -> str:
        """문자열을 snake_case로 변환"""
        if not name:
            return "unknown"
        # 영문자, 숫자, 공백만 남기기
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', str(name))
        # 공백을 언더스코어로
        cleaned = re.sub(r'\s+', '_', cleaned.strip())
        # 연속 언더스코어 제거
        cleaned = re.sub(r'_+', '_', cleaned)
        return cleaned.lower() or "unknown"

    def detect_unit(self, text: str, default: str = "KRW_billion") -> str:
        """텍스트에서 단위 감지"""
        if not text:
            return default

        text_str = str(text)
        for pattern, unit in self.UNIT_PATTERNS:
            if re.search(pattern, text_str, re.IGNORECASE):
                return unit

        return default

    def parse_number(self, value: Any) -> Optional[float]:
        """값을 숫자로 파싱"""
        if value is None:
            return None

        if isinstance(value, (int, float)):
            if str(value).lower() in ('nan', 'inf', '-inf'):
                return None
            return float(value)

        if isinstance(value, str):
            # 빈 문자열
            if not value.strip():
                return None

            # 특수 값
            if value.strip().lower() in ('nan', '-', 'n/a', 'na', '', '-'):
                return None

            # 괄호로 감싼 음수 처리: (100) -> -100
            cleaned = value.strip()
            is_negative = False
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = cleaned[1:-1]
                is_negative = True

            # 쉼표 제거
            cleaned = cleaned.replace(',', '')

            # 퍼센트 기호 제거
            cleaned = cleaned.replace('%', '')

            try:
                result = float(cleaned)
                return -result if is_negative else result
            except ValueError:
                return None

        return None

    def normalize_record(
        self,
        company_code: str,
        entity: str,
        category: str,
        metric_original: str,
        period: str,
        year: int,
        quarter: Optional[int],
        value: Any,
        unit: Optional[str] = None,
        is_cumulative: bool = False,
        is_estimate: bool = False
    ) -> NormalizedRecord:
        """
        원시 데이터를 정규화된 레코드로 변환

        Args:
            company_code: 회사 코드
            entity: 엔티티 (지주, 은행, 카드 등)
            category: 카테고리
            metric_original: 원본 지표명
            period: 기간 (표준 형식)
            year: 연도
            quarter: 분기 (None이면 연간)
            value: 값
            unit: 단위 (None이면 자동 감지)
            is_cumulative: 누적 여부
            is_estimate: 추정치 여부

        Returns:
            NormalizedRecord 객체
        """
        # 지표 매핑
        metric_std, mapped_category, mapped_unit = self.map_metric(
            metric_original, company_code
        )

        # 카테고리 우선순위: 인자 > 매핑 결과
        final_category = category if category and category != "Other" else mapped_category

        # 단위 우선순위: 인자 > 매핑 결과
        final_unit = unit if unit else mapped_unit

        # 값 파싱
        parsed_value = self.parse_number(value)

        return NormalizedRecord(
            holding_company=self.get_company_name(company_code),
            entity=entity,
            category=final_category,
            metric_std=metric_std,
            metric_original=metric_original,
            period=period,
            year=year,
            quarter=quarter,
            value=parsed_value,
            unit=final_unit,
            is_cumulative=is_cumulative,
            is_estimate=is_estimate
        )


# 모듈 레벨 인스턴스 (지연 초기화)
_normalizer: Optional[Normalizer] = None


def get_normalizer(config_dir: Optional[Path] = None) -> Normalizer:
    """정규화기 인스턴스 반환"""
    global _normalizer
    if _normalizer is None:
        _normalizer = Normalizer(config_dir)
    return _normalizer
