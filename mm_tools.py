"""Compatibility exports for the validated mystery-case generation pipeline."""

from case_generation import (
    Character,
    Clue,
    Motive,
    MysteryCase,
    Secret,
    Whereabouts,
    case_to_graph_data,
    generate_case,
    get_model,
    render_character_packet,
    render_player_handout,
    render_solution,
    validate_case,
    write_case_files,
)

__all__ = [
    "Character",
    "Clue",
    "Motive",
    "MysteryCase",
    "Secret",
    "Whereabouts",
    "case_to_graph_data",
    "generate_case",
    "get_model",
    "render_character_packet",
    "render_player_handout",
    "render_solution",
    "validate_case",
    "write_case_files",
]
