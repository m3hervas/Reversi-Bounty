# Reversi Bounty

<p align="center">
  <a href="https://m3hervas.github.io/Reversi-Bounty/">
    <img alt="Jugar ahora en la web" src="https://img.shields.io/badge/%E2%96%B6%20%20JUGAR%20AHORA%20EN%20LA%20WEB-1f7a4d?style=for-the-badge" height="48">
  </a>
</p>

[![Tests](https://github.com/m3hervas/Reversi-Bounty/actions/workflows/tests.yml/badge.svg)](https://github.com/m3hervas/Reversi-Bounty/actions/workflows/tests.yml)
[![Docs](https://readthedocs.org/projects/reversi-bounty/badge/?version=latest)](https://reversi-bounty.readthedocs.io)
[![Web](https://github.com/m3hervas/Reversi-Bounty/actions/workflows/pages.yml/badge.svg)](https://m3hervas.github.io/Reversi-Bounty/)
[![Licencia MIT](https://img.shields.io/badge/licencia-MIT-green)](LICENSE)

<a href="https://m3hervas.github.io/Reversi-Bounty/#/jugar"><img align="right" width="260" src="docs/img/partida.jpg" alt="Una partida contra Zeff minimax en la web"></a>

Reversi (Othello) para personas y bots. Juegas contra bots de IA escritos en Python, cada uno
con su cartel de recompensa, y un torneo nocturno los clasifica a todos. Práctica de IA,
CUNEF 2026/27.

- **[Jugar en la web](https://m3hervas.github.io/Reversi-Bounty/)**: sin instalar nada, también en el móvil.
- **[Marcador del torneo](https://m3hervas.github.io/Reversi-Bounty/#/marcador)**: se juega
  cada noche entre todos los bots.
- **[Documentación](https://reversi-bounty.readthedocs.io)**: reglas, API y tutorial.

## Instalar y jugar en la terminal

```bash
git clone https://github.com/m3hervas/Reversi-Bounty.git
cd Reversi-Bounty
python -m venv .venv
.venv\Scripts\activate         # Windows
source .venv/bin/activate      # Linux/macOS
pip install -e ".[dev]"

reversi-play          # dos personas (también reversi-play-color)
reversi-tournament    # liguilla entre todos los bots
```

## Añadir tu bot

Una subclase de `Player` con nombre, autores, descripción y emoji, y un método, `choose_move`.
Va en `players/custom/` y se envía por pull request: los tests comprueban solos que cumple las
reglas. Sigue el **[tutorial](https://reversi-bounty.readthedocs.io/es/latest/tutorial/)**.

## Licencia

[MIT](LICENSE): puedes usar, copiar y modificar el código manteniendo el aviso de copyright.
