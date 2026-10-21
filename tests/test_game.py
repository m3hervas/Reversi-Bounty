"""Tests del motor: reglas, volteos, pasos de turno, final y robustez."""

from __future__ import annotations

import random

import pytest

from reversibounty.game import (
    BLACK,
    EMPTY,
    SIZE,
    WHITE,
    GameState,
    apply_move,
    flips,
    initial_state,
    is_legal,
    is_terminal,
    legal_moves,
    move_to_str,
    score,
    str_to_move,
    winner,
)


def board_from(rows: list[str], player: int = BLACK) -> GameState:
    """Construye un estado desde texto: X negras, O blancas, . vacío."""
    values = {"X": BLACK, "O": WHITE, ".": EMPTY}
    board = tuple(tuple(values[ch] for ch in row) for row in rows)
    return GameState(board=board, player=player)


def test_initial_state():
    state = initial_state()
    assert state.player == BLACK
    assert score(state) == (2, 2)
    assert state.board[3][3] == WHITE and state.board[4][4] == WHITE
    assert state.board[3][4] == BLACK and state.board[4][3] == BLACK


def test_initial_legal_moves():
    assert sorted(legal_moves(initial_state())) == [(2, 3), (3, 2), (4, 5), (5, 4)]


def test_apply_move_flips_and_changes_turn():
    state = apply_move(initial_state(), (2, 3))
    assert state.board[2][3] == BLACK
    assert state.board[3][3] == BLACK  # volteada
    assert score(state) == (4, 1)
    assert state.player == WHITE


def test_apply_move_does_not_mutate():
    state = initial_state()
    before = state.board
    apply_move(state, (2, 3))
    assert state.board == before


@pytest.mark.parametrize(
    "move",
    [
        (0, 0), (3, 3), (-1, 2), (8, 0), (2, 8), "d3", None,
        (2,), (2, 3, 4), (2.0, 3), (True, 3), [2, "3"],
    ],
)
def test_illegal_moves_are_rejected(move):
    state = initial_state()
    assert not is_legal(state, move)
    with pytest.raises(ValueError):
        apply_move(state, move)


def test_list_move_is_accepted():
    assert is_legal(initial_state(), [2, 3])


def test_flips_in_all_eight_directions():
    state = board_from([
        "O.O.O...",
        ".XXX....",
        "OX.XO...",
        ".XXX....",
        "O.O.O...",
        "........",
        "........",
        "........",
    ], player=WHITE)
    flipped = flips(state.board, WHITE, (2, 2))
    assert sorted(flipped) == [(1, 1), (1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2), (3, 3)]
    after = apply_move(state, (2, 2))
    assert all(after.board[r][c] == WHITE for r, c in flipped)


def test_no_flip_without_closing_disc():
    state = board_from([
        "........",
        ".XXX....",
        ".X.X....",
        ".XXX....",
        "........",
        "........",
        "........",
        "........",
    ], player=WHITE)
    assert flips(state.board, WHITE, (2, 2)) == []
    assert not is_legal(state, (2, 2))


def test_opponent_passes_and_turn_returns():
    # Tras jugar negras en a1, blancas no tienen jugada pero negras sí: blancas pasan.
    state = board_from([
        ".OX.....",
        "........",
        "........",
        "........",
        "........",
        "........",
        "......OX",
        "........",
    ], player=BLACK)
    after = apply_move(state, (0, 0))
    assert not legal_moves(GameState(after.board, WHITE))
    assert legal_moves(GameState(after.board, BLACK))
    assert after.player == BLACK


def test_terminal_full_board_and_winner():
    state = board_from(["XXXXXXXX"] * 5 + ["OOOOOOOO"] * 3)
    assert is_terminal(state)
    assert legal_moves(state) == []
    assert winner(state) == BLACK
    assert score(state) == (40, 24)


def test_terminal_draw():
    state = board_from(["XXXXXXXX"] * 4 + ["OOOOOOOO"] * 4)
    assert is_terminal(state)
    assert winner(state) == 0


def test_terminal_before_board_is_full():
    # Solo quedan fichas negras: nadie puede mover aunque haya huecos.
    state = board_from(["X......."] + ["........"] * 7)
    assert is_terminal(state)
    assert winner(state) == BLACK


def test_winner_is_none_while_playing():
    assert winner(initial_state()) is None


def test_dict_round_trip():
    state = apply_move(initial_state(), (2, 3))
    assert GameState.from_dict(state.to_dict()) == state


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"board": [[0] * 8] * 7, "player": 1},
        {"board": [[0] * 7] * 8, "player": 1},
        {"board": [[2] * 8] * 8, "player": 1},
        {"board": [[0] * 8] * 8, "player": 0},
        {"board": [[0] * 8] * 8, "player": True},
    ],
)
def test_from_dict_rejects_bad_input(data):
    with pytest.raises(ValueError):
        GameState.from_dict(data)


def test_state_is_hashable_and_immutable():
    state = initial_state()
    assert {state: 1}[initial_state()] == 1
    with pytest.raises(AttributeError):
        state.player = WHITE  # type: ignore[misc]


def test_notation():
    assert move_to_str((2, 3)) == "d3"
    assert str_to_move("d3") == (2, 3)
    assert str_to_move(" H8 ") == (SIZE - 1, SIZE - 1)
    for bad in ["", "i1", "a9", "a", "a10"]:
        with pytest.raises(ValueError):
            str_to_move(bad)


def test_random_games_respect_invariants():
    rng = random.Random(0)
    for _ in range(30):
        state = initial_state()
        while not is_terminal(state):
            moves = legal_moves(state)
            assert moves, "una posición no terminal siempre tiene jugadas para quien mueve"
            before = sum(score(state))
            state = apply_move(state, rng.choice(moves))
            assert sum(score(state)) == before + 1
        assert winner(state) in (BLACK, WHITE, 0)


# Partida completa registrada (60 jugadas, con dos pasos de turno automáticos) cuyo resultado
# se ha comprobado contando las fichas del tablero final: ganan las blancas, 38 a 26.
PARTIDA_CONOCIDA = (
    "d3 c3 b3 e3 f3 c5 f6 g2 b5 c6 f4 a5 h1 f5 d6 e7 d7 e6 d8 c4 c7 b7 a8 b6 a4 f8 g4 b4 e8 a3 "
    "a7 g5 g8 c2 h4 g3 a2 h3 c1 d1 d2 e1 f1 f7 a6 h6 e2 b8 g7 c8 h5 g6 h2 h7 h8 g1 b2 f2 a1 b1"
).split()


def test_known_game_ends_with_expected_winner():
    state = initial_state()
    for text in PARTIDA_CONOCIDA:
        state = apply_move(state, str_to_move(text))
    assert is_terminal(state)
    assert score(state) == (26, 38)
    assert sum(score(state)) == SIZE * SIZE
    assert winner(state) == WHITE


def test_empty_board_has_no_moves_and_is_terminal():
    state = board_from(["........"] * 8)
    assert legal_moves(state) == []
    assert is_terminal(state)
    assert score(state) == (0, 0)
    assert winner(state) == 0


def test_position_with_exactly_one_legal_move():
    state = board_from(["XO......"] + ["........"] * 7)
    assert legal_moves(state) == [(0, 2)]


def test_move_on_the_board_edge_flips_along_the_edge():
    state = board_from(["XO......"] + ["........"] * 7)
    after = apply_move(state, (0, 2))
    assert after.board[0][:3] == (BLACK, BLACK, BLACK)
    assert score(after) == (3, 0)
