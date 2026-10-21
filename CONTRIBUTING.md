# Cómo contribuir

La forma principal de contribuir es **añadir un bot** mediante un pull request.

Hay un tutorial completo, con un ejemplo, en la
[documentación](https://reversi-bounty.readthedocs.io/es/latest/tutorial/). En resumen:

1. Haz un fork, clona el repositorio y crea una rama.
2. Escribe tu bot en `players/custom/<tu_bot>.py`: una subclase de `Player` con nombre, autores,
   descripción, emoji y el método `choose_move`.
3. Añade **una** entrada en `players/custom/players.yaml`.
4. Comprueba en local con `pytest -q` y `ruff check .`.
5. Abre el pull request y rellena la plantilla.

Nadie escribe directamente en `main`: todo entra por pull request, con los tests en verde y la
aprobación de otra persona.
