import unittest

import pandas as pd

from modules.data_processor import procesar_dataframe


class DateFormatParsingTests(unittest.TestCase):
    def test_procesar_dataframe_usa_formatos_distintos_para_ingreso_y_auto(self):
        df = pd.DataFrame(
            {
                "PLACA": ["ABC123"],
                "FECHA_INGR": ["13/05/2024"],
                "FECHA_AUTO": ["05/06/2024"],
                "ESTATUS": ["Autorizado"],
            }
        )

        procesado = procesar_dataframe(df, fuente="test")

        self.assertEqual(str(procesado.loc[0, "FECHA_INGR"].date()), "2024-05-13")
        self.assertEqual(str(procesado.loc[0, "FECHA_AUTO"].date()), "2024-05-06")


if __name__ == "__main__":
    unittest.main()
