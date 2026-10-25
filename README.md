# Reversi Bounty

<p align="center">
  <a href="https://m3hervas.github.io/Reversi-Bounty/">
    <img alt="Jugar ahora en la web" src="https://img.shields.io/badge/%E2%96%B6%20%20JUGAR%20AHORA%20EN%20LA%20WEB-1f7a4d?style=for-the-badge" height="48">
  </a>
</p>

[![Web](https://github.com/m3hervas/Reversi-Bounty/actions/workflows/pages.yml/badge.svg)](https://m3hervas.github.io/Reversi-Bounty/)
[![Docs](https://readthedocs.org/projects/reversi-bounty/badge/?version=latest)](https://reversi-bounty.readthedocs.io)
[![Licencia MIT](https://img.shields.io/badge/licencia-MIT-green)](LICENSE)

Reversi (Othello) para humanos y bots: motor en Python, web para jugar contra la IA, API para
programar tu propio bot y torneo automático con clasificación de recompensas. Práctica de IA,
CUNEF 2026/27.

**Juega aquí, sin instalar nada: <https://m3hervas.github.io/Reversi-Bounty/>**

## Instalar y jugar en la terminal

```bash
git clone https://github.com/m3hervas/Reversi-Bounty.git
cd Reversi-Bounty
python -m venv .venv && .venv\Scripts\activate    # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"

reversi-play          # dos personas, solo texto
reversi-play-color    # tablero con colores
```

En tu turno escribe una casilla (`d3`), `?` para la ayuda y `q` para salir.

## Torneo

```bash
reversi-tournament --rondas 10    # liguilla entre todos los bots; guarda results/leaderboard.json
```

GitHub lo juega **cada noche** y publica la clasificación en la rama
[`marcador`](https://github.com/m3hervas/Reversi-Bounty/tree/marcador).

## Escribir un bot

Un bot es una subclase de `Player` con nombre, autores, descripción y emoji, y un método,
`choose_move`. Se añade en `players/custom/` y se envía por pull request. Sigue el
**[tutorial paso a paso](https://reversi-bounty.readthedocs.io/es/latest/tutorial/)**; los tests, el
estilo y la prueba de contrato te dicen si cumple las reglas.

Más en la [documentación](https://reversi-bounty.readthedocs.io): API, uso desde Python y reglas.
