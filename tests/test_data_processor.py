import unittest

import pandas as pd

from modules.data_processor import procesar_dataframe


class DataProcessorTests(unittest.TestCase):
    def test_procesar_dataframe_descarta_filas_vacias_y_resumen_sin_identidad(self):
        raw = pd.DataFrame(
            [
                {
                    "FECHA INGR": "2025-02-12",
                    "PLACA ": "LRZ187",
                    "SINIESTRO": "148355761_1",
                    "IMPREVISTO": "costado rh",
                    "ACCIÓN": "BITEC",
                    "CAUSAL": "NO COTIZADO",
                    "RECUPERADO": "$ 533,500",
                    "ESTATUS": "AUTORIZADO",
                    "DIA": 12,
                    "MES": 2,
                    "AÑO": 2025,
                },
                {
                    "FECHA INGR": "",
                    "PLACA ": "",
                    "SINIESTRO": "",
                    "IMPREVISTO": "",
                    "ACCIÓN": "",
                    "CAUSAL": "",
                    "RECUPERADO": "$ 156,453,119",
                    "ESTATUS": "",
                    "DIA": "",
                    "MES": "",
                    "AÑO": "",
                },
                {
                    "FECHA INGR": "",
                    "PLACA ": "",
                    "SINIESTRO": "",
                    "IMPREVISTO": "",
                    "ACCIÓN": "",
                    "CAUSAL": "",
                    "RECUPERADO": "",
                    "ESTATUS": "",
                    "DIA": "",
                    "MES": "",
                    "AÑO": "",
                },
            ]
        )

        result = procesar_dataframe(raw, fuente="test")

        self.assertEqual(len(result), 1)
        self.assertEqual(result["DIFERENCIA"].sum(), 533500)


if __name__ == "__main__":
    unittest.main()
