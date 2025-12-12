"""
CLI 인터페이스 모듈

IR FactBook Parser의 명령행 인터페이스
"""

import sys
import json
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from .parser import FactBookParser, parse_factbook, export_to_csv, export_to_json
from .validators import validate_records, ValidationReport
from .normalizer import NormalizedRecord


console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="ir-factbook-parser")
def cli():
    """
    IR FactBook Parser - 4대 금융지주 IR FactBook 정규화 도구

    4대 금융지주(우리, KB, 신한, 하나)의 IR FactBook Excel 파일을
    정규화된 데이터로 변환합니다.
    """
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="출력 파일 경로 (기본값: output/normalized.csv)"
)
@click.option(
    "-f", "--format",
    type=click.Choice(["csv", "json", "both"]),
    default="csv",
    help="출력 형식 (기본값: csv)"
)
@click.option(
    "-c", "--company",
    type=click.Choice(["woori", "kb", "shinhan", "hana"]),
    help="회사 코드 (지정하지 않으면 자동 감지)"
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="데이터 검증 수행 여부 (기본값: True)"
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="상세 출력"
)
def parse(
    input_file: str,
    output: Optional[str],
    format: str,
    company: Optional[str],
    validate: bool,
    verbose: bool
):
    """
    FactBook Excel 파일을 파싱하여 정규화된 데이터로 변환

    INPUT_FILE: 파싱할 Excel 파일 경로
    """
    input_path = Path(input_file)

    # 출력 경로 설정
    if output is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        base_name = input_path.stem
        output = str(output_dir / f"{base_name}_normalized")
    else:
        output = output.rsplit(".", 1)[0]  # 확장자 제거

    console.print(Panel.fit(
        f"[bold blue]IR FactBook Parser[/bold blue]\n"
        f"입력: {input_path.name}\n"
        f"회사: {company or '자동 감지'}",
        title="파싱 시작"
    ))

    # 파싱 실행
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("파싱 중...", total=None)

        try:
            records = parse_factbook(input_file, company)
            progress.update(task, description=f"파싱 완료: {len(records)} 레코드")
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")
            sys.exit(1)

    if not records:
        console.print("[yellow]경고: 파싱된 레코드가 없습니다.[/yellow]")
        sys.exit(0)

    # 검증
    if validate:
        console.print("\n[bold]데이터 검증 중...[/bold]")
        report = validate_records(records)
        _print_validation_summary(report, verbose)

    # 내보내기
    console.print("\n[bold]내보내기 중...[/bold]")

    if format in ("csv", "both"):
        csv_path = f"{output}.csv"
        export_to_csv(records, csv_path)
        console.print(f"  ✓ CSV: {csv_path}")

    if format in ("json", "both"):
        json_path = f"{output}.json"
        export_to_json(records, json_path)
        console.print(f"  ✓ JSON: {json_path}")

    console.print(f"\n[green]완료! {len(records)}개 레코드 처리됨[/green]")


