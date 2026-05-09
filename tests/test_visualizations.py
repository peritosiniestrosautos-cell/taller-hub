import unittest

import pandas as pd

from modules import visualizations


class VisualizationsTests(unittest.TestCase):
    def test_calculate_accumulated_savings_kpi_ignora_duplicados_y_estatus(self):
        df = pd.DataFrame(
            [
                {"PLACA": "AAA111", "SINIESTRO": "S1", "ESTATUS": "AUTORIZADO", "DIFERENCIA": 100},
                {"PLACA": "AAA111", "SINIESTRO": "S1", "ESTATUS": "AUTORIZADO", "DIFERENCIA": 200},
                {"PLACA": "BBB222", "SINIESTRO": "S2", "ESTATUS": "RECHAZADO", "DIFERENCIA": 300},
            ]
        )

        result = visualizations.calculate_accumulated_savings_kpi(df)

        self.assertEqual(result["total_ahorro"], 600)
        self.assertEqual(result["reparaciones_con_ahorro"], 3)

    def test_format_period_label_admite_mes_y_anio_float(self):
        self.assertEqual(
            visualizations.format_period_label(2.0, 2025.0),
            "02/2025",
        )


if __name__ == "__main__":
    unittest.main()
