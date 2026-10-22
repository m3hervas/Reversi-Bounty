"""El workflow que publica la web: tiene que poder desplegar y no publicar nada de más."""

from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
FLUJO = yaml.safe_load((RAIZ / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8"))
PASOS = FLUJO["jobs"]["deploy"]["steps"]


def test_se_lanza_con_main_y_a_mano():
    # En YAML, la clave «on» se lee como True.
    disparadores = FLUJO.get("on") or FLUJO[True]
    assert disparadores["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in disparadores


def test_tiene_los_permisos_justos_para_desplegar():
    assert FLUJO["permissions"] == {"contents": "read", "pages": "write", "id-token": "write"}


def test_construye_el_zip_antes_de_subir_la_web():
    ordenes = [paso.get("run", paso.get("uses", "")) for paso in PASOS]
    construir = next(i for i, o in enumerate(ordenes) if "build_web.py" in o)
    subir = next(i for i, o in enumerate(ordenes) if "upload-pages-artifact" in o)
    assert construir < subir


def test_publica_solo_la_carpeta_web():
    subir = next(p for p in PASOS if "upload-pages-artifact" in p.get("uses", ""))
    assert subir["with"]["path"] == "web"


def test_termina_con_el_paso_de_despliegue():
    assert "deploy-pages" in PASOS[-1]["uses"]
    assert PASOS[-1]["id"] == "deployment"
