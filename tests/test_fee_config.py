import unittest

import pandas as pd

from modules.fee_config import calculate_fees_per_month


class FeeConfigTests(unittest.TestCase):
    def test_calculate_fees_per_month_usa_todos_los_autorizados_sin_deduplicar(self):
        df = pd.DataFrame(
            [
                {
                    "PLACA": "AAA111",
                    "SINIESTRO": "S1",
                    "ESTATUS": "AUTORIZADO",
                    "DIFERENCIA": 1000,
                    "AÑO": 2025,
                    "MES": 2,
                },
                {
                    "PLACA": "AAA111",
                    "SINIESTRO": "S1",
                    "ESTATUS": "AUTORIZADO",
                    "DIFERENCIA": 9000,
                    "AÑO": 2025,
                    "MES": 2,
                },
                {
                    "PLACA": "BBB222",
                    "SINIESTRO": "S2",
                    "ESTATUS": "RECHAZADO",
                    "DIFERENCIA": 5000,
                    "AÑO": 2025,
                    "MES": 2,
                },
            ]
        )

        config = {
            "global_defaults": {
                "threshold": 15000000,
                "base_percentage": 0.18,
                "premium_percentage": 0.20,
            },
            "talleres": {},
            "hide_fees_presentation": False,
        }

        result = calculate_fees_per_month(df, config)

        self.assertEqual(result["total_savings"], 10000)
        self.assertEqual(result["total_honorarios"], 1800)


if __name__ == "__main__":
    unittest.main()
