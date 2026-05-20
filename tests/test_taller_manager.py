import unittest

from modules.taller_manager import _get_default_talleres


class TallerManagerTests(unittest.TestCase):
    def test_default_talleres_incluye_talleres_base(self):
        talleres = _get_default_talleres()

        expected = {
            "autozen": "https://docs.google.com/spreadsheets/d/1IJetXo3teQCw1iTVGR1ky-GDMMRoUd-D/edit?gid=1340033279#gid=1340033279",
            "taller_1": "https://docs.google.com/spreadsheets/d/1WgrIeUkrmvgecDP5hKaOtXjrmxsGdjSzMrari4LbvAI/edit?gid=0#gid=0",
            "renomotriz": "https://docs.google.com/spreadsheets/d/1PvdZBQCFBBFSgKhjfFkHFXs1jO5nJIUvXBSlX0pXUZg/edit?gid=0#gid=0",
            "colision_express": "https://docs.google.com/spreadsheets/d/1ScPJ0hsqdwS2Lwo2KujfzCKJKsrwRxvbkdVghk4sVS0/edit?gid=0#gid=0",
        }

        self.assertEqual(set(talleres), set(expected))
        for taller_id, sheet_url in expected.items():
            self.assertEqual(talleres[taller_id]["id"], taller_id)
            self.assertEqual(talleres[taller_id]["sheet_url"], sheet_url)

    def test_default_talleres_solo_distrikia_activo(self):
        talleres = _get_default_talleres()

        activos = {
            taller_id
            for taller_id, config in talleres.items()
            if config.get("activo", False)
        }

        self.assertEqual(activos, {"taller_1"})


if __name__ == "__main__":
    unittest.main()
