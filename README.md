# Reversi-Bounty

[![Docs](https://readthedocs.org/projects/reversi-bounty/badge/?version=latest)](https://reversi-bounty.readthedocs.io)

Reversi (Othello) para humanos y bots: motor en Python, web para jugar contra la IA en el navegador, API para programar tu propio bot y torneo automático con clasificación de recompensas. Práctica de IA, CUNEF 2026/27.

## Jugar en la terminal

Dos personas pueden jugar una partida completa de Reversi desde la consola, sin web.

1. Instala el proyecto (solo la primera vez):

   ```bash
   git clone https://github.com/m3hervas/Reversi-Bounty.git
   cd Reversi-Bounty
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

   En Linux o macOS, el entorno se activa con `source .venv/bin/activate`.

2. Lanza el juego con uno de estos dos comandos:

   ```bash
   reversi-play          # solo texto, funciona en cualquier terminal
   reversi-play-color    # tablero con colores y fichas grandes
   ```

3. Al empezar verás las instrucciones. En tu turno, escribe una casilla marcada en el tablero, por ejemplo `d3`, y pulsa Enter. Escribe `?` para ver la ayuda y `q` para salir.

Los comandos se instalan con el paquete, así que también funcionan con un simple `pip install` sin clonar el repositorio.
