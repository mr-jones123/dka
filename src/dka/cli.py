from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dka import __version__
from dka.adapters import export_hf, import_pld
from dka.core import build, init_project, validate

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dka", description="Dataset kit assistant for speech datasets"
    )
    parser.add_argument("--version", action="version", version=f"dka {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="create a dka dataset folder")
    init_p.add_argument("path", nargs="?", default=".")

    val_p = sub.add_parser("validate", help="check raw metadata and audio")
    val_p.add_argument("path", nargs="?", default=".")

    build_p = sub.add_parser(
        "build", help="prepare metadata, splits, reports, and dataset card"
    )
    build_p.add_argument("path", nargs="?", default=".")
    build_p.add_argument("--preset", choices=["pld"])
    build_p.add_argument("--out")
    build_p.add_argument("--limit", type=int)
    build_p.add_argument("--hf", action="store_true")

    export_p = sub.add_parser("export", help="export processed data for training")
    export_p.add_argument("path", nargs="?", default=".")
    export_p.add_argument("--format", choices=["hf"], default="hf")

    pld_p = sub.add_parser("import-pld", help="import a UP-DSP-PLD language folder")
    pld_p.add_argument("source")
    pld_p.add_argument("target")
    pld_p.add_argument("--limit", type=int)

    args = parser.parse_args()

    if args.command == "init":
        root = Path(args.path).resolve()
        init_project(root)
        console.print(
            Panel.fit(
                f"Created dka dataset at [bold]{root}[/bold]",
                title="dka init",
                border_style="green",
            )
        )
        return

    if args.command == "validate":
        root = Path(args.path).resolve()
        rows, flags = validate(root)
        _print_validate(rows, flags)
        return

    if args.command == "build":
        root = Path(args.path).resolve()
        if args.preset == "pld":
            if not args.out:
                parser.error("build --preset pld requires --out")
            root = Path(args.out).resolve()
            count = import_pld(Path(args.path).resolve(), root, args.limit)
            console.print(f"[green]Imported {count} PLD rows.[/green]")
        result = build(root)
        _print_build(result.stats, result.flags)
        if args.hf:
            out = export_hf(root)
            console.print(f"[green]Exported hf dataset to {out}[/green]")
        return

    if args.command == "export":
        root = Path(args.path).resolve()
        out = export_hf(root)
        console.print(
            Panel.fit(
                f"Exported [bold]{args.format}[/bold] dataset to [bold]{out}[/bold]",
                title="dka export",
                border_style="green",
            )
        )
        return

    if args.command == "import-pld":
        count = import_pld(
            Path(args.source).resolve(), Path(args.target).resolve(), args.limit
        )
        console.print(
            Panel.fit(
                f"Imported [bold]{count}[/bold] PLD rows to [bold]{Path(args.target).resolve()}[/bold]",
                title="dka import-pld",
                border_style="green",
            )
        )
        return


def _print_validate(rows: list[dict[str, str]], flags: dict[str, int]) -> None:
    table = Table(title="Validation")
    table.add_column("Check")
    table.add_column("Result", justify="right")
    table.add_row("Rows", str(len(rows)))
    if flags:
        for key, value in sorted(flags.items()):
            table.add_row(key, f"[yellow]{value}[/yellow]")
    else:
        table.add_row("Blocking issues", "[green]0[/green]")
    console.print(table)


def _print_build(stats: dict[str, object], flags: dict[str, int]) -> None:
    table = Table(title="dka build complete")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Samples", str(stats["total_samples"]))
    table.add_row("Hours", str(stats["total_hours"]))
    table.add_row("Speakers", str(stats["speakers"]))
    table.add_row("Flagged samples", str(stats["flagged_samples"]))
    console.print(table)

    if flags:
        flag_table = Table(title="Quality flags")
        flag_table.add_column("Flag")
        flag_table.add_column("Count", justify="right")
        for key, value in sorted(flags.items()):
            flag_table.add_row(key, str(value))
        console.print(flag_table)
    else:
        console.print("[green]No quality flags.[/green]")


if __name__ == "__main__":
    main()
