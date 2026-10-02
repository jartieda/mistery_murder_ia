import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

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
    render_act_two_reveal,
    render_character_packet,
    render_player_handout,
    render_solution,
    validate_case,
    write_case_files,
)
from mm_graph import draw_case_graph


def sample_case() -> MysteryCase:
    characters = [
        Character(name="Mira Vale", role="Archivist", biography="Mira catalogues the estate's private letters and knows its hidden history.", gender="female"),
        Character(name="Ezra Cole", role="Gardener", biography="Ezra has tended the grounds for years and can reach every locked outbuilding.", gender="male"),
        Character(name="Noor Bell", role="Composer", biography="Noor was invited to perform at the estate and has a disputed claim to its music collection.", gender="female"),
    ]
    return MysteryCase(
        setting="A storm-bound country estate",
        introduction="During a private weekend at the estate, a guest is found dead after the lights fail.",
        characters=characters,
        victim=Character(name="Rowan Vale", role="Host", biography="Rowan inherited the estate and planned to sell its collection the next morning.", gender="nonbinary"),
        murderer_name="Mira Vale",
        murder_time="22:15",
        murder_location="The locked archive",
        weapon_name="blue-and-gold porcelain vase",
        weapon_owner_name="Mira Vale",
        weapon_origin="Mira's private study beside the archive",
        weapon_signature="a crescent-shaped chip in its cobalt glaze",
        incident="Rowan was discovered in the archive shortly after the storm cut power across the estate.",
        motives=[
            Motive(character_name="Mira Vale", reason="Rowan planned to destroy letters that could expose Mira's forged catalog entries."),
            Motive(character_name="Ezra Cole", reason="Rowan intended to dismiss Ezra and sell the gardens to a developer."),
            Motive(character_name="Noor Bell", reason="Rowan refused to return a score Noor believed had been stolen from her family."),
        ],
        secrets=[
            Secret(holder_name="Mira Vale", about_name="Ezra Cole", fact="Ezra had searched the east greenhouse after closing time and carried soil into the house."),
            Secret(holder_name="Ezra Cole", about_name="Noor Bell", fact="Noor had copied the disputed score before Rowan announced the sale."),
            Secret(holder_name="Noor Bell", about_name="Mira Vale", fact="Mira had requested a duplicate key to the archive earlier that week."),
        ],
        whereabouts=[
            Whereabouts(character_name="Mira Vale", account="Mira says she was in the reading room reviewing the inventory.", location="The reading room", start_time="22:00", end_time="22:30"),
            Whereabouts(character_name="Ezra Cole", account="Ezra says he was checking storm damage near the glasshouse.", location="The main gallery", start_time="22:00", end_time="22:30", witness_name="Noor Bell", witnessed_start_time="22:00", witnessed_end_time="22:10"),
            Whereabouts(character_name="Noor Bell", account="Noor says she was in the music room packing her instruments.", location="The main gallery", start_time="22:00", end_time="22:30", witness_name="Ezra Cole", witnessed_start_time="22:00", witnessed_end_time="22:10"),
        ],
        clues=[
            Clue(title="A damp key tag", description="A key tag from the archive was found beside the rain-soaked service entrance.", implicates=["Mira Vale", "Ezra Cole"], act="I"),
            Clue(title="The torn inventory", description="A torn inventory page is missing the record for one letter Rowan planned to sell.", implicates=["Mira Vale", "Noor Bell"], act="II"),
            Clue(title="The broken vase fragment", description="A porcelain shard was found embedded in the victim's hair.", implicates=["Mira Vale", "Noor Bell"], act="II", weapon_match=True),
        ],
        solution="Mira used the duplicate key to enter during the blackout and killed Rowan before returning to the reading room. The key tag and altered inventory reveal her motive, while the greenhouse soil and competing claims keep the other suspects plausible.",
    )


