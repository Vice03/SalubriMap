#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Module « Assistant » : trouver un modèle de langue local, ou en obtenir un adapté à la machine (avec accord).

Appelé par run/start.sh et run/start.bat quand SALUBRI_ASSISTANT_ENABLED=true dans .env. Bibliothèque standard
seulement : il tourne avant toute installation. Quoi qu'il arrive ici, le reste de Salubri démarre.

    python run/llm_detect.py                 # détection, et proposition de téléchargement si rien n'est trouvé
    python run/llm_detect.py --llm=no        # jamais de téléchargement
    python run/llm_detect.py --llm=yes       # télécharger sans demander (si la machine le permet)
    python run/llm_detect.py --dry-run       # tout afficher, ne rien écrire ni télécharger
    python run/llm_detect.py --doctor        # une ligne d'état pour run/doctor

Ordre : SALUBRI_LLM_URL déjà réglé → serveurs locaux habituels (Ollama, LM Studio, llama.cpp, Jan, LocalAI, vLLM)
→ meilleur modèle installé qui sait appeler des outils, dans la limite de la machine → sinon, avec accord, le
conteneur Ollama du profil Docker « assistant » télécharge le modèle du palier de la machine (volume nommé).
Jamais de téléchargement : sans terminal (CI, tâche planifiée), en démonstration (SALUBRI_LLM_DURING_DEMO=off),
pendant make verify, la répétition ou les tests (SALUBRI_NO_LLM_PULL=1).
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"

# (nom, port, chemin de la liste des modèles, nom d'hôte vu depuis le conteneur de l'API)
RUNTIMES = [
    ("Ollama", 11434, "/api/tags"),
    ("LM Studio", 1234, "/v1/models"),
    ("llama.cpp server", 8080, "/v1/models"),
    ("llama.cpp server", 8081, "/v1/models"),
    ("Jan", 1337, "/v1/models"),
    ("LocalAI", 8080, "/v1/models"),
    ("vLLM", 8000, "/v1/models"),
]
FAMILIES = ("qwen3", "qwen2.5", "qwen2_5", "llama3", "llama-3", "llama3.1", "llama3.2", "mistral")


@dataclass
class Tier:
    nom: str
    tag: str | None  # étiquette Ollama
    taille_go: float
    licence: str
    max_params_b: float  # plus gros modèle installé accepté sur cette machine


# Paliers (vérifiés sur registry.ollama.ai le 17/11/2026). Qwen2.5 3B est sous licence de recherche Qwen (usage
# non commercial) : le palier modeste prend donc le 1,5B (Apache 2.0), plus faible mais libre.
TIERS = {
    "aucun": Tier("moins de 8 Go de mémoire, sans GPU", None, 0, "", 0),
    "petit": Tier("Qwen2.5 1,5B instruct (4 bits)", "qwen2.5:1.5b-instruct", 1.0, "Apache-2.0", 4),
    "moyen": Tier("Qwen2.5 7B instruct (4 bits)", "qwen2.5:7b-instruct", 4.7, "Apache-2.0", 8),
    "grand": Tier("Qwen2.5 14B instruct (4 bits)", "qwen2.5:14b-instruct", 9.0, "Apache-2.0", 15),
}


@dataclass
class Hardware:
    ram_go: float
    ram_libre_go: float
    vram_go: float
    apple: bool
    coeurs: int
    disque_libre_go: float


def tier_for(h: Hardware) -> str:
    """< 8 Go sans GPU → aucun ; 8–15 Go → petit ; ≥ 16 Go de mémoire ou 6–10 Go de VRAM → moyen ;
    ≥ 32 Go de mémoire ou ≥ 12 Go de VRAM → grand (mémoire unifiée Apple comptée comme RAM)."""
    if h.ram_go >= 32 or h.vram_go >= 12:
        return "grand"
    if h.ram_go >= 16 or h.vram_go >= 6:
        return "moyen"
    if h.ram_go >= 8:
        return "petit"
    return "aucun"


