"""
Default settings for HAM (HSTL Audio Metadata) Framework.
"""

DEFAULT_SETTINGS = {
    "project": {
        "name": "",
        "created": "",
        "data_directory": "",
    },
    "steps_completed": {
        "step1": False,
        "step2": False,
        "step3": False,
        "step4": False,
        "step5": False,
    },
    "step_configurations": {
        "step2": {
            "strict_date_validation": True,
        },
        "step3": {
            "id3v2_version": 3,
        },
        "step4": {
            "thumbnail_font_size": 24,
            "thumbnail_font_color": "yellow",
            "thumbnail_base_image": "assets/HST-thumbnail-c.png",
        },
        "step5": {
            "spot_check_count": 3,
        },
    },
    "validation": {
        "strict_mode": True,
        "auto_backup": True,
    },
    "logging": {
        "level": "INFO",
        "console_output": True,
    },
}

REQUIRED_CSV_COLUMNS = [
    "title",
    "Accession Number",
    "Date",
    "Restrictions",
    "Description",
    "Place",
    "Speakers",
    "Production and Copyright",
]
