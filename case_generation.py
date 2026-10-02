from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

load_dotenv("env_keys")


class Character(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    biography: str = Field(min_length=20)
    gender: Literal["female", "male", "nonbinary"] = Field(
        description="Character gender. Use these exact values regardless of output language."
    )


class Motive(BaseModel):
    model_config = ConfigDict(extra="forbid")

    character_name: str
    reason: str = Field(min_length=20)


class Secret(BaseModel):
    model_config = ConfigDict(extra="forbid")

    holder_name: str
    about_name: str
    fact: str = Field(min_length=20)


class Whereabouts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    character_name: str
    account: str = Field(min_length=20)
    location: str = Field(min_length=1)
    start_time: str = Field(min_length=1)
    end_time: str = Field(min_length=1)
    witness_name: str | None = None
    witnessed_start_time: str | None = Field(
        default=None,
        description="Start of the interval directly observed by the named witness, in 24-hour HH:MM format.",
    )
    witnessed_end_time: str | None = Field(
        default=None,
        description="End of the interval directly observed by the named witness, in 24-hour HH:MM format.",
    )


class Clue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str = Field(min_length=20)
    implicates: list[str] = Field(min_length=1)
    act: Literal["I", "II"] = Field(description="Act in which this clue is revealed")
    weapon_match: bool = Field(
        default=False,
        description="True only for the Act II clue that physically matches the murder weapon to its stated origin.",
    )


class MysteryCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setting: str = Field(min_length=10)
    introduction: str = Field(min_length=40)
    characters: list[Character] = Field(min_length=3)
    victim: Character
    murderer_name: str
    murder_time: str = Field(
        min_length=1,
        description="Estimated time of death, using 24-hour HH:MM format.",
    )
    murder_location: str = Field(min_length=1)
    weapon_name: str = Field(min_length=1)
    weapon_owner_name: str
    weapon_origin: str = Field(min_length=1)
    weapon_signature: str = Field(min_length=10)
    incident: str = Field(min_length=40)
    motives: list[Motive] = Field(min_length=3)
    secrets: list[Secret] = Field(min_length=3)
    whereabouts: list[Whereabouts] = Field(min_length=3)
    clues: list[Clue] = Field(min_length=3)
    solution: str = Field(min_length=80)


CASE_PROMPT = """Create a playable, logically consistent murder-mystery case for exactly {count} player characters.
Return one complete case matching the requested structured schema.

Quality requirements:
- Write all prose fields (setting, introduction, roles, biographies, incident, motives, secrets, whereabouts, clues, solution, weapon name, weapon origin, and weapon signature) in {language}. Keep proper names unchanged. The gender field must use exactly `female`, `male`, or `nonbinary`.
- Use distinct, memorable names, occupations, voices, and relationships. Avoid placeholder names and repeated archetypes.
- Set the entire case in one specific place and a compact time window. Keep all events compatible with the murder time and location.
- The victim is not one of the player characters. Choose exactly one murderer from the player characters.
- Give every player character one motive, one private secret to know, and one whereabouts account. Set an estimated death time as 24-hour HH:MM. Every whereabouts account must include a concise location and a start/end interval in HH:MM that covers the death time; keep the case in the same evening and do not cross midnight.
- For a named witness, give the exact interval they directly observed, use the same location for both characters, and make the observation interval fit within both characters' whereabouts intervals. It must not cover the murder time for the murderer; do not accidentally give the murderer a witnessed alibi at the time of death.
- Each motive must explain why that named character might kill this victim; never swap the killer and victim roles.
- Give each player one secret about a different player character (never the victim). Each secret should make its subject look potentially guilty, without proving guilt or revealing who the murderer is. Arrange the secrets so each player holds one secret and is the subject of exactly one secret.
- Whereabouts accounts are claims, not guaranteed proof of innocence. Use an optional witness only when that character can plausibly corroborate the account. Do not make every non-murderer conclusively innocent.
- Provide at least three concrete clues, with at least one clue revealed in each of Acts I and II. Their implications may be ambiguous and should leave several plausible suspects. At least one clue should be consistent with the actual murderer.
- Set weapon_name, weapon_owner_name, weapon_origin, and weapon_signature to concrete facts. weapon_owner_name must be the murderer, and weapon_origin must identify a specific place controlled by that character. The weapon_signature must be a distinctive, verifiable physical feature, not a generic property like color alone. Exactly one Act II clue must set weapon_match=true and describe the fragment or trace of this weapon. The generator will add a public forensic comparison using these fields, so the weapon-to-origin link must be accurate, specific, and consistent with the solution.
- The solution must identify the murderer and explain the method, motive, timeline, and how the clues support the answer. Keep this solution out of the player-facing introduction and clue descriptions.
- Reuse names exactly and consistently in every reference. Do not invent additional people who could be suspects or witnesses.

Requested player-character count: {count}
Requested language for all case prose: {language}
{female_requirement}
"""

OUTPUT_TEXT = {
    "English": {
        "victim": "The Victim",
        "cast": "The Cast",
        "incident": "The Incident",
        "how_to_play": "How to Play",
        "act_i": "Act I: Introductions and First Revelations",
        "act_i_instructions": "Introduce your character, discuss the Act I clues below, and begin sharing information that puts suspects under scrutiny.",
        "share_secret": "Every player must reveal the secret in their private packet during Act I or Act II. Explain how it makes the other character look potentially guilty; a secret is suspicion, not proof.",
        "share_motive": "By the end of Act I, every player must reveal the motive on their private sheet, or a public version of their conflict with the victim, so the group can compare suspects.",
        "share_witness": "If your private packet names you as a witness to another player's whereabouts, state what you witnessed during Act I or Act II and identify whose account it supports.",
        "act_i_clues": "Act I Clues",
        "act_ii": "Act II: Evidence and Witness Accounts",
        "act_ii_instructions": "The facilitator will provide the Act II clues separately when this act begins. Discuss new evidence, question one another, and share any private information you have not revealed yet.",
        "resolution": "Resolution",
        "resolution_instructions": "Each player names the suspect they believe is responsible and explains why. The facilitator then reveals the solution.",
        "act_ii_reveal": "Act II: New Evidence",
        "private_role": "Private role",
        "your_character": "Your character",
        "your_motive": "Your motive",
        "your_secret": "Your secret",
        "secret_fact": "You know this about {name}: {fact}",
        "secret_instruction": "Reveal this secret during Act I or Act II. Explain why it makes that character look potentially guilty, but do not present it as proof.",
        "your_account": "Your account of the night",
        "interval": "Claimed interval",
        "location_label": "Location",
        "witness_interval": "Interval you witnessed",
        "forensic_comparison": "Forensic comparison: The fragment's distinctive feature ({weapon_signature}) matches the {weapon_name} recorded at {weapon_origin}.",
        "estimated_death_time": "Estimated time of death",
        "weapon": "Weapon",
        "weapon_owner": "Weapon owner",
        "weapon_origin": "Weapon origin",
        "weapon_signature": "Matching feature",
        "corroborating_witness": "Corroborating witness",
        "no_witness": "No witness is listed.",
        "witnessed_whereabouts": "Whereabouts you witnessed",
        "witness_instruction": "During Act I or Act II, publicly state what you witnessed and whose account it supports. Do not claim more than this information establishes.",
        "not_a_witness": "You are not listed as a witness to another player's whereabouts.",
        "facilitator_solution": "Facilitator solution",
        "murderer": "Murderer",
        "time": "Time",
        "location": "Location",
        "motives": "Motives",
        "secret_assignments": "Secret assignments",
        "knows_about": "knows about",
        "whereabouts_claims": "Whereabouts claims",
        "witness_none": "none",
        "clue_implications": "Clue implications",
    },
    "Spanish": {
        "victim": "La víctima",
        "cast": "Personajes",
        "incident": "El incidente",
        "how_to_play": "Cómo jugar",
        "act_i": "Acto I: Presentaciones y primeras revelaciones",
        "act_i_instructions": "Presenta a tu personaje, comenta las pistas del Acto I y empieza a compartir información que haga sospechar de los personajes.",
        "share_secret": "Cada jugador debe revelar el secreto de su ficha durante el Acto I o el Acto II. Explica por qué hace que el otro personaje parezca culpable; un secreto despierta sospechas, pero no demuestra nada.",
        "share_motive": "Antes de terminar el Acto I, cada jugador debe revelar el motivo de su ficha, o una versión pública de su conflicto con la víctima, para que el grupo pueda comparar sospechosos.",
        "share_witness": "Si tu ficha indica que eres testigo de los movimientos de otro personaje, cuenta lo que viste durante el Acto I o el Acto II e indica a quién respalda tu testimonio.",
        "act_i_clues": "Pistas del Acto I",
        "act_ii": "Acto II: Pruebas y testimonios",
        "act_ii_instructions": "Al comenzar este acto, la persona que dirige la partida entregará por separado las pistas del Acto II. Comentad las nuevas pruebas, preguntaos entre vosotros y compartid la información privada que aún no hayáis revelado.",
        "resolution": "Resolución",
        "resolution_instructions": "Cada jugador señala a quien considera responsable y explica por qué. Después, la persona que dirige la partida revela la solución.",
        "act_ii_reveal": "Acto II: Nuevas pruebas",
        "private_role": "Ficha privada",
        "your_character": "Tu personaje",
        "your_motive": "Tu motivo",
        "your_secret": "Tu secreto",
        "secret_fact": "Sabes esto sobre {name}: {fact}",
        "secret_instruction": "Revela este secreto durante el Acto I o el Acto II. Explica por qué hace que ese personaje parezca culpable, pero no lo presentes como una prueba concluyente.",
        "your_account": "Tu versión de esa noche",
        "interval": "Intervalo que declaras",
        "location_label": "Lugar",
        "witness_interval": "Intervalo que presenciaste",
        "forensic_comparison": "Comparación forense: el rasgo distintivo del fragmento ({weapon_signature}) coincide con el objeto «{weapon_name}», registrado en {weapon_origin}.",
        "estimated_death_time": "Hora estimada de la muerte",
        "weapon": "Arma homicida",
        "weapon_owner": "Responsable del arma",
        "weapon_origin": "Procedencia del arma",
        "weapon_signature": "Rasgo coincidente",
        "corroborating_witness": "Testigo que puede corroborarlo",
        "no_witness": "No hay ningún testigo indicado.",
        "witnessed_whereabouts": "Movimientos que presenciaste",
        "witness_instruction": "Durante el Acto I o el Acto II, cuenta públicamente lo que presenciaste y a quién respalda tu testimonio. No afirmes más de lo que estos datos permiten concluir.",
        "not_a_witness": "No figuras como testigo de los movimientos de otro personaje.",
        "facilitator_solution": "Solución para quien dirige la partida",
        "murderer": "Asesino",
        "time": "Hora",
        "location": "Lugar",
        "motives": "Motivos",
        "secret_assignments": "Secretos asignados",
        "knows_about": "sabe esto sobre",
        "whereabouts_claims": "Versiones sobre los movimientos",
        "witness_none": "ninguno",
        "clue_implications": "A quién apuntan las pistas",
    },
}


def _output_text(language: str) -> dict[str, str]:
    normalized_language = language.strip().casefold()
    if normalized_language in {"spanish", "español", "es", "castellano"}:
        return OUTPUT_TEXT["Spanish"]
    return OUTPUT_TEXT["English"]


@lru_cache(maxsize=1)
def get_model():
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        vertexai=True,
        project=os.getenv("GOOGLE_CLOUD_PROJECT") or None,
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        temperature=0.55,
        model_kwargs={"automatic_function_calling": {"disable": True}},
    )