class CaseValidationTests(unittest.TestCase):
    def test_generation_reports_attempt_validation_and_retry_stages(self) -> None:
        invalid_case = sample_case().model_copy(update={"murderer_name": "Unknown Suspect"})
        structured_model = Mock()
        structured_model.invoke.side_effect = [invalid_case, sample_case()]
        model = Mock()
        model.with_structured_output.return_value = structured_model
        progress: list[str] = []

        with patch("case_generation.get_model", return_value=model):
            case = generate_case(3, progress_callback=progress.append)

        self.assertEqual(case.murderer_name, "Mira Vale")
        self.assertIn("attempt 1/3", progress[0])
        self.assertIn("Checking character references", progress[1])
        self.assertIn("retrying", progress[2])
        self.assertIn("attempt 2/3", progress[3])
        self.assertIn("passed all consistency checks", progress[-1])

    def test_generation_prompt_receives_language_and_gender_count(self) -> None:
        structured_model = Mock()
        structured_model.invoke.return_value = sample_case()
        model = Mock()
        model.with_structured_output.return_value = structured_model

        with patch("case_generation.get_model", return_value=model):
            generate_case(3, language="Spanish", female_characters=2)

        prompt = structured_model.invoke.call_args.args[0]
        self.assertIn("in Spanish", prompt)
        self.assertIn("exactly 2 female player characters", prompt)
        self.assertIn("weapon signature", prompt)
        self.assertIn("exact interval they directly observed", prompt)

    def test_generation_retries_when_female_count_does_not_match(self) -> None:
        invalid_case = sample_case()
        characters = list(invalid_case.characters)
        characters[2] = characters[2].model_copy(update={"gender": "male"})
        invalid_case = invalid_case.model_copy(update={"characters": characters})
        structured_model = Mock()
        structured_model.invoke.side_effect = [invalid_case, sample_case()]
        model = Mock()
        model.with_structured_output.return_value = structured_model
        progress: list[str] = []

        with patch("case_generation.get_model", return_value=model):
            case = generate_case(3, progress_callback=progress.append, female_characters=2)

        self.assertEqual(sum(character.gender == "female" for character in case.characters), 2)
        self.assertEqual(structured_model.invoke.call_count, 2)
        self.assertTrue(any("retrying" in message for message in progress))

    def test_exact_female_player_count_is_validated(self) -> None:
        self.assertEqual(validate_case(sample_case(), 3, requested_female_characters=2), [])
        errors = validate_case(sample_case(), 3, requested_female_characters=1)

        self.assertTrue(any("Expected 1 female player characters; got 2" in error for error in errors))

    def test_female_count_must_fit_player_cast(self) -> None:
        with self.assertRaisesRegex(ValueError, "female_characters must be between"):
            generate_case(3, female_characters=4)

    def test_whereabouts_must_cover_exact_murder_time(self) -> None:
        case = sample_case()
        whereabouts = list(case.whereabouts)
        whereabouts[0] = whereabouts[0].model_copy(update={"start_time": "22:20"})
        invalid_case = case.model_copy(update={"whereabouts": whereabouts})

        self.assertTrue(
            any("must cover the murder time" in error for error in validate_case(invalid_case, 3))
        )

    def test_murderer_cannot_have_a_witness_covering_death_time(self) -> None:
        case = sample_case()
        whereabouts = list(case.whereabouts)
        whereabouts[0] = whereabouts[0].model_copy(
            update={
                "witness_name": "Ezra Cole",
                "witnessed_start_time": "22:10",
                "witnessed_end_time": "22:20",
                "location": "The main gallery",
            }
        )
        invalid_case = case.model_copy(update={"whereabouts": whereabouts})

        self.assertTrue(
            any("murderer must not have a witness" in error for error in validate_case(invalid_case, 3))
        )

    def test_witness_interval_must_match_both_locations(self) -> None:
        case = sample_case()
        whereabouts = list(case.whereabouts)
        whereabouts[2] = whereabouts[2].model_copy(update={"location": "The music room"})
        invalid_case = case.model_copy(update={"whereabouts": whereabouts})

        self.assertTrue(
            any("same stated location" in error for error in validate_case(invalid_case, 3))
        )

    def test_act_two_forensic_weapon_match_is_required(self) -> None:
        case = sample_case()
        clues = [clue.model_copy(update={"weapon_match": False}) for clue in case.clues]
        invalid_case = case.model_copy(update={"clues": clues})

        self.assertTrue(
            any("Exactly one Act II clue" in error for error in validate_case(invalid_case, 3))
        )

    def test_gemini_uses_json_schema_without_afc(self) -> None:
        model = get_model()
        structured_model = model.with_structured_output(
            MysteryCase,
            method="json_schema",
        )

        self.assertTrue(model.model_kwargs["automatic_function_calling"]["disable"])
        self.assertEqual(structured_model.steps[0].kwargs["response_mime_type"], "application/json")
        self.assertNotIn("tools", structured_model.steps[0].kwargs)

    def test_valid_case_passes_cross_reference_checks(self) -> None:
        self.assertEqual(validate_case(sample_case(), requested_count=3), [])

    def test_unknown_witness_is_rejected(self) -> None:
        case = sample_case()
        whereabouts = list(case.whereabouts)
        whereabouts[0] = whereabouts[0].model_copy(update={"witness_name": "Unknown Person"})
        invalid_case = case.model_copy(update={"whereabouts": whereabouts})

        self.assertTrue(any("Unknown whereabouts witness" in error for error in validate_case(invalid_case, 3)))

    def test_direct_culprit_disclosure_is_rejected(self) -> None:
        case = sample_case()
        invalid_case = case.model_copy(update={"introduction": "Mira Vale is the murderer."})

        self.assertTrue(any("must not directly identify" in error for error in validate_case(invalid_case, 3)))

    def test_player_handout_does_not_contain_facilitator_solution(self) -> None:
        case = sample_case()
        handout = render_player_handout(case)

        self.assertNotIn(case.solution, handout)
        self.assertNotIn("Murderer:", handout)
        self.assertIn("Rowan Vale", handout)
        self.assertIn("Act I Clues", handout)
        self.assertIn("Act I", handout)
        self.assertIn("Act II", handout)
        self.assertIn("Resolution", handout)
        self.assertIn("A damp key tag", handout)
        self.assertNotIn("The torn inventory", handout)
        self.assertIn("reveal the secret", handout)
        self.assertIn("reveal the motive on their private sheet", handout)
        self.assertIn("state what you witnessed", handout)

    def test_act_two_clues_are_a_separate_reveal(self) -> None:
        reveal = render_act_two_reveal(sample_case())

        self.assertIn("The torn inventory", reveal)
        self.assertIn("The broken vase fragment", reveal)
        self.assertIn("cobalt glaze", reveal)
        self.assertIn("private study", reveal)
        self.assertNotIn("A damp key tag", reveal)

    def test_spanish_language_translates_all_fixed_player_instructions(self) -> None:
        case = sample_case()
        handout = render_player_handout(case, "Spanish")
        role_packet = render_character_packet(case, case.characters[1], "es")
        act_two = render_act_two_reveal(case, "Español")
        solution = render_solution(case, "Spanish")

        self.assertIn("## Cómo jugar", handout)
        self.assertIn("Hora estimada de la muerte", handout)
        self.assertIn("Acto I: Presentaciones", handout)
        self.assertIn("Acto II: Pruebas", handout)
        self.assertIn("## Resolución", handout)
        self.assertNotIn("How to Play", handout)
        self.assertNotIn("Act I:", handout)
        self.assertIn("Ficha privada", role_packet)
        self.assertIn("revelar el motivo de su ficha", role_packet)
        self.assertIn("Revela este secreto", role_packet)
        self.assertIn("Movimientos que presenciaste", role_packet)
        self.assertIn("cuenta públicamente lo que presenciaste", role_packet)
        self.assertNotIn("Whereabouts you witnessed", role_packet)
        self.assertIn("Acto II: Nuevas pruebas", act_two)
        self.assertIn("Solución para quien dirige la partida", solution)
        self.assertIn("Asesino:", solution)

    def test_case_files_use_selected_language_for_all_markdown(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            paths = write_case_files(sample_case(), temporary_directory, language="Spanish")

            self.assertIn("Cómo jugar", paths["player_handout"].read_text(encoding="utf-8"))
            self.assertIn("Acto II", paths["act_two_reveal"].read_text(encoding="utf-8"))
            self.assertIn("Solución para quien dirige", paths["solution"].read_text(encoding="utf-8"))
            packet = next(paths["player_packets"].glob("*.md")).read_text(encoding="utf-8")
            self.assertIn("Ficha privada", packet)

    def test_private_packet_and_solution_include_private_facts(self) -> None:
        case = sample_case()
        mira_packet = render_character_packet(case, case.characters[0])
        ezra_packet = render_character_packet(case, case.characters[1])
        facilitator_solution = render_solution(case)

        self.assertIn("forged catalog entries", mira_packet)
        self.assertIn("Reveal this secret during Act I or Act II", mira_packet)
        self.assertIn("Whereabouts you witnessed", ezra_packet)
        self.assertIn("Noor Bell", ezra_packet)
        self.assertIn("22:00–22:30", ezra_packet)
        self.assertIn("22:00–22:10", ezra_packet)
        self.assertIn("The main gallery", ezra_packet)
        self.assertIn("publicly state what you witnessed", ezra_packet)
        self.assertIn("Mira Vale", facilitator_solution)
        self.assertIn("a crescent-shaped chip in its cobalt glaze", facilitator_solution)
        self.assertIn("Murderer:", facilitator_solution)

    def test_every_player_is_the_subject_of_one_other_players_secret(self) -> None:
        self.assertEqual(validate_case(sample_case(), requested_count=3), [])

        case = sample_case()
        secrets = list(case.secrets)
        secrets[0] = secrets[0].model_copy(update={"about_name": "Mira Vale"})
        invalid_case = case.model_copy(update={"secrets": secrets})
        errors = validate_case(invalid_case, requested_count=3)

        self.assertTrue(any("exactly one secret about every player" in error for error in errors))

    def test_graph_uses_canonical_relationships(self) -> None:
        graph_data = case_to_graph_data(sample_case())

        self.assertIn(
            {"source": "Mira Vale", "target": "Rowan Vale", "type": "murdered"},
            graph_data["rels"],
        )

    def test_private_graph_renders_to_png(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "case.private.png"
            rendered_path = draw_case_graph(sample_case(), output_path, language="Spanish")

            self.assertEqual(rendered_path, output_path)
            self.assertGreater(output_path.stat().st_size, 0)

    def test_case_files_are_written_with_separate_audiences(self) -> None:
        case = sample_case()
        with TemporaryDirectory() as temporary_directory:
            paths = write_case_files(case, temporary_directory)

            self.assertTrue(paths["player_handout"].is_file())
            self.assertTrue(paths["act_two_reveal"].is_file())
            self.assertTrue(paths["solution"].is_file())
            self.assertTrue(paths["private_case"].is_file())
            self.assertEqual(len(list(paths["player_packets"].glob("*.md"))), 3)
            self.assertNotIn(case.solution, paths["player_handout"].read_text(encoding="utf-8"))
            self.assertIn("The torn inventory", paths["act_two_reveal"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
