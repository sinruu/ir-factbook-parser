"""
데이터 검증 모듈

파싱된 데이터의 유효성을 검증하고 품질 보고서 생성
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from .normalizer import NormalizedRecord


class ValidationSeverity(Enum):
    """검증 심각도"""
    ERROR = "error"      # 치명적 오류
    WARNING = "warning"  # 경고
    INFO = "info"        # 정보


@dataclass
class ValidationIssue:
    """검증 이슈"""
    severity: ValidationSeverity
    code: str
    message: str
    record: Optional[Dict[str, Any]] = None
    field: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "record": self.record
        }


@dataclass
class ValidationReport:
    """검증 보고서"""
    total_records: int = 0
    valid_records: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)

    # 통계
    by_company: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)
    by_period: Dict[str, int] = field(default_factory=dict)
    metrics_found: Set[str] = field(default_factory=set)
    missing_required_metrics: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

    @property
    def is_valid(self) -> bool:
        """치명적 오류가 없으면 유효"""
        return self.error_count == 0

    def add_issue(self, issue: ValidationIssue):
        self.issues.append(issue)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_records": self.total_records,
                "valid_records": self.valid_records,
                "error_count": self.error_count,
                "warning_count": self.warning_count,
                "is_valid": self.is_valid
            },
            "statistics": {
                "by_company": self.by_company,
                "by_category": self.by_category,
                "by_period": dict(sorted(self.by_period.items())),
                "unique_metrics": len(self.metrics_found),
                "metrics_found": sorted(self.metrics_found)
            },
            "missing_required_metrics": self.missing_required_metrics,
            "issues": [i.to_dict() for i in self.issues[:100]]  # 최대 100개
        }

    def print_summary(self):
        """요약 출력"""
        print(f"\n{'='*60}")
        print("검증 보고서")
        print(f"{'='*60}")
        print(f"총 레코드: {self.total_records:,}")
        print(f"유효 레코드: {self.valid_records:,}")
        print(f"오류: {self.error_count}")
        print(f"경고: {self.warning_count}")
        print(f"\n회사별 레코드:")
        for company, count in sorted(self.by_company.items()):
            print(f"  - {company}: {count:,}")
        print(f"\n발견된 고유 지표 수: {len(self.metrics_found)}")

        if self.missing_required_metrics:
            print(f"\n필수 지표 누락:")
            for company, metrics in self.missing_required_metrics.items():
                print(f"  - {company}: {', '.join(metrics)}")

        if self.issues:
            print(f"\n주요 이슈 (최대 10개):")
            for issue in self.issues[:10]:
                print(f"  [{issue.severity.value.upper()}] {issue.message}")


class DataValidator:
    """데이터 검증기"""

    # 기본 범위 검증 규칙
    DEFAULT_RANGE_CHECKS = {
        "total_assets": {"min": 0, "max": 2_000_000},  # 2000조 (십억 단위)
        "npl_ratio": {"min": 0, "max": 0.5},  # 50%
        "bis_ratio": {"min": 0.05, "max": 0.5},  # 5% ~ 50%
        "cet1_ratio": {"min": 0.05, "max": 0.5},
        "tier1_ratio": {"min": 0.05, "max": 0.5},
        "nim": {"min": 0, "max": 0.15},  # 15%
        "nis": {"min": 0, "max": 0.15},
        "roe": {"min": -0.5, "max": 0.5},  # -50% ~ 50%
        "roa": {"min": -0.1, "max": 0.1},  # -10% ~ 10%
    }

    # 필수 지표
    DEFAULT_REQUIRED_METRICS = [
        "total_assets",
        "net_income",
        "npl_ratio",
        "bis_ratio"
    ]

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Args:
            config_dir: 설정 파일 디렉토리 경로
        """
        self.range_checks = self.DEFAULT_RANGE_CHECKS.copy()
        self.required_metrics = self.DEFAULT_REQUIRED_METRICS.copy()

        if config_dir:
            self._load_config(config_dir)

    def _load_config(self, config_dir: Path):
        """설정 파일에서 검증 규칙 로드"""
        schema_path = config_dir / "schema.yaml"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = yaml.safe_load(f)

            if "validation_rules" in schema:
                rules = schema["validation_rules"]
                if "range_checks" in rules:
                    self.range_checks.update(rules["range_checks"])
                if "required_metrics" in rules:
                    self.required_metrics = rules["required_metrics"]

    def validate_records(
        self,
        records: List[NormalizedRecord]
    ) -> ValidationReport:
        """
        레코드 목록 검증

        Args:
            records: 정규화된 레코드 목록

        Returns:
            ValidationReport 객체
        """
        report = ValidationReport()
        report.total_records = len(records)

        # 회사별 발견된 지표 추적
        company_metrics: Dict[str, Set[str]] = {}

        for record in records:
            issues = self.validate_record(record)

            # 통계 업데이트
            report.by_company[record.holding_company] = \
                report.by_company.get(record.holding_company, 0) + 1
            report.by_category[record.category] = \
                report.by_category.get(record.category, 0) + 1
            report.by_period[record.period] = \
                report.by_period.get(record.period, 0) + 1
            report.metrics_found.add(record.metric_std)

            # 회사별 지표 추적
            if record.holding_company not in company_metrics:
                company_metrics[record.holding_company] = set()
            company_metrics[record.holding_company].add(record.metric_std)

            # 이슈 추가
            for issue in issues:
                report.add_issue(issue)

            # 유효 레코드 카운트 (ERROR가 없으면 유효)
            if not any(i.severity == ValidationSeverity.ERROR for i in issues):
                report.valid_records += 1

        # 필수 지표 누락 확인
        for company, metrics in company_metrics.items():
            missing = [m for m in self.required_metrics if m not in metrics]
            if missing:
                report.missing_required_metrics[company] = missing
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_REQUIRED_METRIC",
                    message=f"{company}에서 필수 지표 누락: {', '.join(missing)}"
                ))

        return report

    def validate_record(self, record: NormalizedRecord) -> List[ValidationIssue]:
        """
        단일 레코드 검증

        Args:
            record: 정규화된 레코드

        Returns:
            ValidationIssue 목록
        """
        issues = []

        # 1. 필수 필드 검증
        if not record.holding_company:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_COMPANY",
                message="회사명이 누락됨",
                record=record.to_dict()
            ))

        if not record.period:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_PERIOD",
                message="기간이 누락됨",
                record=record.to_dict()
            ))

        if not record.metric_std:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_METRIC",
                message="지표명이 누락됨",
                record=record.to_dict()
            ))

        # 2. 값 검증
        if record.value is not None:
            # 범위 검증
            if record.metric_std in self.range_checks:
                range_rule = self.range_checks[record.metric_std]
                min_val = range_rule.get("min")
                max_val = range_rule.get("max")

                # 퍼센트 단위일 경우 값 조정 확인
                check_value = record.value
                if record.unit == "percent" and check_value > 1:
                    # 이미 퍼센트로 표현된 경우 (예: 15.5)
                    check_value = check_value / 100

                if min_val is not None and check_value < min_val:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="VALUE_BELOW_MIN",
                        message=f"{record.metric_std} 값({record.value})이 최소값({min_val})보다 작음",
                        record=record.to_dict(),
                        field="value"
                    ))

                if max_val is not None and check_value > max_val:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="VALUE_ABOVE_MAX",
                        message=f"{record.metric_std} 값({record.value})이 최대값({max_val})보다 큼",
                        record=record.to_dict(),
                        field="value"
                    ))

        # 3. 연도 유효성
        if record.year:
            if record.year < 2000 or record.year > 2030:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="INVALID_YEAR",
                    message=f"연도({record.year})가 유효 범위(2000-2030)를 벗어남",
                    record=record.to_dict(),
                    field="year"
                ))

        # 4. 분기 유효성
        if record.quarter is not None:
            if record.quarter < 1 or record.quarter > 4:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_QUARTER",
                    message=f"분기({record.quarter})가 유효 범위(1-4)를 벗어남",
                    record=record.to_dict(),
                    field="quarter"
                ))

        # 5. 단위 유효성
        valid_units = {
            "KRW_billion", "KRW_trillion", "percent", "bps",
            "ratio", "won", "count"
        }
        if record.unit and record.unit not in valid_units:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="UNKNOWN_UNIT",
                message=f"알 수 없는 단위: {record.unit}",
                record=record.to_dict(),
                field="unit"
            ))

        return issues


# 모듈 레벨 함수
def validate_records(
    records: List[NormalizedRecord],
    config_dir: Optional[Path] = None
) -> ValidationReport:
    """레코드 목록 검증 (편의 함수)"""
    validator = DataValidator(config_dir)
    return validator.validate_records(records)
