"""Interactive setup command: `efleetplan-start`.

Copies the bundled config templates (env.yaml, run configs, and the
predefined vehicle/schedule/company/infrastructure library) to a
folder of the user's choosing, ready to edit and pass to
`load_scheduler_config()` / `load_opt_config()`.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Iterator


def _iter_template_files() -> Iterator[tuple[resources.abc.Traversable, str]]:
    root = resources.files("efleetplan") / "_config_templates"

    def walk(node: resources.abc.Traversable, prefix: str):
        for entry in node.iterdir():
            rel = f"{prefix}{entry.name}"
            if entry.is_dir():
                yield from walk(entry, f"{rel}/")
            else:
                yield entry, rel

    yield from walk(root, "")


def main() -> None:
    raw = input("Where should the config folder be created? [./config]: ").strip()
    dest = Path(raw) if raw else Path("config")

    if dest.exists() and any(dest.iterdir()):
        answer = input(f"'{dest}' already exists and is not empty. Overwrite files? [y/N]: ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    for src_file, rel_path in _iter_template_files():
        target = dest / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(src_file.read_bytes())

    print(f"\nConfig templates created at: {dest.resolve()}")
    print("Edit the YAML files there, then point load_scheduler_config() / load_opt_config() at them.")


if __name__ == "__main__":
    main()