def _clock_minutes(value: str) -> int | None:
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        return None
    hours, minutes = map(int, value.split(":"))
    return hours * 60 + minutes


def validate_case(
    case: MysteryCase,
    requested_count: int,
    requested_female_characters: int | None = None,
) -> list[str]:
    errors: list[str] = []
    names = [character.name for character in case.characters]
    normalized_names = [name.casefold().strip() for name in names]
    name_set = set(names)

    if len(names) != requested_count:
        errors.append(f"Expected {requested_count} player characters; got {len(names)}.")
    if requested_female_characters is not None:
        female_count = sum(character.gender == "female" for character in case.characters)
        if female_count != requested_female_characters:
            errors.append(
                f"Expected {requested_female_characters} female player characters; got {female_count}."
            )
    if len(set(normalized_names)) != len(normalized_names):
        errors.append("Player character names must be unique, ignoring case.")
    if case.victim.name.casefold().strip() in set(normalized_names):
        errors.append("The victim must not be one of the player characters.")
    if case.murderer_name not in name_set:
        errors.append("The murderer_name must exactly match one player character.")
    if case.weapon_owner_name not in name_set:
        errors.append(f"Unknown weapon owner: {case.weapon_owner_name}.")
    elif case.weapon_owner_name != case.murderer_name:
        errors.append("The weapon origin must belong to the actual murderer.")

    murder_minute = _clock_minutes(case.murder_time)
    if murder_minute is None:
        errors.append("Murder time must use 24-hour HH:MM format.")

    motive_names = [motive.character_name for motive in case.motives]
    if len(motive_names) != len(names) or set(motive_names) != name_set:
        errors.append("There must be exactly one motive for every player character.")

    holders = [secret.holder_name for secret in case.secrets]
    if len(holders) != len(names) or set(holders) != name_set:
        errors.append("There must be exactly one private secret for every player character.")
    secret_subjects = [secret.about_name for secret in case.secrets]
    if len(secret_subjects) != len(names) or set(secret_subjects) != name_set:
        errors.append("There must be exactly one secret about every player character.")
    for secret in case.secrets:
        if secret.holder_name not in name_set:
            errors.append(f"Unknown secret holder: {secret.holder_name}.")
        if secret.about_name not in name_set:
            errors.append(f"Unknown secret subject: {secret.about_name}.")
        if secret.holder_name == secret.about_name:
            errors.append("A character cannot hold a secret about themselves.")

    whereabouts_names = [item.character_name for item in case.whereabouts]
    whereabouts_by_name = {item.character_name: item for item in case.whereabouts}
    if len(whereabouts_names) != len(names) or set(whereabouts_names) != name_set:
        errors.append("There must be exactly one whereabouts account for every player character.")
    for item in case.whereabouts:
        start_minute = _clock_minutes(item.start_time)
        end_minute = _clock_minutes(item.end_time)
        if start_minute is None or end_minute is None:
            errors.append(f"Whereabouts for {item.character_name} must use HH:MM times.")
        elif end_minute <= start_minute:
            errors.append(f"Whereabouts for {item.character_name} must end after they start.")
        elif murder_minute is not None and not start_minute <= murder_minute <= end_minute:
            errors.append(f"Whereabouts for {item.character_name} must cover the murder time.")

        if item.witness_name is not None:
            if item.witness_name not in name_set:
                errors.append(f"Unknown whereabouts witness: {item.witness_name}.")
            if item.witness_name == item.character_name:
                errors.append("A character cannot corroborate their own whereabouts.")
            witness_start = _clock_minutes(item.witnessed_start_time or "")
            witness_end = _clock_minutes(item.witnessed_end_time or "")
            if witness_start is None or witness_end is None:
                errors.append(f"Witness interval for {item.character_name} must use HH:MM times.")
            elif start_minute is not None and end_minute is not None:
                if witness_end <= witness_start:
                    errors.append(f"Witness interval for {item.character_name} must end after it starts.")
                if not start_minute <= witness_start < witness_end <= end_minute:
                    errors.append(f"Witness interval must fit within {item.character_name}'s claimed interval.")
                if (
                    item.character_name == case.murderer_name
                    and murder_minute is not None
                    and witness_start <= murder_minute <= witness_end
                ):
                    errors.append("The murderer must not have a witness covering the murder time.")
            witness_account = whereabouts_by_name.get(item.witness_name)
            if witness_account is not None:
                witness_account_start = _clock_minutes(witness_account.start_time)
                witness_account_end = _clock_minutes(witness_account.end_time)
                if (
                    witness_start is not None
                    and witness_end is not None
                    and witness_account_start is not None
                    and witness_account_end is not None
                    and not witness_account_start <= witness_start < witness_end <= witness_account_end
                ):
                    errors.append(f"{item.witness_name}'s own whereabouts must cover the witness interval.")
                if witness_account.location.casefold().strip() != item.location.casefold().strip():
                    errors.append(
                        f"{item.witness_name} must be at the same stated location to witness {item.character_name}."
                    )
        elif item.witnessed_start_time is not None or item.witnessed_end_time is not None:
            errors.append(f"Witness times for {item.character_name} require a named witness.")

    for clue in case.clues:
        unknown_names = set(clue.implicates) - name_set
        if unknown_names:
            errors.append(f"Clue '{clue.title}' references unknown suspects: {sorted(unknown_names)}.")
    clue_acts = {clue.act for clue in case.clues}
    if not {"I", "II"}.issubset(clue_acts):
        errors.append("There must be at least one clue revealed in each act.")
    weapon_match_clues = [clue for clue in case.clues if clue.weapon_match]
    if len(weapon_match_clues) != 1 or weapon_match_clues[0].act != "II":
        errors.append("Exactly one Act II clue must identify the murder weapon's forensic match.")
    if not any(case.murderer_name in clue.implicates for clue in case.clues):
        errors.append("At least one clue must be consistent with the actual murderer.")
    if not any(
        name != case.murderer_name
        for clue in case.clues
        for name in clue.implicates
    ):
        errors.append("At least one clue must leave another suspect plausible.")

    public_text = "\n".join(
        [case.introduction, case.incident, *(clue.description for clue in case.clues)]
    )
    murderer_name = re.escape(case.murderer_name)
    spoiler_patterns = (
        rf"\b{murderer_name}\b\s+(?:is|was)\s+(?:the\s+)?(?:murderer|killer|culprit)\b",
        rf"\b(?:the\s+)?(?:murderer|killer|culprit)\s+(?:is|was)\s+{murderer_name}\b",
        rf"\b{murderer_name}\b\s+(?:killed|murdered)\b",
    )
    if any(re.search(pattern, public_text, flags=re.IGNORECASE) for pattern in spoiler_patterns):
        errors.append("Player-facing narrative must not directly identify the murderer.")

    return errors


