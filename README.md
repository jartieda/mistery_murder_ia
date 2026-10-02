# Mystery Murder Games with AI

This project generates a structured, playable murder-mystery case. One canonical case file is checked for consistency before the player handout, private role packets, and facilitator solution are rendered.

## Requirements

- Python 3.10 or newer
- A Google Cloud project with the Vertex AI API enabled and billing configured
- Application Default Credentials with permission to use Vertex AI (for example, `roles/aiplatform.user`)

## Setup

Activate the project environment and install dependencies:

```bash
source /home/jartieda/venv_mistery_murder_ia/bin/activate
pip install -r requirements.txt
```

Authenticate with Google Cloud's default credential flow. No Gemini API key or `NVIDIA_API_KEY` is required:

```bash
gcloud auth application-default login
gcloud config set project YOUR_GOOGLE_CLOUD_PROJECT
gcloud services enable aiplatform.googleapis.com
export GOOGLE_CLOUD_PROJECT=YOUR_GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION=global
```

The model defaults to `gemini-2.5-flash`. Override it with `GEMINI_MODEL` when needed.

## Generate a Case

```bash
python generate1.py --characters 5 --language Spanish --female-characters 3 --output-dir output
```

`--language` sets the language used for all generated case text and defaults to `English`. The handout, private packets, Act II reveal, solution, and graph use Spanish headings and instructions when the language is `Spanish` (or `es`); English is used for built-in labels in other languages. `--female-characters` requests an exact number of female player characters; it is optional, and the victim is not included in that count. The character count must be between 3 and 12, and the requested female count must be between zero and the player count. The generator checks the returned gender labels and retries if the requested number is not met. The default command creates:

The CLI reports generation, validation attempts and retries, file writing, and graph rendering as they happen.

- `output/player_handout.md`: shared, spoiler-free premise, cast, incident, and clues
- `output/act_ii_reveal.md`: facilitator-delivered clue sheet to reveal when Act II begins
- `output/player_packets/`: one private role sheet per character; distribute each only to its player
- `output/solution.md`: facilitator-only culprit and explanation
- `output/case.private.json`: complete canonical case data; facilitator-only
- `output/case.private.png`: graph of the canonical case; facilitator-only

The shared handout contains Act I clues only. Keep `act_ii_reveal.md` back until Act II, and keep `solution.md` facilitator-only until the resolution phase.

Use `--no-graph` to skip the graph. The legacy `generate_with_agent.py` command remains available and now invokes the same validated pipeline; the previous free-form ReAct loop was removed because it discarded tool results and did not reliably validate the case.

## Create Print PDFs

After generating the Markdown files, build the player PDFs:

```bash
python make_print_pdfs.py --input-dir output --paper A4
```

The tool auto-detects Spanish or English headings; set `--language Spanish` or `--language English` to choose the printed labels explicitly. `--paper Letter` selects US Letter instead of A4. It creates `output/print-ready/players/` with one PDF per player, each containing a full repeated copy of the shared handout followed by only that player's private role sheet. It creates `output/print-ready/act-ii/` with one separate Act II clue sheet per player, so these can be held back and distributed when that phase begins. No facilitator solution is included. `INSTRUCCIONES-DE-IMPRESION.md` lists the PDFs and the number of repeated copies needed.

The layout embeds Unicode-capable fonts, uses clear section hierarchy and restrained decorative rules, and adds page headers and numbering. PDFs use printer-friendly white pages, A4 by default, and generous margins.

## Validation

The generator checks cast size and uniqueness, murderer and witness references, secret subjects, per-character motives, and clue references before writing files. Death time and every whereabouts interval use 24-hour `HH:MM`; each account must cover the death time, and a witness must share the stated location and provide a bounded observation interval. When Gemini names a witness but omits the observed interval, the generator infers a five-minute window only if both accounts overlap in time and location; it will not infer a window over the culprit's death minute. The murderer cannot have a witness covering the moment of death. An intentional false or partial whereabouts claim must be marked with a facilitator explanation and a clue that lets players expose it. Exactly one Act II clue is required to carry a specific weapon-to-origin comparison, which is printed in the player reveal rather than being left only in the facilitator solution.

After local validation, a Gemini reviewer checks the canonical case alongside the rendered player handout, role packets, Act II reveal, and facilitator solution for contradictions and fair-play solvability. It may request up to two targeted repairs. The selected culprit, player roster, and gender assignments are immutable during repair. If major issues remain after the repair limit, generation stops with an error rather than writing unapproved materials. This semantic review adds Gemini calls and is still a model-based check; facilitators should review the final case before play.

Run the offline checks with:

```bash
python -m unittest discover -s tests -v
```
