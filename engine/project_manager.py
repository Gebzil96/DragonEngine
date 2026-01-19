# engine/project_manager.py
# 🧠 ЛОГИКА: менеджер проектов (реестр, открыть проект, последний проект)
# ✅ Экспортирует ИМЕНА, которые ждёт editor/editor_app.py:
#    list_all_projects, register_project, open_last_project, save_last_project, open_project_by_path

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ============================================================
# 🟡 ИЗМЕНЯЕМЫЕ ПАРАМЕТРЫ
# ============================================================

ENGINE_ROOT_DIR = Path(__file__).resolve().parents[1]
RES_DIR = ENGINE_ROOT_DIR / "res"

PROJECTS_INDEX_FILE = RES_DIR / "projects_index.json"
LAST_PROJECT_FILE = RES_DIR / "last_project.json"

PROJECT_JSON_NAME = "project.json"


# ============================================================
# ✅ Модель (как ожидает editor_app.py)
# ============================================================

@dataclass
class ProjectInfo:
    name: str
    root: Path
    start_scene: Path


# ============================================================
# 🧩 Утилиты
# ============================================================

def _ensure_res_dir() -> None:
    RES_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    _ensure_res_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_path(p: Path) -> str:
    return str(p.resolve())


def _project_json_path(project_root: Path) -> Path:
    return project_root / PROJECT_JSON_NAME


def _project_info_from_project_json(project_root: Path) -> ProjectInfo | None:
    project_root = project_root.resolve()
    pj = _project_json_path(project_root)
    if not pj.exists():
        return None

    data = _read_json(pj, default={})
    name = data.get("name") or project_root.name
    start_scene_rel = data.get("start_scene")

    if not isinstance(name, str):
        name = project_root.name
    if not isinstance(start_scene_rel, str) or not start_scene_rel.strip():
        return None

    start_scene_abs = (project_root / start_scene_rel).resolve()
    return ProjectInfo(name=name, root=project_root, start_scene=start_scene_abs)


# ============================================================
# 📚 Реестр проектов (для "Проекты:")
# ============================================================

def _load_index_records() -> list[dict[str, Any]]:
    data = _read_json(PROJECTS_INDEX_FILE, default={"projects": []})
    items = data.get("projects", [])
    if not isinstance(items, list):
        return []
    return [x for x in items if isinstance(x, dict)]


def _save_index_records(records: list[dict[str, Any]]) -> None:
    _write_json(PROJECTS_INDEX_FILE, {"projects": records})


def register_project(project_root: Path) -> None:
    """
    ✅ UI вызывает это после создания/открытия проекта.
    """
    info = _project_info_from_project_json(project_root)
    if info is None:
        return

    records = _load_index_records()
    root_norm = _normalize_path(info.root)

    records = [r for r in records if _normalize_path(Path(r.get("root", ""))) != root_norm]
    records.insert(0, {"name": info.name, "root": root_norm})
    _save_index_records(records)


def list_all_projects() -> list[ProjectInfo]:
    """
    ✅ UI рисует "Проекты:" из этого списка.
    """
    records = _load_index_records()
    result: list[ProjectInfo] = []

    for r in records:
        root_str = r.get("root")
        if not isinstance(root_str, str) or not root_str.strip():
            continue

        info = _project_info_from_project_json(Path(root_str))
        if info is None:
            continue

        result.append(info)

    return result


# ============================================================
# 🕰 Последний проект
# ============================================================

def save_last_project(project_root: Path) -> None:
    _write_json(LAST_PROJECT_FILE, {"root": _normalize_path(project_root)})


def _load_last_project_root() -> Path | None:
    data = _read_json(LAST_PROJECT_FILE, default={})
    root = data.get("root")
    if not isinstance(root, str) or not root.strip():
        return None
    return Path(root).resolve()


# ============================================================
# 📦 Открытие проекта
# ============================================================

def open_project_by_path(project_root: Path) -> ProjectInfo | None:
    info = _project_info_from_project_json(project_root)
    if info is None:
        return None

    register_project(info.root)
    save_last_project(info.root)
    return info


def _scan_projects_dir_for_any_project(projects_dir: Path) -> ProjectInfo | None:
    projects_dir = projects_dir.resolve()
    if not projects_dir.exists():
        return None

    for child in projects_dir.iterdir():
        if not child.is_dir():
            continue
        info = _project_info_from_project_json(child)
        if info is not None:
            return info

    return None


def open_last_project(projects_dir: Path) -> ProjectInfo | None:
    # 1) last_project.json
    last_root = _load_last_project_root()
    if last_root is not None:
        info = _project_info_from_project_json(last_root)
        if info is not None:
            return info

    # 2) projects_index.json
    projects = list_all_projects()
    if projects:
        return projects[0]

    # 3) fallback: витрина projects_dir
    info = _scan_projects_dir_for_any_project(projects_dir)
    if info is not None:
        return info

    return None


# ============================================================
# ✅ EXTRA: совместимость со старым именем list_projects (если где-то осталось)
# ============================================================

def list_projects() -> list[str]:
    return [p.name for p in list_all_projects()]
