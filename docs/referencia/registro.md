# El registro de jugadores

Un jugador entra en el proyecto solo si aparece en una **lista editada a mano**. Nada se
descubre solo: quien revisa un pull request ve, en el mismo diff, el archivo del bot y la
única línea que lo admite. Esa revisión es la puerta de seguridad.

Hay dos listas, cada una junto a los jugadores que admite:

| Lista | Qué admite |
|---|---|
| `players/builtin/players.yaml` | Los jugadores de referencia que trae el proyecto. |
| `players/custom/players.yaml` | Los enviados por pull request. |

Cada entrada dice dónde está la clase y cuál es, y nada más:

```yaml
players:
  - file: mi_bot.py     # un archivo junto a la lista
    class: MiBot
```

El nombre, los autores, la descripción y el emoji **no se repiten** en la lista: los declara la
propia clase. Así hay una sola fuente de verdad.

!!! warning "Cargar un jugador ejecuta su código"
    Importar un archivo ejecuta lo que haya escrito en él. Es seguro solo porque los archivos
    llegan por pull requests revisados.

## La prueba de contrato

`tests/test_contract.py` recorre **todos los jugadores registrados** y, en cada turno de varias
partidas jugadas con negras y con blancas, comprueba que la jugada es legal y que el jugador no
modifica el estado que recibe. No hace falta escribir ninguna prueba para un bot nuevo: si
incumple el contrato, la integración continua se pone en rojo y no se puede fusionar.

::: reversibounty.manifest