# ---------------------------------------------------------------- matériel
def hardware() -> Hardware:
    ram = free = 0.0
    sysname = platform.system()
    try:
        if sysname == "Linux":
            info = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines() if ":" in line)
            ram = int(info["MemTotal"].split()[0]) / 1024**2
            free = int(info.get("MemAvailable", info["MemFree"]).split()[0]) / 1024**2
        elif sysname == "Darwin":
            ram = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout) / 1024**3
            free = ram / 2
        elif sysname == "Windows":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong), ("c", ctypes.c_ulonglong),
                            ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]  # fmt: skip

            ms = MS()
            ms.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))  # type: ignore[attr-defined]
            ram, free = ms.ullTotalPhys / 1024**3, ms.ullAvailPhys / 1024**3
    except Exception:
        pass
    vram = 0.0
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=5).stdout  # fmt: skip
            vram = max((float(x) for x in out.split()), default=0) / 1024
        except Exception:
            vram = 0.0
    apple = sysname == "Darwin" and platform.machine() == "arm64"
    disk = shutil.disk_usage(ROOT).free / 1024**3
    return Hardware(round(ram, 1), round(free, 1), round(vram, 1), apple, os.cpu_count() or 1, round(disk, 1))


# ---------------------------------------------------------------- détection
def _get(url: str, timeout: float = 1.0) -> object | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (adresses locales seulement)
            return json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def list_models(base: str, path: str) -> list[str] | None:
    """Modèles d'un serveur (forme Ollama /api/tags ou OpenAI /v1/models) ; None s'il ne répond pas."""
    body = _get(base + path)
    if body is None:
        return None
    if isinstance(body, dict) and "models" in body:  # Ollama
        return [m.get("name") or m.get("model", "") for m in body["models"] if isinstance(m, dict)]
    if isinstance(body, dict) and "data" in body:  # OpenAI
        return [m.get("id", "") for m in body["data"] if isinstance(m, dict)]
    return []


