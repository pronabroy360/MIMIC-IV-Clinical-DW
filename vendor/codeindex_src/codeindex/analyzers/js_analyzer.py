"""JavaScript / TypeScript / Vue repository analyzer (regex-based)."""
import json
import re
from pathlib import Path

from .base import load_gitignore_patterns, is_ignored, is_skip_dir, dir_group

JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue"}

CONFIG_STEMS = {
    "config", "settings", "constants", "env", "configuration", "conf",
    "vite.config", "webpack.config", "babel.config", "jest.config",
    "vitest.config", "tailwind.config", "next.config", "nuxt.config",
    "svelte.config", "astro.config", "rollup.config", "esbuild.config",
}

# Path-based heuristics
_ROUTE_DIRS = {"pages", "routes", "views", "screens"}
_NEXT_APP_FILES = {"page", "layout", "loading", "error", "not-found", "template", "route"}
_STORE_DIRS = {"store", "stores", "state", "redux", "slices", "atoms", "contexts", "context"}
_STORE_STEMS = {"store", "slice", "reducer", "context", "atom", "provider", "actions", "mutations"}

# Frameworks detected by package.json dependency names
FRAMEWORK_SIGNALS = [
    ("next",           "next"),
    ("nuxt",           "nuxt"),
    ("@sveltejs/kit",  "sveltekit"),
    ("svelte",         "svelte"),
    ("@angular/core",  "angular"),
    ("gatsby",         "gatsby"),
    ("remix",          "remix"),
    ("astro",          "astro"),
    ("react",          "react"),
    ("vue",            "vue"),
]

