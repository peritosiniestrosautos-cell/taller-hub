import unittest
from unittest.mock import patch

import pandas as pd

from modules.sidebar import aplicar_filtros


class SidebarFilterTests(unittest.TestCase):
    def test_aplicar_filtros_de_taller_acepta_ids_seleccionados(self):
        df = pd.DataFrame(
            [
                {"TALLER_ORIGEN": "Renomotriz", "AÑO": 2026, "MES": 3},
                {"TALLER_ORIGEN": "Distrikia", "AÑO": 2026, "MES": 3},
            ]
        )

        with patch("modules.sidebar.get_nombre_taller", side_effect=lambda tid: {"renomotriz": "Renomotriz"}.get(tid, tid)):
            result = aplicar_filtros(df, {"talleres": ["renomotriz"]})

        self.assertEqual(result["TALLER_ORIGEN"].tolist(), ["Renomotriz"])


if __name__ == "__main__":
    unittest.main()
