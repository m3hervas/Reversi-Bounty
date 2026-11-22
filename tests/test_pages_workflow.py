"""El workflow que publica la web: tiene que poder desplegar y no publicar nada de más."""

from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
FLUJO = yaml.safe_load((RAIZ / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8"))
#: Los pasos que preparan y suben la web; la publicación va en otro trabajo (ver test de abajo).
PASOS = FLUJO["jobs"]["build"]["steps"]
DESPLIEGUE = FLUJO["jobs"]["deploy"]


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


def test_publica_en_un_trabajo_aparte_cuando_la_web_ya_esta_subida():
    # En el mismo trabajo, el despliegue preguntaba por la web antes de que GitHub la registrara.
    assert DESPLIEGUE["needs"] == "build"
    assert DESPLIEGUE["environment"]["name"] == "github-pages"
    assert "deploy-pages" in DESPLIEGUE["steps"][-1]["uses"]
    assert DESPLIEGUE["steps"][-1]["id"] == "deployment"
    assert not any("deploy-pages" in paso.get("uses", "") for paso in PASOS)


# -- Paso 5.4: volver a publicar cuando hay clasificación nueva ------------ #


def test_se_vuelve_a_publicar_al_terminar_el_torneo():
    # Un commit hecho por un workflow no genera "push": hay que escuchar al torneo.
    disparadores = FLUJO.get("on") or FLUJO[True]
    torneo = yaml.safe_load((RAIZ / ".github" / "workflows" / "torneo.yml").read_text("utf-8"))
    assert disparadores["workflow_run"]["workflows"] == [torneo["name"]]
    assert disparadores["workflow_run"]["types"] == ["completed"]


def test_no_publica_si_el_torneo_fallo():
    # La condición va en «build»; «deploy» lo necesita, así que si se salta uno, se salta el otro.
    condicion = FLUJO["jobs"]["build"]["if"]
    assert "workflow_run.conclusion == 'success'" in condicion
    assert "github.event_name != 'workflow_run'" in condicion  # push y a mano, siempre


def test_copia_la_clasificacion_de_la_rama_marcador_antes_de_subir_la_web():
    ordenes = [paso.get("run", paso.get("uses", "")) for paso in PASOS]
    copiar = next(i for i, o in enumerate(ordenes) if "web/leaderboard.json" in o)
    subir = next(i for i, o in enumerate(ordenes) if "upload-pages-artifact" in o)
    assert copiar < subir
    assert "origin marcador" in ordenes[copiar]
    assert "else" in ordenes[copiar]  # sin rama marcador todavía, la web se publica igual
