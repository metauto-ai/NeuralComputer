#!/usr/bin/env python3
"""Populate predictable file system assets for command-line demos."""
from __future__ import annotations

import gzip
import io
import os
import sqlite3
import tarfile
import zipfile
from pathlib import Path
from typing import Mapping

TMP_DIR = Path("/tmp")
WORKSPACE_DIR = Path("/workspace")


def write_file(path: Path, content: str | bytes, mode: int = 0o644) -> None:
    """Create a file with the provided content, ensuring parents exist."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def shell_content(prefix: str, idx: int) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            f"# placeholder script for {prefix}_{idx}",
            "set -euo pipefail",
            f"echo '{prefix} script {idx} executed'",
        ]
    ) + "\n"


def python_content(prefix: str, idx: int) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env python3",
            "def main() -> None:",
            f"    print(\"{prefix} stats report {idx}\")",
            "",
            "if __name__ == \"__main__\":",
            "    main()",
        ]
    ) + "\n"


def text_content(prefix: str, idx: int) -> str:
    return "\n".join(
        [
            f"{prefix} sample {idx}",
            "This file ships with the Neural Computer demo fixtures.",
            "Each entry provides predictable text for tests.",
        ]
    ) + "\n"


def csv_content(prefix: str, idx: int) -> str:
    return "\n".join(
        [
            "id,value,description",
            f"{idx},42,{prefix} dataset row",
            f"{idx+1},84,{prefix} dataset row",
        ]
    ) + "\n"


def md_content(prefix: str, idx: int) -> str:
    return "\n".join(
        [
            f"# {prefix.title()} notebook {idx}",
            "",
            "This markdown file is available for editor demos.",
            "- line 1",
            "- line 2",
        ]
    ) + "\n"


def log_content(prefix: str, idx: int) -> str:
    return "\n".join(
        [
            f"2024-01-01T00:00:0{idx % 10}Z INFO start {prefix}_{idx}",
            f"2024-01-01T00:00:1{idx % 10}Z INFO completed {prefix}_{idx}",
        ]
    ) + "\n"


def create_range(prefix: str, ext: str, start: int, end: int, mode: int, content_fn) -> None:
    for idx in range(start, end + 1):
        path = TMP_DIR / f"{prefix}_{idx}.{ext}"
        write_file(path, content_fn(prefix, idx), mode)


STATIC_TEXT_FILES = {
    "batch3_log.txt": "Batch 3 processing log placeholder.\n",
    "batch_log.txt": "Aggregated batch log placeholder.\n",
    "less_batch3.txt": "Less command fixtures for batch 3.\n",
    "less_batch.txt": "Less command fixtures for combined batch.\n",
    "session_log.txt": "General session log placeholder.\n",
    "session_notes.txt": "Notes recorded during a troubleshooting session.\n",
    "scrollback.txt": "Scrollback capture placeholder.\n",
    "todo_batch.txt": "Todo entries for batch scripts.\n",
    "vim_buffer.txt": "Vim buffer sample for batch 3.\n",
}

# Compatibility switch: set NC_INCLUDE_VHS_FIXTURES=1 to create legacy names.
INCLUDE_VHS_FIXTURES = os.environ.get("NC_INCLUDE_VHS_FIXTURES", "1").lower() in {
    "1",
    "true",
    "yes",
}

LEGACY_STATIC_TEXT_FILES = {
    "vhs_batch3_log.txt": "Batch 3 processing log placeholder.\n",
    "vhs_batch_log.txt": "Aggregated batch log placeholder.\n",
    "vhs_less_b3.txt": "Less command fixtures for batch 3.\n",
    "vhs_less_batch.txt": "Less command fixtures for combined batch.\n",
    "vhs_log.txt": "General session log placeholder.\n",
    "vhs_notes.txt": "Notes recorded during a troubleshooting session.\n",
    "vhs_scroll.txt": "Scrollback capture placeholder.\n",
    "vhs_todo_batch.txt": "Todo entries for batch scripts.\n",
    "vhs_vim_b3.txt": "Vim buffer sample for batch 3.\n",
}


WORKSPACE_FILES: dict[str, tuple[str | bytes, int]] = {
    "README.md": (
        "# Neural Computer Fixtures\n\n"
        "This workspace contains placeholder assets for terminal demos.\n",
        0o644,
    ),
    "access.log": (
        "2024-01-01T00:00:00Z GET /index.html 200\n"
        "2024-01-01T00:01:00Z POST /login 302\n",
        0o644,
    ),
    "app.js": ("console.log('Neural Computer Node demo');\n", 0o644),
    "backup.txt": ("Nightly backup manifest\n", 0o644),
    "binary.dat": (bytes(range(16)), 0o644),
    "config.conf": ("[main]\noption=true\n", 0o644),
    "config.py": ("VALUE = 'config placeholder'\n", 0o644),
    "config.txt": ("configuration placeholder\n", 0o644),
    "config.yaml": ("setting: value\n", 0o644),
    "config_backup.txt": ("backup configuration snapshot\n", 0o644),
    "data.bin": (b"\x00\x01\x02\x03" * 8, 0o644),
    "data.csv": ("id,value\n1,42\n2,84\n", 0o644),
    "data.json": ("{\"status\": \"ok\", \"items\": 3}\n", 0o644),
    "data.log": (
        "2024-01-01T00:00:00Z INFO start pipeline\n"
        "2024-01-01T00:00:05Z INFO processed batch\n",
        0o644,
    ),
    "data.txt": ("Dataset summary for shell exercises.\n", 0o644),
    "desination.txt": ("Typo destination placeholder\n", 0o644),
    "document.js": ("console.log('document placeholder');\n", 0o644),
    "document.py": ("print('document placeholder')\n", 0o644),
    "document.txt": ("General document text sample.\n", 0o644),
    "document_backup.js": ("console.log('backup document');\n", 0o644),
    "document_backup.py": ("print('backup document')\n", 0o644),
    "document_backup.txt": ("Backup document text sample.\n", 0o644),
    "overview.md": (
        "# Demo Overview\n\n"
        "This markdown file explains the goal of the sample workspace.\n",
        0o644,
    ),
    "error.log": (
        "2024-01-01T00:02:00Z ERROR disk full\n"
        "2024-01-01T00:02:30Z WARN cleanup pending\n",
        0o644,
    ),
    "fiile.txt": ("Intentionally misspelled file placeholder.\n", 0o644),
    "file.txt": ("Primary sample file for cp/mv demos.\n", 0o644),
    "file.html": ("<html><body>Placeholder HTML file</body></html>\n", 0o644),
    "file1.txt": ("File one content\n", 0o644),
    "file2.txt": ("File two content\n", 0o644),
    "hello.txt": ("Hello from the fixtures!\n", 0o644),
    "large_file.txt": (
        "".join(f"Line {i:03d}\n" for i in range(1, 51)),
        0o644,
    ),
    "lines.txt": ("first line\nsecond line\nthird line\n", 0o644),
    "live.log": ("2024-01-01T00:05:00Z INFO live update\n", 0o644),
    "log.txt": ("General log output\n", 0o644),
    "names.txt": ("Ada\nEdsger\nGrace\n", 0o644),
    "new.txt": ("new content\n", 0o644),
    "new_config.txt": ("new configuration version\n", 0o644),
    "new_document.js": ("console.log('new document');\n", 0o644),
    "new_document.py": ("print('new document')\n", 0o644),
    "new_document.txt": ("New document text placeholder.\n", 0o644),
    "newfile.txt": ("new file placeholder\n", 0o644),
    "note.txt": ("single note entry\n", 0o644),
    "notes.txt": ("- note 1\n- note 2\n", 0o644),
    "numbers.txt": ("1\n2\n3\n4\n5\n", 0o644),
    "project-plan.txt": (
        "Milestones:\n- gather logs\n- review metrics\n- prepare summary\n",
        0o644,
    ),
    "old.txt": ("legacy text\n", 0o644),
    "old_config.txt": ("legacy config\n", 0o644),
    "old_document.js": ("console.log('old document');\n", 0o644),
    "old_document.py": ("print('old document')\n", 0o644),
    "old_document.txt": ("Old document text placeholder.\n", 0o644),
    "oldfile.txt": ("old file placeholder\n", 0o644),
    "package.json": ("{\n  \"name\": \"fixture\",\n  \"version\": \"1.0.0\"\n}\n", 0o644),
    "readonly.txt": ("Read-only sample file.\n", 0o444),
    "script.py": ("print('script placeholder')\n", 0o644),
    "script.sh": ("#!/usr/bin/env bash\necho 'script placeholder'\n", 0o644),
    "setup.py": ("from setuptools import setup\nsetup(name='fixture', version='0.0.1')\n", 0o644),
    "status.md": (
        "## Status\n\nEverything is operating within expected parameters.\n",
        0o644,
    ),
    "simple.txt": ("simple text\n", 0o644),
    "source.txt": ("source reference text\n", 0o644),
    "table.tsv": ("name\tvalue\nfoo\t1\nbar\t2\n", 0o644),
    "test.txt": ("test data\n", 0o644),
    "output.html": ("<html><body>Download placeholder</body></html>\n", 0o644),
    "file.gz": (gzip.compress(b"Compressed placeholder content\n"), 0o644),
    "unwanted.txt": ("temporary file slated for removal\n", 0o644),
    "words.txt": ("alpha beta gamma delta\n", 0o644),
}


DIRECTORY_NAMES = [
    "archive",
    "archive1",
    "archive2",
    "archive_archive",
    "archive_backup",
    "backup",
    "backup1",
    "backup2",
    "backup_archive",
    "backup_backup",
    "documents",
    "documents1",
    "documents2",
    "documents_archive",
    "documents_backup",
    "folder",
    "folder1",
    "folder2",
]


TMP_GLOB_FILES = {
    "session.tmp": "temporary session data\n",
    "cache.tmp": "cached computation\n",
}


ZIP_ARCHIVES: Mapping[str, Mapping[str, str]] = {
    "archive.zip": {
        "docs/readme.txt": "Archive zip document\n",
        "docs/notes.txt": "Notes inside archive.zip\n",
    },
    "file.zip": {
        "data/sample.txt": "Sample inside file.zip\n",
        "data/metrics.csv": "id,value\n1,10\n2,20\n",
    },
    "backup.zip": {
        "snapshots/state.txt": "Snapshot data\n",
    },
}


TAR_ARCHIVES: Mapping[str, tuple[str, Mapping[str, str]]] = {
    "archive.tar": (
        "w",
        {
            "reports/summary.txt": "Archive TAR summary\n",
            "reports/data.csv": "id,value\n1,100\n2,200\n",
        },
    ),
    "file.tar.gz": (
        "w:gz",
        {
            "package/README.md": "Compressed package readme\n",
            "package/script.sh": "#!/usr/bin/env bash\necho compressed\n",
        },
    ),
    "backup.tar.gz": (
        "w:gz",
        {
            "snapshot/state.json": "{\"state\": \"ok\"}\n",
        },
    ),
}


def create_tmp_assets() -> None:
    create_range("adv2_less", "txt", 1, 100, 0o644, text_content)
    create_range("adv2_pipeline", "csv", 1, 100, 0o644, csv_content)
    create_range("adv2_script", "sh", 1, 100, 0o755, shell_content)
    create_range("adv2_script", "log", 1, 100, 0o644, log_content)
    create_range("adv2_stats", "py", 1, 100, 0o755, python_content)
    create_range("adv2_vim", "md", 1, 100, 0o644, md_content)

    create_range("demo_less", "txt", 1, 80, 0o644, text_content)
    create_range("demo_pipeline", "csv", 1, 80, 0o644, csv_content)
    create_range("demo_script", "sh", 1, 80, 0o755, shell_content)
    create_range("demo_script", "log", 1, 80, 0o644, log_content)
    create_range("demo_stats", "py", 1, 80, 0o755, python_content)
    create_range("demo_notes", "md", 1, 80, 0o644, md_content)

    if INCLUDE_VHS_FIXTURES:
        create_range("vhs_less_adv", "txt", 1, 100, 0o644, text_content)
        create_range("vhs_pipeline", "csv", 1, 100, 0o644, csv_content)
        create_range("vhs_script", "sh", 1, 120, 0o755, shell_content)
        create_range("vhs_script", "log", 1, 120, 0o644, log_content)
        create_range("vhs_stats", "py", 1, 100, 0o755, python_content)
        create_range("vhs_vim_adv", "md", 1, 100, 0o644, md_content)

    for name, content in STATIC_TEXT_FILES.items():
        write_file(TMP_DIR / name, content, 0o644)

    if INCLUDE_VHS_FIXTURES:
        for name, content in LEGACY_STATIC_TEXT_FILES.items():
            write_file(TMP_DIR / name, content, 0o644)

    for name, content in TMP_GLOB_FILES.items():
        write_file(TMP_DIR / name, content, 0o644)


def create_workspace_directories() -> None:
    for dirname in DIRECTORY_NAMES:
        directory = WORKSPACE_DIR / dirname
        directory.mkdir(parents=True, exist_ok=True)
        placeholder = directory / "placeholder.txt"
        write_file(
            placeholder,
            f"Placeholder content for {dirname}.\n",
            0o644,
        )


def create_workspace_archives() -> None:
    for archive_name, members in ZIP_ARCHIVES.items():
        archive_path = WORKSPACE_DIR / archive_name
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, "w") as zf:
            for member, payload in members.items():
                zf.writestr(member, payload)

    for archive_name, (mode, members) in TAR_ARCHIVES.items():
        archive_path = WORKSPACE_DIR / archive_name
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path, mode) as tar:
            for member, payload in members.items():
                data = payload.encode("utf-8")
                info = tarfile.TarInfo(name=member)
                info.size = len(data)
                if member.endswith(".sh"):
                    info.mode = 0o755
                else:
                    info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))


def create_workspace_assets() -> None:
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    for name, (content, mode) in WORKSPACE_FILES.items():
        write_file(WORKSPACE_DIR / name, content, mode)

    # Additional files to satisfy glob patterns.
    glob_samples = {
        "app.log": "App log entry\n",
        "system.log": "System log entry\n",
        "report.txt": "Report text\n",
        "analysis.txt": "Analysis text\n",
        "module.py": "print('module placeholder')\n",
    }
    for name, content in glob_samples.items():
        write_file(WORKSPACE_DIR / name, content, 0o644)

    special_dirs = {
        WORKSPACE_DIR / "Doc": {"overview.txt": "Document repository overview\n"},
        WORKSPACE_DIR / "CLI": {},
        WORKSPACE_DIR / "CLI/demo-fixtures": {
            "README.md": "Command-line demo placeholder directory\n"
        },
    }

    for directory, files in special_dirs.items():
        directory.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            write_file(directory / filename, content, 0o644)

    create_workspace_directories()

    # Ensure nested directory for mkdir -p demos exists.
    nested = WORKSPACE_DIR / "path/to/dir"
    nested.mkdir(parents=True, exist_ok=True)
    write_file(nested / "readme.txt", "Nested directory placeholder\n", 0o644)

    # Provide initial .tmp files that rm *.tmp can remove safely.
    for name in ["session.tmp", "cache.tmp", "build.tmp"]:
        write_file(WORKSPACE_DIR / name, "temporary placeholder\n", 0o644)

    create_workspace_archives()

    # SQLite database for `sqlite3 database.db` demos.
    db_path = WORKSPACE_DIR / "database.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, message TEXT)")
        conn.execute(
            "INSERT OR IGNORE INTO logs(id, message) VALUES (1, 'Initial log entry')"
        )


def create_system_assets() -> None:
    system_log = Path("/var/log/system.log")
    write_file(system_log, "2024-01-01T00:00:00Z INFO system boot\n", 0o644)


def main() -> None:
    create_tmp_assets()
    create_workspace_assets()
    create_system_assets()


if __name__ == "__main__":
    main()