def params_b(name: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", name.lower().replace("_", "."))
    return float(m.group(1)) if m else 7.0


def usable(name: str) -> bool:
    n = name.lower()
    return any(f in n for f in FAMILIES) and "embed" not in n and "coder" not in n and "vision" not in n


def best_model(models: list[str], max_b: float) -> str | None:
    """Plus gros modèle instruct d'une famille qui appelle des outils, dans la limite de la machine."""
    ok = [m for m in models if usable(m) and params_b(m) <= max_b]
    if not ok:
        return None
    return sorted(ok, key=lambda m: (params_b(m), "instruct" in m.lower(), m))[-1]


def is_salubri(base: str) -> bool:
    body = _get(base + "/api/health")
    return isinstance(body, dict) and "masking" in body and "queue" in body


def detect(max_b: float, host: str = "http://localhost") -> tuple[str, str, str] | None:
    """(runtime, url de base OpenAI vue de l'hôte, modèle) du meilleur modèle trouvé, ou None."""
    found: list[tuple[str, str, str]] = []
    seen_ports: set[int] = set()
    for name, port, path in RUNTIMES:
        base = f"{host}:{port}"
        if port == 8000 and is_salubri(base):
            continue  # l'API de Salubri, pas vLLM
        if port in seen_ports and name == "LocalAI":
            continue  # même port que llama.cpp, déjà interrogé
        models = list_models(base, path)
        seen_ports.add(port)
        if models is None:
            continue
        m = best_model(models, max_b)
        if m:
            found.append((name, f"{base}/v1", m))
    if not found:
        return None
    return sorted(found, key=lambda f: params_b(f[2]))[-1]


# ---------------------------------------------------------------- .env
def read_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return {**out, **{k: v for k, v in os.environ.items() if k.startswith("SALUBRI_")}}


def write_env(values: dict[str, str], dry: bool) -> None:
    if dry:
        print("  (essai : .env non modifié) " + ", ".join(f"{k}={v}" for k, v in values.items()))
        return
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    keep = [ln for ln in lines if ln.split("=", 1)[0].strip() not in values]
    ENV.write_text("\n".join(keep + [f"{k}={v}" for k, v in values.items()]) + "\n", encoding="utf-8")


def container_url(url: str) -> str:
    """L'API tourne dans Docker : « localhost » de la machine s'y appelle host.docker.internal."""
    return url.replace("://localhost", "://host.docker.internal").replace("://127.0.0.1", "://host.docker.internal")


# ---------------------------------------------------------------- consentement et téléchargement
def may_pull(mode: str, env: dict[str, str], interactive: bool) -> tuple[bool, str]:
    """(télécharger ?, raison). Jamais sans terminal, en démonstration ou pendant les contrôles."""
    if mode == "no":
        return False, "--llm=no"
    if env.get("SALUBRI_NO_LLM_PULL") == "1" or env.get("CI"):
        return False, "contrôles automatiques (CI, make verify, répétition, tests)"
    if env.get("SALUBRI_DEMO_MODE", "true").lower() != "false" and env.get(
        "SALUBRI_LLM_DURING_DEMO", "off"
    ).lower() not in ("on", "true", "1"):
        return False, "démonstration (SALUBRI_LLM_DURING_DEMO=off) : jamais de téléchargement avant une séance du jury"
    if mode == "yes":
        return True, "--llm=yes"
    if not interactive:
        return False, "pas de terminal pour demander l'accord"
    return True, "à confirmer"


def ask(question: str) -> bool:
    try:
        return input(question).strip().lower() in ("o", "oui", "y", "yes")
    except EOFError:
        return False


def pull(tag: str, gpu: bool) -> bool:
    """Conteneur Ollama du profil « assistant » ; le téléchargement reprend où il s'était arrêté."""
    files = ["-f", "docker-compose.yml"] + (["-f", "docker-compose.gpu.yml"] if gpu else [])
    up = subprocess.run(["docker", "compose", *files, "--profile", "assistant", "up", "-d", "ollama"], cwd=ROOT)
    if up.returncode != 0:
        return False
    return subprocess.run(["docker", "compose", "--profile", "assistant", "exec", "ollama", "ollama", "pull", tag],
                          cwd=ROOT).returncode == 0  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    mode = next((a.split("=", 1)[1] for a in args if a.startswith("--llm=")), "auto")
    dry = "--dry-run" in args
    env = read_env()
    if env.get("SALUBRI_ASSISTANT_ENABLED", "false").lower() not in ("true", "1", "on"):
        if "--doctor" in args:
            print("Assistant : module éteint")
        return 0
    hw = hardware()
    tier = TIERS[tier_for(hw)]
    if env.get("SALUBRI_LLM_URL") and "--doctor" not in args and "--force" not in args:
        print(
            f"Assistant : SALUBRI_LLM_URL déjà réglé ({env['SALUBRI_LLM_URL']}, modèle {env.get('SALUBRI_LLM_MODEL', '?')})"
        )
        return 0
    found = detect(max(tier.max_params_b, 4 if hw.ram_go >= 8 else 0))
    if "--doctor" in args:
        state = f"modèle {found[2]} sur {found[0]}" if found else "aucun modèle local joignable"
        print(f"Assistant : {state} ; palier de la machine : {tier.nom} "
              f"(RAM {hw.ram_go} Go, VRAM {hw.vram_go} Go, disque libre {hw.disque_libre_go} Go)")  # fmt: skip
        return 0
    if found:
        name, url, model = found
        print(f"Assistant : modèle {model} trouvé sur {name}")
        write_env({"SALUBRI_LLM_URL": container_url(url), "SALUBRI_LLM_MODEL": model}, dry)
        return 0
    if tier.tag is None:
        print(f"Assistant : désactivé, {tier.nom} (RAM {hw.ram_go} Go). Rien n'est téléchargé.")
        return 0
    go, why = may_pull(mode, env, sys.stdin.isatty() and not dry)
    need = tier.taille_go * 1.2 + 1
    if not go or dry:
        print(f"Assistant : aucun modèle local. Il faudrait {tier.tag} ({tier.taille_go} Go, {tier.licence}) ; "
              f"pas de téléchargement : {why if not go else 'essai'}.")  # fmt: skip
        return 0
    if hw.disque_libre_go < need:
        print(f"Assistant : désactivé, disque insuffisant ({hw.disque_libre_go} Go libres, {need:.0f} Go nécessaires).")
        return 0
    if why == "à confirmer" and not ask(
        f"Télécharger {tier.tag} ({tier.taille_go} Go, licence {tier.licence}) ? {hw.disque_libre_go} Go libres. [o/N] "
    ):
        print("Assistant : pas de téléchargement, Salubri démarre sans l'assistant.")
        return 0
    gpu = hw.vram_go > 0 and shutil.which("nvidia-ctk") is not None and (ROOT / "docker-compose.gpu.yml").exists()
    if not pull(tier.tag, gpu):
        print("Assistant : téléchargement impossible (réseau, disque ou Docker) ; Salubri démarre sans l'assistant.")
        return 0
    write_env({"SALUBRI_LLM_URL": "http://ollama:11434/v1", "SALUBRI_LLM_MODEL": tier.tag}, dry)
    print(f"Assistant : {tier.tag} prêt dans le conteneur Ollama (profil « assistant »).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # jamais bloquant pour le démarrage de Salubri
        print(f"Assistant : détection impossible ({exc}) ; Salubri démarre sans l'assistant.")
        sys.exit(0)
