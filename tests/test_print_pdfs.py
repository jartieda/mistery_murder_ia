import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from make_print_pdfs import build_print_pdfs


class PrintPdfTests(unittest.TestCase):
    def test_builds_one_personal_pack_and_act_two_copy_per_player(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "source"
            packets = source / "player_packets"
            packets.mkdir(parents=True)
            (source / "player_handout.md").write_text(
                "# La mansión de la niebla\n\n## Cómo jugar\nInstrucciones comunes para todos los jugadores.\n",
                encoding="utf-8",
            )
            (source / "act_ii_reveal.md").write_text(
                "# Acto II: Nuevas pruebas\n\n## La llave de plata\nUna pista que se entrega al comenzar el segundo acto.\n",
                encoding="utf-8",
            )
            (packets / "01-ana.md").write_text(
                "# Ficha privada: Ana\n\n## Tu secreto\nSolo Ana debe leer este secreto.\n",
                encoding="utf-8",
            )
            (packets / "02-luis.md").write_text(
                "# Ficha privada: Luis\n\n## Tu secreto\nSolo Luis debe leer este secreto.\n",
                encoding="utf-8",
            )

            outputs = build_print_pdfs(source)

            self.assertEqual(len(outputs["players"]), 2)
            self.assertEqual(len(outputs["act_ii"]), 2)
            self.assertTrue(all(path.read_bytes().startswith(b"%PDF-") for path in outputs["players"]))
            self.assertTrue(all(path.read_bytes().startswith(b"%PDF-") for path in outputs["act_ii"]))
            self.assertTrue(any("01-ana-paquete.pdf" in path.name for path in outputs["players"]))
            self.assertTrue(any("02-luis-acto-ii.pdf" in path.name for path in outputs["act_ii"]))

            for player_pdf in outputs["players"]:
                page_count = len(re.findall(rb"/Type\s*/Page\b", player_pdf.read_bytes()))
                self.assertGreaterEqual(page_count, 2)

            index_text = outputs["index"][0].read_text(encoding="utf-8")
            self.assertIn("Copias necesarias de la hoja común: 2", index_text)
            self.assertIn("Copias necesarias de las pistas del Acto II: 2", index_text)


if __name__ == "__main__":
    unittest.main()