"""Generate a validated mystery case and write its player/facilitator files."""

import argparse
from pathlib import Path

from case_generation import generate_case, write_case_files
from mm_graph import draw_case_graph


def show_progress(message: str) -> None:
    print(f"    {message}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--characters", type=int, default=5, help="number of player characters (3-12)")
    parser.add_argument(
        "--language",
        default="English",
        help="language for all generated case text (for example: Spanish, English, French)",
    )
    parser.add_argument(
        "--female-characters",
        type=int,
        help="exact number of female player characters; the victim is not counted",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--no-graph", action="store_true", help="skip the private case graph")
    args = parser.parse_args()

    female_count_status = (
        f"{args.female_characters} female player characters"
        if args.female_characters is not None
        else "no fixed female-character count"
    )
    print(
        f"[1/4] Generating a {args.language} case for {args.characters} players "
        f"({female_count_status})...",
        flush=True,
    )
    case = generate_case(
        args.characters,
        progress_callback=show_progress,
        language=args.language,
        female_characters=args.female_characters,
    )

    print("[2/4] Writing the player handout, role packets, and facilitator solution...", flush=True)
    paths = write_case_files(case, args.output_dir, language=args.language)
    if not args.no_graph:
        print("[3/4] Rendering the facilitator-only case graph...", flush=True)
        graph_path = args.output_dir / "case.private.png"
        draw_case_graph(case, graph_path, language=args.language)
        paths["private_graph"] = graph_path
    else:
        print("[3/4] Skipping the case graph (--no-graph).", flush=True)

    print("[4/4] Generation complete.", flush=True)
    print(f"Generated case for {len(case.characters)} players in {args.output_dir.resolve()}")
    print(f"Player handout: {paths['player_handout']}")
    print(f"Private role packets: {paths['player_packets']}")
    print(f"Facilitator solution: {paths['solution']}")
    print("The private case JSON and graph contain the solution; do not distribute them to players.")


if __name__ == "__main__":
    main()
