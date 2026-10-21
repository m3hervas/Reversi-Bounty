# Reversi Bounty

Reversi (Othello) para humanos y bots: un motor de juego en Python, una web para jugar
contra la IA desde el navegador, una API para programar tu propio bot y un torneo automático
con clasificación de recompensas.

Práctica de **Inteligencia Artificial, 3º MAT-A, CUNEF Universidad 2026/27**.

## Qué hay en el proyecto

| Parte | Qué hace |
|---|---|
| Motor del juego | Reglas, jugadas legales, volteos, paso de turno y final de partida. |
| API de bots | Una clase `Player` que cualquiera puede implementar para escribir su bot. |
| Torneo | Todos contra todos, con ambos colores, y clasificación. |
| Web | Jugar contra la IA en el navegador, sin instalar nada. |

!!! note "Estado"
    La documentación crece con el proyecto. Por ahora están disponibles las
    [reglas del juego](reglas.md) y la referencia del [motor del juego](referencia/motor.md).

## Instalación

```bash
git clone https://github.com/m3hervas/Reversi-Bounty.git
cd Reversi-Bounty
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```