# ── Import extraction regexes ─────────────────────────────────────────────────
# Matches: import ... from 'X' / import 'X' / export ... from 'X'
_IMPORT_FROM_RE = re.compile(
    r"""(?:^|;|\})\s*(?:import|export)\s+(?:[^'"\n]*?\s+from\s+)?['"]([^'"]+)['"]""",
    re.MULTILINE,
)
# Matches: require('X') / require("X")
_REQUIRE_RE = re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""")
# Matches: import('X') dynamic imports
_DYN_IMPORT_RE = re.compile(r"""(?<!\w)import\s*\(\s*['"]([^'"]+)['"]\s*\)""")

# ── Component / hook / store detection regexes ────────────────────────────────
# JSX return: return ( <... or return <...
_JSX_RETURN_RE = re.compile(r'return\s*\(?[\s\n]*<[A-Za-z/]', re.MULTILINE)
# PascalCase JSX element usage (strong signal of component file)
_JSX_PASCAL_RE = re.compile(r'<[A-Z][A-Za-z]+[\s/>]')
# export function/const useXxx or export default function useXxx
_HOOK_EXPORT_RE = re.compile(r'export\s+(?:default\s+)?(?:const|function)\s+use[A-Z]')
# Context API
_CONTEXT_RE = re.compile(r'createContext\s*[(<]')
# State management: Redux, Zustand, Jotai, Svelte stores
_STORE_RE = re.compile(
    r'createSlice\s*\(|createStore\s*\(|atom\s*\(|writable\s*\('
    r"|readable\s*\(|create\s*\(\s*\((?:set|get)\)"
)

# ── Vue SFC extraction ────────────────────────────────────────────────────────
_VUE_SCRIPT_RE = re.compile(r'<script(?:\s[^>]*)?>(.+?)</script>', re.DOTALL | re.IGNORECASE)


def collect_files(root: Path, patterns: list):
    seen = set()
    for ext in JS_EXTENSIONS:
        for p in root.rglob(f"*{ext}"):
            if is_skip_dir(p) or is_ignored(p, root, patterns):
                continue
            seen.add(p)
    return sorted(seen)


def read_package_json(root: Path):
    """Returns (all_dep_names, detected_framework, package_manager)."""
    pkg_file = root / "package.json"
    if not pkg_file.exists():
        return set(), None, None

    try:
        pkg = json.loads(pkg_file.read_text(errors="replace"))
    except (json.JSONDecodeError, OSError):
        return set(), None, None

    all_deps = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        all_deps.update(pkg.get(key, {}).keys())

    framework = next(
        (fw for signal, fw in FRAMEWORK_SIGNALS if signal in all_deps),
        None,
    )

    if (root / "pnpm-lock.yaml").exists():
        pm = "pnpm"
    elif (root / "yarn.lock").exists():
        pm = "yarn"
    elif (root / "package-lock.json").exists():
        pm = "npm"
    else:
        pm = None

    return all_deps, framework, pm


def detect_language(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".vue":
        return "vue"
    if suffix in {".ts", ".tsx"}:
        return "typescript"
    return "javascript"


def node_type(path: Path, source: str = "") -> str:
    """Classify a file into a semantic node type using path + content heuristics."""
    stem = path.stem.lower()
    ext = path.suffix.lower()
    parts_lower = [p.lower() for p in path.parts]

    # ── Config files ──────────────────────────────────────────────────────────
    if stem in CONFIG_STEMS:
        return "config"
    for name in CONFIG_STEMS:
        if stem.endswith(f".{name}"):
            return "config"

    # ── Vue SFC → always a component ─────────────────────────────────────────
    if ext == ".vue":
        return "component"

    # ── Route detection (by directory convention) ────────────────────────────
    if any(p in _ROUTE_DIRS for p in parts_lower):
        return "route"
    # Next.js app router special file names
    if "app" in parts_lower and ext in {".jsx", ".tsx"} and stem in _NEXT_APP_FILES:
        return "route"

    # ── Store / state management detection ───────────────────────────────────
    if any(p in _STORE_DIRS for p in parts_lower):
        return "store"
    if any(kw in stem for kw in _STORE_STEMS):
        return "store"
    if source and (_CONTEXT_RE.search(source) or _STORE_RE.search(source)):
        return "store"

    # ── Hook detection ────────────────────────────────────────────────────────
    # Filename starts with "use" + capital letter (e.g., useAuth.ts)
    if stem.startswith("use") and len(stem) > 3 and stem[3].isupper():
        return "hook"
    if source and _HOOK_EXPORT_RE.search(source):
        return "hook"

    # ── Component detection (JSX files or files containing JSX) ─────────────
    if ext in {".jsx", ".tsx"}:
        return "component"
    # .js/.ts files that contain JSX syntax
    if source and (_JSX_RETURN_RE.search(source) or _JSX_PASCAL_RE.search(source)):
        return "component"

    return "module"


def extract_imports(source: str):
    """Return deduplicated list of module strings referenced in the file."""
    seen = set()
    mods = []
    for pattern in (_IMPORT_FROM_RE, _REQUIRE_RE, _DYN_IMPORT_RE):
        for m in pattern.finditer(source):
            mod = m.group(1)
            if mod not in seen:
                seen.add(mod)
                mods.append(mod)
    return mods


def extract_vue_imports(source: str):
    """Extract imports from the <script> block of a Vue SFC."""
    match = _VUE_SCRIPT_RE.search(source)
    if not match:
        return []
    return extract_imports(match.group(1))


def resolve_internal(mod: str, file_path: Path, root: Path, all_files: set):
    """Resolve a relative/absolute module path to a repo-relative file path."""
    if not (mod.startswith(".") or mod.startswith("/")):
        return None  # Package import — handled separately

    base = file_path.parent
    raw = (base / mod).resolve()

    # Try adding common JS/TS/Vue extensions if none present
    all_extensions = list(JS_EXTENSIONS) + [".css", ".scss", ".sass", ".less"]
    candidates = [raw]
    if not raw.suffix:
        candidates = [raw.with_suffix(ext) for ext in all_extensions] + candidates

    for candidate in candidates:
        try:
            rel = str(candidate.relative_to(root))
            if rel in all_files:
                return rel
        except ValueError:
            continue

    # Try as directory index
    for idx_name in ("index.js", "index.ts", "index.jsx", "index.tsx", "index.vue"):
        candidate = raw / idx_name
        try:
            rel = str(candidate.relative_to(root))
            if rel in all_files:
                return rel
        except ValueError:
            continue

    return None


def package_name(mod: str) -> str:
    """Extract the top-level package name (handles @scope/pkg paths)."""
    if mod.startswith("@"):
        parts = mod.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else mod
    return mod.split("/")[0]


def analyze(root: Path, group_map: dict):
    """
    Returns (nodes, external_nodes, links_map, meta).
    links_map keys are (source_rel, target_rel) tuples.
    """
    patterns = load_gitignore_patterns(root)
    js_files = collect_files(root, patterns)

    if not js_files:
        return [], [], {}, {"total_files": 0, "total_loc": 0}

    _ext_deps, framework, package_manager = read_package_json(root)

    all_rel = {str(f.relative_to(root)) for f in js_files}
    # Also include CSS/stylesheet files so JS→CSS import links can be resolved
    _css_exts = {".css", ".scss", ".sass", ".less", ".styl"}
    for _ext in _css_exts:
        for _p in root.rglob(f"*{_ext}"):
            if not is_skip_dir(_p) and not is_ignored(_p, root, patterns):
                all_rel.add(str(_p.relative_to(root)))
    nodes = []
    links_map = {}
    external_nodes = {}
    total_loc = 0

    for f in js_files:
        rel = str(f.relative_to(root))
        try:
            source = f.read_text(errors="replace")
        except OSError:
            continue

        loc = source.count("\n") + 1
        total_loc += loc

        lang = detect_language(f)
        ntype = node_type(f, source)

        # For Vue SFCs, extract imports from the script block only
        mods = extract_vue_imports(source) if f.suffix == ".vue" else extract_imports(source)

        nodes.append({
            "id": rel,
            "type": ntype,
            "language": lang,
            "framework": framework,
            "size": loc,
            "loc": loc,
            "group": dir_group(f, root, group_map),
            "imports": len(mods),
        })

        for mod in mods:
            internal = resolve_internal(mod, f, root, all_rel)
            if internal:
                key = (rel, internal)
                links_map[key] = links_map.get(key, 0) + 1
            elif not mod.startswith(".") and not mod.startswith("/"):
                pkg = package_name(mod)
                if pkg not in external_nodes:
                    external_nodes[pkg] = {
                        "id": pkg,
                        "type": "import",
                        "language": lang,
                        "size": 40,
                        "loc": 0,
                        "group": 9000,
                        "imports": 0,
                    }
                key = (rel, pkg)
                links_map[key] = links_map.get(key, 0) + 1

    meta = {
        "total_files": len(js_files),
        "total_loc": total_loc,
    }
    if framework:
        meta["framework"] = framework
    if package_manager:
        meta["packageManager"] = package_manager

    return nodes, list(external_nodes.values()), links_map, meta
