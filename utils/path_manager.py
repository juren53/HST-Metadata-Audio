"""
Path management for HAM batch projects.

Each batch follows the layout:
  <data_dir>/
    input/
      mp3/          - original MP3 files (source, never modified)
      csv/          - CSV metadata file
    output/
      tmp/          - Step 3 Mutagen output; Step 4 Pillow staging
      processed/    - final tagged MP3 files
    reports/        - step reports and summaries
    logs/           - processing logs
    config/         - project-specific YAML config
"""

from pathlib import Path
from typing import Optional


class PathManager:
    """Manages all paths for a HAM batch project."""

    def __init__(self, data_dir: Path, framework_root: Optional[Path] = None):
        self.data_dir = Path(data_dir)
        self.framework_root = Path(framework_root) if framework_root else Path(__file__).parent.parent

        # --- Input ---
        self.input_dir = self.data_dir / "input"
        self.input_mp3_dir = self.input_dir / "mp3"
        self.input_csv_dir = self.input_dir / "csv"

        # --- Output ---
        self.output_dir = self.data_dir / "output"
        self.working_dir = self.output_dir / "tmp"
        self.processed_dir = self.output_dir / "processed"

        # --- Supporting ---
        self.reports_dir = self.data_dir / "reports"
        self.logs_dir = self.data_dir / "logs"
        self.config_dir = self.data_dir / "config"

        # --- Framework-level ---
        self.assets_dir = self.framework_root / "assets"
        self.registry_dir = self.framework_root / "config"

    def create_batch_dirs(self):
        """Create all required batch directories."""
        dirs = [
            self.input_mp3_dir,
            self.input_csv_dir,
            self.working_dir,
            self.processed_dir,
            self.reports_dir,
            self.logs_dir,
            self.config_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    @property
    def config_path(self) -> Path:
        return self.config_dir / "project_config.yaml"

    @property
    def thumbnail_base(self) -> Path:
        return self.assets_dir / "HST-blank-album-art.jpg"

    def find_csv_file(self) -> Optional[Path]:
        """Return the first CSV file found in input/csv/, or None."""
        csvs = list(self.input_csv_dir.glob("*.csv"))
        return csvs[0] if csvs else None

    def get_mp3_files(self):
        """Return sorted list of MP3 files in input/mp3/."""
        return sorted(self.input_mp3_dir.glob("*.mp3"))

    def __repr__(self):
        return f"PathManager(data_dir={self.data_dir})"