@cli.command()
@click.argument("input_files", nargs=-1, type=click.Path(exists=True))
@click.option(
    "-o", "--output",
    type=click.Path(),
    default="output/all_normalized.csv",
    help="출력 파일 경로"
)
@click.option(
    "-f", "--format",
    type=click.Choice(["csv", "json", "both"]),
    default="csv",
    help="출력 형식"
)
def batch(input_files: tuple, output: str, format: str):
    """
    여러 FactBook 파일을 일괄 처리

    INPUT_FILES: 파싱할 Excel 파일들
    """
    if not input_files:
        console.print("[red]오류: 입력 파일을 지정하세요.[/red]")
        sys.exit(1)

    all_records: List[NormalizedRecord] = []

    console.print(Panel.fit(
        f"[bold blue]일괄 처리[/bold blue]\n"
        f"파일 수: {len(input_files)}",
        title="시작"
    ))

    for input_file in input_files:
        console.print(f"\n처리 중: {Path(input_file).name}")
        try:
            records = parse_factbook(input_file)
            all_records.extend(records)
            console.print(f"  ✓ {len(records)} 레코드")
        except Exception as e:
            console.print(f"  [red]✗ 오류: {e}[/red]")

    if not all_records:
        console.print("[yellow]경고: 파싱된 레코드가 없습니다.[/yellow]")
        sys.exit(0)

    # 검증
    console.print("\n[bold]데이터 검증 중...[/bold]")
    report = validate_records(all_records)
    _print_validation_summary(report, verbose=False)

    # 내보내기
    output_base = output.rsplit(".", 1)[0]
    Path(output_base).parent.mkdir(parents=True, exist_ok=True)

    if format in ("csv", "both"):
        csv_path = f"{output_base}.csv"
        export_to_csv(all_records, csv_path)
        console.print(f"\n✓ CSV: {csv_path}")

    if format in ("json", "both"):
        json_path = f"{output_base}.json"
        export_to_json(all_records, json_path)
        console.print(f"✓ JSON: {json_path}")

    console.print(f"\n[green]완료! 총 {len(all_records)}개 레코드[/green]")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "-c", "--company",
    type=click.Choice(["woori", "kb", "shinhan", "hana"]),
    help="회사 코드"
)
def validate_cmd(input_file: str, company: Optional[str]):
    """
    FactBook 파일의 데이터 품질 검증

    INPUT_FILE: 검증할 Excel 파일 경로
    """
    console.print("[bold]파싱 및 검증 중...[/bold]")

    try:
        records = parse_factbook(input_file, company)
    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")
        sys.exit(1)

    report = validate_records(records)
    _print_validation_summary(report, verbose=True)

    # 상세 이슈 출력
    if report.issues:
        console.print("\n[bold]상세 이슈:[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("심각도", width=10)
        table.add_column("코드", width=25)
        table.add_column("메시지", width=50)

        for issue in report.issues[:20]:
            severity_color = {
                "error": "red",
                "warning": "yellow",
                "info": "blue"
            }.get(issue.severity.value, "white")

            table.add_row(
                f"[{severity_color}]{issue.severity.value.upper()}[/{severity_color}]",
                issue.code,
                issue.message[:50]
            )

        console.print(table)

        if len(report.issues) > 20:
            console.print(f"... 외 {len(report.issues) - 20}개 이슈")


@cli.command()
def info():
    """지원되는 금융지주사 및 파일 형식 정보"""
    console.print(Panel.fit(
        "[bold blue]IR FactBook Parser[/bold blue]\n"
        "4대 금융지주 IR FactBook 정규화 도구",
        title="정보"
    ))

    table = Table(show_header=True, header_style="bold")
    table.add_column("회사", width=15)
    table.add_column("코드", width=10)
    table.add_column("파일 패턴", width=30)
    table.add_column("시트 수", width=10)

    companies = [
        ("우리금융지주", "woori", "*woori*.xlsx", "25"),
        ("KB금융지주", "kb", "*KB*Factbook*.xlsx", "51"),
        ("신한금융지주", "shinhan", "*SFG*FactBook*.xlsx", "40"),
        ("하나금융지주", "hana", "*HFG*Databook*.xlsx", "24"),
    ]

    for name, code, pattern, sheets in companies:
        table.add_row(name, code, pattern, sheets)

    console.print(table)

    console.print("\n[bold]출력 스키마:[/bold]")
    schema_table = Table(show_header=True, header_style="bold")
    schema_table.add_column("필드", width=20)
    schema_table.add_column("타입", width=15)
    schema_table.add_column("설명", width=35)

    fields = [
        ("holding_company", "string", "금융지주사명"),
        ("entity", "string", "법인 (지주/은행/카드 등)"),
        ("category", "string", "지표 대분류"),
        ("metric_std", "string", "표준화된 지표명"),
        ("metric_original", "string", "원본 지표명"),
        ("period", "string", "기간 (YYYY-QN 형식)"),
        ("year", "int", "연도"),
        ("quarter", "int", "분기 (1-4, null=연간)"),
        ("value", "float", "수치 값"),
        ("unit", "string", "단위"),
        ("is_cumulative", "bool", "누적 여부"),
        ("is_estimate", "bool", "추정치 여부"),
    ]

    for field, type_, desc in fields:
        schema_table.add_row(field, type_, desc)

    console.print(schema_table)


def _print_validation_summary(report: ValidationReport, verbose: bool = False):
    """검증 요약 출력"""
    status = "[green]✓ 유효[/green]" if report.is_valid else "[red]✗ 오류 있음[/red]"

    console.print(f"\n검증 결과: {status}")
    console.print(f"  총 레코드: {report.total_records:,}")
    console.print(f"  유효 레코드: {report.valid_records:,}")
    console.print(f"  오류: {report.error_count}")
    console.print(f"  경고: {report.warning_count}")

    if verbose:
        console.print("\n[bold]회사별 레코드:[/bold]")
        for company, count in sorted(report.by_company.items()):
            console.print(f"  {company}: {count:,}")

        console.print(f"\n발견된 고유 지표: {len(report.metrics_found)}개")

        if report.missing_required_metrics:
            console.print("\n[yellow]필수 지표 누락:[/yellow]")
            for company, metrics in report.missing_required_metrics.items():
                console.print(f"  {company}: {', '.join(metrics)}")


def main():
    """CLI 메인 엔트리포인트"""
    cli()


if __name__ == "__main__":
    main()
