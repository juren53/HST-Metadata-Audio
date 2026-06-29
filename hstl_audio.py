#!/usr/bin/env python3
"""
hstl_audio.py — HAM (HSTL Audio Metadata) CLI entry point.

Usage examples:
  python hstl_audio.py init --data-dir "C:\\Data\\Audio_SR59" --project-name "SR59"
  python hstl_audio.py batches
  python hstl_audio.py run --step 2
  python hstl_audio.py run --steps 2-3
  python hstl_audio.py run --all
  python hstl_audio.py status
  python hstl_audio.py validate --dependencies
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on the path so sibling packages resolve.
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from __init__ import __version__, __app_name__
from config.config_manager import ConfigManager
from utils.batch_registry import BatchRegistry
from utils.path_manager import PathManager
from utils.logger import get_logger

logger = get_logger("ham-cli")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_context(config_path: Path):
    """Build a ProcessingContext from a config file."""
    from steps.base_step import ProcessingContext
    config = ConfigManager(config_path)
    data_dir = config.get("project.data_directory")
    if not data_dir:
        logger.error("project.data_directory not set in config")
        sys.exit(1)
    paths = PathManager(Path(data_dir))
    return ProcessingContext(paths, config, logger)


def _build_pipeline(context):
    """Instantiate and return a pipeline with all 5 steps registered."""
    from core.pipeline import Pipeline
    from steps.step1_csv_prep import Step1_CSVPrep
    from steps.step2_csv_validation import Step2_CSVValidation
    from steps.step3_metadata_embed import Step3_MetadataEmbed
    from steps.step4_thumbnail_embed import Step4_ThumbnailEmbed
    from steps.step5_validation import Step5_Validation

    pipeline = Pipeline(context)
    for step in [Step1_CSVPrep(), Step2_CSVValidation(), Step3_MetadataEmbed(),
                 Step4_ThumbnailEmbed(), Step5_Validation()]:
        pipeline.register_step(step)
    return pipeline


def _parse_steps(steps_str: str):
    """Parse '2', '1-3', or '2,4' into a sorted list of ints."""
    if "-" in steps_str:
        lo, hi = steps_str.split("-", 1)
        return list(range(int(lo), int(hi) + 1))
    if "," in steps_str:
        return sorted(int(s) for s in steps_str.split(","))
    return [int(steps_str)]


# ─────────────────────────────────────────────────────────────────────────────
# Sub-command handlers
# ─────────────────────────────────────────────────────────────────────────────

def cmd_init(args):
    data_dir = Path(args.data_dir).resolve()
    name = args.project_name or data_dir.name

    paths = PathManager(data_dir)
    paths.create_batch_dirs()

    config = ConfigManager()
    config.set("project.name", name)
    config.set("project.data_directory", str(data_dir))
    config.save_config(config.config_data, paths.config_path)

    registry = BatchRegistry()
    batch_id = registry.register_batch(name, str(data_dir), str(paths.config_path))

    if batch_id:
        logger.info(f"Initialized batch '{name}' (id={batch_id})")
        logger.info(f"  Data dir : {data_dir}")
        logger.info(f"  Config   : {paths.config_path}")
        logger.info(f"Place MP3s in: {paths.input_mp3_dir}")
        logger.info(f"Place CSV in : {paths.input_csv_dir}")
    else:
        logger.error("Failed to register batch")
        sys.exit(1)


def cmd_batches(args):
    registry = BatchRegistry()
    batches = registry.list_batches_summary()
    show_all = getattr(args, "all", False)
    if not show_all:
        batches = [b for b in batches if b["status"] == "active"]

    if not batches:
        print("No batches found.")
        return

    print(f"\n{'ID':<10} {'Name':<25} {'Progress':<10} {'Status':<12} {'Data Directory'}")
    print("-" * 90)
    for b in batches:
        print(f"{b['id']:<10} {b['name']:<25} {b['progress']:<10} {b['status']:<12} {b['data_directory']}")
    print()


def cmd_run(args):
    config_path = Path(args.config) if args.config else None
    if config_path is None:
        logger.error("No --config specified. Use --config <path/to/project_config.yaml>")
        sys.exit(1)

    context = _build_context(config_path)
    pipeline = _build_pipeline(context)

    if hasattr(args, "all") and args.all:
        start, end = 1, 5
    elif args.step:
        start = end = int(args.step)
    elif args.steps:
        step_nums = _parse_steps(args.steps)
        start, end = min(step_nums), max(step_nums)
    elif args.from_step:
        start, end = int(args.from_step), 5
    elif args.continue_:
        start = (context.config.get_next_step() or 1)
        end = 5
    else:
        logger.error("Specify --step, --steps, --all, --from, or --continue")
        sys.exit(1)

    dry_run = getattr(args, "dry_run", False)
    result = pipeline.run(start, end, dry_run=dry_run)
    sys.exit(0 if result.success else 1)


def cmd_status(args):
    config_path = Path(args.config) if args.config else None
    if not config_path:
        logger.error("--config required")
        sys.exit(1)
    config = ConfigManager(config_path)
    name = config.get("project.name", "Unknown")
    data_dir = config.get("project.data_directory", "")
    print(f"\nProject : {name}")
    print(f"Data dir: {data_dir}")
    print(f"Progress: {config.get_progress()}")
    print()
    for i in range(1, 6):
        done = config.get_step_status(i)
        status = "done" if done else "    "
        print(f"  [{status}] Step {i}")
    print()


def cmd_validate(args):
    if args.dependencies:
        _check_dependencies()
        return
    if args.paths and args.config:
        config = ConfigManager(Path(args.config))
        data_dir = config.get("project.data_directory")
        p = PathManager(Path(data_dir)) if data_dir else None
        if p:
            for label, path in [
                ("input/mp3",       p.input_mp3_dir),
                ("input/csv",       p.input_csv_dir),
                ("output/tmp",      p.working_dir),
                ("output/processed",p.processed_dir),
            ]:
                exists = "✓" if path.exists() else "✗"
                print(f"  [{exists}] {label}: {path}")
        return
    logger.info("Use --dependencies or --paths (with --config)")


def _check_dependencies():
    deps = {"mutagen": False, "Pillow": False, "PyYAML": False, "colorama": False, "tqdm": False}
    import_keys = {"Pillow": "PIL", "PyYAML": "yaml"}
    for pkg in deps:
        try:
            import importlib
            importlib.import_module(import_keys.get(pkg, pkg.lower()))
            deps[pkg] = True
        except ImportError:
            pass
    print("\nDependency check:")
    for pkg, ok in deps.items():
        status = "[OK]" if ok else "[X]  (pip install " + pkg + ")"
        print(f"  {status}  {pkg}")
    print()


def cmd_batch_action(args):
    registry = BatchRegistry()
    batch_id = args.batch_id
    action = args.batch_action

    batch = registry.get_batch(batch_id)
    if not batch:
        logger.error(f"Batch '{batch_id}' not found")
        sys.exit(1)

    if action == "info":
        for k, v in batch.items():
            print(f"  {k}: {v}")
    elif action == "complete":
        registry.update_batch_status(batch_id, "completed")
        logger.info(f"Batch '{batch['name']}' marked as completed")
    elif action == "archive":
        registry.update_batch_status(batch_id, "archived")
        logger.info(f"Batch '{batch['name']}' archived")
    elif action == "reactivate":
        registry.update_batch_status(batch_id, "active")
        logger.info(f"Batch '{batch['name']}' reactivated")
    elif action == "remove":
        if not getattr(args, "confirm", False):
            logger.error("Add --confirm to remove a batch from the registry")
            sys.exit(1)
        registry.unregister_batch(batch_id)
        logger.info(f"Batch '{batch['name']}' removed from registry (files preserved)")


# ─────────────────────────────────────────────────────────────────────────────
# CLI parser
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hstl_audio",
        description=f"{__app_name__} Framework CLI v{__version__}",
    )
    parser.add_argument("--config", metavar="PATH", help="Path to project_config.yaml")
    parser.add_argument("--version", action="version", version=f"HAM v{__version__}")

    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize a new batch project")
    p_init.add_argument("--data-dir", required=True, metavar="DIR")
    p_init.add_argument("--project-name", metavar="NAME")

    # batches
    p_batches = sub.add_parser("batches", help="List batch projects")
    p_batches.add_argument("--all", action="store_true", help="Include archived/completed")

    # run
    p_run = sub.add_parser("run", help="Run one or more steps")
    p_run.add_argument("--step", metavar="N", help="Run single step")
    p_run.add_argument("--steps", metavar="RANGE", help="Run steps e.g. 1-3 or 2,4")
    p_run.add_argument("--all", action="store_true", help="Run all steps")
    p_run.add_argument("--from", dest="from_step", metavar="N", help="Run from step N to 5")
    p_run.add_argument("--continue", dest="continue_", action="store_true")
    p_run.add_argument("--dry-run", action="store_true")

    # status
    sub.add_parser("status", help="Show batch status")

    # validate
    p_val = sub.add_parser("validate", help="Validation checks")
    p_val.add_argument("--dependencies", action="store_true")
    p_val.add_argument("--paths", action="store_true")
    p_val.add_argument("--step", metavar="N")

    # batch (lifecycle)
    p_batch = sub.add_parser("batch", help="Batch lifecycle management")
    p_batch.add_argument("batch_action",
                         choices=["info", "complete", "archive", "reactivate", "remove"])
    p_batch.add_argument("batch_id")
    p_batch.add_argument("--confirm", action="store_true")

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    dispatch = {
        "init":     cmd_init,
        "batches":  cmd_batches,
        "run":      cmd_run,
        "status":   cmd_status,
        "validate": cmd_validate,
        "batch":    cmd_batch_action,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(0)

    handler(args)


if __name__ == "__main__":
    main()
