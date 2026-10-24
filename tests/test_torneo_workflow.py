"""El workflow del torneo (paso 5.4): se ejecuta solo y guarda la clasificación sin tocar main."""

from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
FLUJO = yaml.safe_load((RAIZ / ".github" / "workflows" / "torneo.yml").read_text(encoding="utf-8"))
PASOS = FLUJO["jobs"]["torneo"]["steps"]
ORDENES = "\n".join(paso.get("run", paso.get("uses", "")) for paso in PASOS)


def test_se_lanza_cada_dia_y_a_mano():
    # En YAML, la clave «on» se lee como True.
    disparadores = FLUJO.get("on") or FLUJO[True]
    assert "workflow_dispatch" in disparadores
    (programado,) = disparadores["schedule"]
    minuto, hora, dia, mes, semana = programado["cron"].split()
    assert minuto.isdigit() and hora.isdigit()  # una hora fija...
    assert (dia, mes, semana) == ("*", "*", "*")  # ...todos los días


def test_solo_pide_permiso_para_escribir_contenido():
    assert FLUJO["permissions"] == {"contents": "write"}


def test_no_se_solapan_dos_torneos():
    assert FLUJO["concurrency"]["cancel-in-progress"] is False


def test_juega_el_torneo_con_el_comando_del_paquete():
    assert "pip install -e ." in ORDENES
    assert "reversi-tournament" in ORDENES


def test_guarda_la_clasificacion_en_la_rama_marcador_y_nunca_en_main():
    assert "git push origin marcador" in ORDENES
    ordenes_git = [linea.strip() for linea in ORDENES.splitlines() if "git " in linea]
    assert not [o for o in ordenes_git if "main" in o and not o.startswith("#")]  # nada con main
    assert "git add -f results/leaderboard.json" in ORDENES  # results/ está en .gitignore


def test_crea_la_rama_marcador_la_primera_vez():
    assert "git switch --orphan marcador" in ORDENES


def test_no_hace_commit_si_no_ha_cambiado_nada():
    assert "git diff --cached --quiet" in ORDENES
