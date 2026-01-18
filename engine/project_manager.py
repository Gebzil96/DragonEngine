from pathlib import Path
import json
from typing import Optional, List


class ProjectInfo:
    """🧠 ЛОГИКА: структура данных проекта (чтобы editor_app мог открыть стартовую сцену)."""
    def __init__(self, name: str, root: Path, project_json: Path, start_scene: Path):
        self.name = name
        self.root = root
        self.project_json = project_json
        self.start_scene = start_scene


# 🧠 ЛОГИКА: файл, где храним путь к последнему проекту (лежит рядом с этим файлом)
LAST_PROJECT_FILE = Path(__file__).resolve().parent / "last_project.json"

# 🧠 ЛОГИКА: файл-реестр ВСЕХ проектов (пути могут быть где угодно на диске)
PROJECTS_INDEX_FILE = Path(__file__).resolve().parent / "projects_index.json"


def ensure_projects_dir(projects_dir: Path):
    """🧠 ЛОГИКА: гарантируем существование папки проектов (витрина внутри DragonEngine)."""
    if not projects_dir.exists():
        projects_dir.mkdir(parents=True)


def list_projects(projects_dir: Path) -> List[Path]:
    """
    🧠 ЛОГИКА: список проектов ТОЛЬКО в projects_dir (витрина).
    Это не все проекты на диске, а только те, что лежат в этой папке.
    """
    ensure_projects_dir(projects_dir)
    return sorted([p for p in projects_dir.iterdir() if p.is_dir()], key=lambda p: p.name.lower())


# =========================
# ✅ РЕЕСТР ВСЕХ ПРОЕКТОВ
# =========================

def _load_projects_index() -> List[Path]:
    """🧠 ЛОГИКА: читаем projects_index.json и возвращаем существующие пути."""
    if not PROJECTS_INDEX_FILE.exists():
        return []

    try:
        with open(PROJECTS_INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw = data.get("projects", [])
        paths: List[Path] = []

        for p in raw:
            try:
                pp = Path(p)
                if pp.exists():
                    paths.append(pp)
            except Exception:
                continue

        # 🧠 ЛОГИКА: удалим дубликаты (сохранив порядок)
        uniq: List[Path] = []
        seen = set()
        for p in paths:
            key = str(p).lower()
            if key not in seen:
                uniq.append(p)
                seen.add(key)

        return uniq
    except Exception:
        return []


def _save_projects_index(paths: List[Path]):
    """🧠 ЛОГИКА: сохраняем список путей проектов в projects_index.json."""
    data = {"projects": [str(p) for p in paths]}
    with open(PROJECTS_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def register_project(project_root: Path):
    """🧠 ЛОГИКА: добавляет проект в общий список (неважно где он лежит)."""
    project_root = Path(project_root)

    paths = _load_projects_index()

    # 🧠 ЛОГИКА: проверка дубликата по lower()
    root_key = str(project_root).lower()
    keys = {str(p).lower() for p in paths}

    if root_key not in keys and project_root.exists():
        paths.append(project_root)
        _save_projects_index(paths)


def list_all_projects() -> List[Path]:
    """🧠 ЛОГИКА: возвращает ВСЕ известные проекты (из реестра)."""
    return _load_projects_index()


# =========================
# ✅ LAST PROJECT
# =========================

def save_last_project(project_root: Path):
    """🧠 ЛОГИКА: сохраняем путь к последнему проекту (работает для проектов в ЛЮБОЙ папке)."""
    data = {"last_project": str(Path(project_root))}
    with open(LAST_PROJECT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_last_project_path() -> Optional[Path]:
    """🧠 ЛОГИКА: читаем путь к последнему проекту из файла."""
    if not LAST_PROJECT_FILE.exists():
        return None

    try:
        with open(LAST_PROJECT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        p = data.get("last_project")
        if not p:
            return None

        pp = Path(p)
        return pp
    except Exception:
        return None


# =========================
# ✅ OPEN PROJECT
# =========================

def open_project_by_path(project_root: Path) -> Optional[ProjectInfo]:
    """🧠 ЛОГИКА: открывает проект по точному пути к папке проекта."""
    project_root = Path(project_root)
    project_json_path = project_root / "project.json"
    if not project_json_path.exists():
        return None

    with open(project_json_path, "r", encoding="utf-8") as f:
        project_data = json.load(f)

    start_scene_rel = Path(project_data.get("start_scene", "scenes/main.scene.json"))

    return ProjectInfo(
        name=project_data.get("name", project_root.name),
        root=project_root,
        project_json=project_json_path,
        start_scene=project_root / start_scene_rel
    )


def open_last_project(projects_dir: Optional[Path] = None) -> Optional[ProjectInfo]:
    """
    🧠 ЛОГИКА:
    1) Сначала пытаемся открыть last_project.json (самый надёжный способ)
    2) Если его нет — fallback: ищем последний изменённый проект в projects_dir (витрина)
    """
    # 1) last_project.json
    last_path = load_last_project_path()
    if last_path:
        info = open_project_by_path(last_path)
        if info is not None:
            return info

    # 2) fallback по projects_dir
    if projects_dir is None:
        return None

    projects_dir = Path(projects_dir)
    projects = list_projects(projects_dir)
    if not projects:
        return None

    last = max(projects, key=lambda p: p.stat().st_mtime)
    return open_project_by_path(last)