def generate_case(
    number_of_characters: int = 5,
    progress_callback: Callable[[str], None] | None = None,
    language: str = "English",
    female_characters: int | None = None,
) -> MysteryCase:
    if not 3 <= number_of_characters <= 12:
        raise ValueError("number_of_characters must be between 3 and 12")
    if not language.strip():
        raise ValueError("language must not be empty")
    if female_characters is not None and not 0 <= female_characters <= number_of_characters:
        raise ValueError("female_characters must be between 0 and number_of_characters")

    female_requirement = (
        f"Generate exactly {female_characters} female player characters (gender=female); "
        "the remaining player characters must not have gender=female. The victim is not counted."
        if female_characters is not None
        else "There is no required female character count; choose a varied cast."
    )
    prompt = CASE_PROMPT.format(
        count=number_of_characters,
        language=language.strip(),
        female_requirement=female_requirement,
    )
    structured_model = get_model().with_structured_output(
        MysteryCase,
        method="json_schema",
    )
    last_errors: list[str] = []

    for attempt in range(3):
        retry_prompt = prompt
        if last_errors:
            retry_prompt += "\nFix these validation errors in the complete case:\n- "
            retry_prompt += "\n- ".join(last_errors)
        if progress_callback:
            progress_callback(f"Generating complete case with Gemini (attempt {attempt + 1}/3)...")
        case = structured_model.invoke(retry_prompt)
        if not isinstance(case, MysteryCase):
            case = MysteryCase.model_validate(case)
        if progress_callback:
            progress_callback("Checking character references, clues, and spoiler constraints...")
        last_errors = validate_case(case, number_of_characters, female_characters)
        if not last_errors:
            if progress_callback:
                progress_callback("Case passed all consistency checks.")
            return case
        if progress_callback and attempt < 2:
            progress_callback(f"Found {len(last_errors)} consistency issue(s); retrying...")

    raise ValueError("Generated case failed consistency checks: " + " ".join(last_errors))


def render_player_handout(case: MysteryCase, language: str = "English") -> str:
    text = _output_text(language)
    lines = [
        f"# {case.setting}",
        "",
        case.introduction,
        "",
        f"## {text['victim']}",
        f"### {case.victim.name}, {case.victim.role}",
        case.victim.biography,
        "",
        f"## {text['cast']}",
    ]
    for character in case.characters:
        lines.extend([f"### {character.name}, {character.role}", character.biography, ""])

    lines.extend(
        [
            f"## {text['incident']}",
            case.incident,
            f"**{text['estimated_death_time']}:** {case.murder_time}",
            "",
            f"## {text['how_to_play']}",
            f"### {text['act_i']}",
            text["act_i_instructions"],
            "",
            text["share_motive"],
            text["share_secret"],
            text["share_witness"],
            "",
            f"## {text['act_i_clues']}",
        ]
    )
    for clue in case.clues:
        if clue.act != "I":
            continue
        lines.extend([f"### {clue.title}", clue.description, ""])
    lines.extend(
        [
            f"### {text['act_ii']}",
            text["act_ii_instructions"],
            "",
            f"### {text['resolution']}",
            text["resolution_instructions"],
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_act_two_reveal(case: MysteryCase, language: str = "English") -> str:
    text = _output_text(language)
    lines = [f"# {text['act_ii_reveal']}", ""]
    for clue in case.clues:
        if clue.act == "II":
            lines.extend([f"## {clue.title}", clue.description, ""])
            if clue.weapon_match:
                lines.extend(
                    [
                        text["forensic_comparison"].format(
                            weapon_signature=case.weapon_signature,
                            weapon_name=case.weapon_name,
                            weapon_origin=case.weapon_origin,
                        ),
                        "",
                    ]
                )
    return "\n".join(lines).rstrip() + "\n"


def render_character_packet(
    case: MysteryCase,
    character: Character,
    language: str = "English",
) -> str:
    text = _output_text(language)
    motive = next(item for item in case.motives if item.character_name == character.name)
    secret = next(item for item in case.secrets if item.holder_name == character.name)
    whereabouts = next(item for item in case.whereabouts if item.character_name == character.name)
    witness = whereabouts.witness_name or text["no_witness"]
    witnessed_accounts = [
        item for item in case.whereabouts if item.witness_name == character.name
    ]
    lines = [
        f"# {text['private_role']}: {character.name}",
        "",
        f"## {text['your_character']}\n{character.biography}",
        f"## {text['your_motive']}\n{motive.reason}",
        text["share_motive"],
        f"## {text['your_secret']}\n{text['secret_fact'].format(name=secret.about_name, fact=secret.fact)}",
        text["secret_instruction"],
        f"## {text['your_account']}\n{whereabouts.account}",
        f"**{text['interval']}:** {whereabouts.start_time}–{whereabouts.end_time}; **{text['location_label']}:** {whereabouts.location}",
        f"{text['corroborating_witness']}: {witness}",
    ]
    if witnessed_accounts:
        lines.extend(
            [
                "",
                f"## {text['witnessed_whereabouts']}",
                text["witness_instruction"],
            ]
        )
        lines.extend(
            f"- **{item.character_name}:** {item.account} ({text['witness_interval']}: {item.witnessed_start_time}–{item.witnessed_end_time}; {text['location_label'].casefold()}: {item.location})"
            for item in witnessed_accounts
        )
    else:
        lines.extend(
            [
                "",
                f"## {text['witnessed_whereabouts']}",
                text["not_a_witness"],
            ]
        )
    return "\n".join(lines) + "\n"


def render_solution(case: MysteryCase, language: str = "English") -> str:
    text = _output_text(language)
    lines = [
        f"# {text['facilitator_solution']}: {case.setting}",
        "",
        f"**{text['murderer']}:** {case.murderer_name}",
        f"**{text['time']}:** {case.murder_time}",
        f"**{text['location']}:** {case.murder_location}",
        f"**{text['weapon']}:** {case.weapon_name}",
        f"**{text['weapon_owner']}:** {case.weapon_owner_name}",
        f"**{text['weapon_origin']}:** {case.weapon_origin}",
        f"**{text['weapon_signature']}:** {case.weapon_signature}",
        "",
        case.solution,
        "",
        f"## {text['motives']}",
    ]
    lines.extend(f"- **{item.character_name}:** {item.reason}" for item in case.motives)
    lines.extend(["", f"## {text['secret_assignments']}"])
    lines.extend(
        f"- **{item.holder_name}** {text['knows_about']} **{item.about_name}**: {item.fact}"
        for item in case.secrets
    )
    lines.extend(["", f"## {text['whereabouts_claims']}"])
    lines.extend(
        f"- **{item.character_name}:** {item.account} ({text['interval'].casefold()}: {item.start_time}–{item.end_time}; {text['location_label'].casefold()}: {item.location}; {text['corroborating_witness'].casefold()}: {item.witness_name or text['witness_none']}; {text['witness_interval'].casefold()}: {item.witnessed_start_time or text['witness_none']}–{item.witnessed_end_time or text['witness_none']})"
        for item in case.whereabouts
    )
    lines.extend(["", f"## {text['clue_implications']}"])
    lines.extend(f"- **{item.title}:** {', '.join(item.implicates)}" for item in case.clues)
    return "\n".join(lines).rstrip() + "\n"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "player"


def write_case_files(
    case: MysteryCase,
    output_dir: str | Path = "output",
    language: str = "English",
) -> dict[str, Path]:
    destination = Path(output_dir)
    packets_dir = destination / "player_packets"
    packets_dir.mkdir(parents=True, exist_ok=True)

    player_path = destination / "player_handout.md"
    act_two_path = destination / "act_ii_reveal.md"
    solution_path = destination / "solution.md"
    private_case_path = destination / "case.private.json"
    player_path.write_text(render_player_handout(case, language), encoding="utf-8")
    act_two_path.write_text(render_act_two_reveal(case, language), encoding="utf-8")
    solution_path.write_text(render_solution(case, language), encoding="utf-8")
    private_case_path.write_text(
        json.dumps(case.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    packet_paths: list[Path] = []
    for index, character in enumerate(case.characters, start=1):
        packet_path = packets_dir / f"{index:02d}-{_slug(character.name)}.md"
        packet_path.write_text(
            render_character_packet(case, character, language),
            encoding="utf-8",
        )
        packet_paths.append(packet_path)

    return {
        "player_handout": player_path,
        "act_two_reveal": act_two_path,
        "solution": solution_path,
        "private_case": private_case_path,
        "player_packets": packets_dir,
    }


def case_to_graph_data(case: MysteryCase) -> dict[str, Any]:
    nodes = [{"id": character.name, "type": "person"} for character in case.characters]
    nodes.append({"id": case.victim.name, "type": "victim"})
    nodes.extend({"id": f"Clue: {clue.title}", "type": "clue"} for clue in case.clues)
    relationships: list[dict[str, str]] = [
        {"source": case.murderer_name, "target": case.victim.name, "type": "murdered"}
    ]
    relationships.extend(
        {"source": item.character_name, "target": case.victim.name, "type": "motive"}
        for item in case.motives
    )
    relationships.extend(
        {"source": item.holder_name, "target": item.about_name, "type": "knows_secret"}
        for item in case.secrets
    )
    relationships.extend(
        {"source": item.character_name, "target": item.witness_name, "type": "corroborated_by"}
        for item in case.whereabouts
        if item.witness_name
    )
    relationships.extend(
        {"source": f"Clue: {clue.title}", "target": name, "type": "implicates"}
        for clue in case.clues
        for name in clue.implicates
    )
    return {"nodes": nodes, "rels": relationships}
