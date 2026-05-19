import io
import unittest

import pandas as pd
from reportlab.platypus import Table

from modules import exporters
from modules.pdf_charts import (
    generar_grafico_ahorro_comparativo_ejecutivo,
    generar_grafico_imprevistos_ejecutivo,
    generar_grafico_tasa_ejecutivo,
)
from modules.pdf_executive_helpers import build_kpi_card
from modules.pdf_narrative import narrativa_introduccion
from modules.pdf_styles import EXEC_COLORS, get_executive_styles


def _make_minimal_df():
    return pd.DataFrame(
        {
            "AÑO": [2026],
            "MES": [3],
            "DIA": [15],
            "PLACA": ["ABC123"],
            "CAUSAL": ["DAÑO OCASIONADO"],
            "ACCION": ["CAMBIO"],
            "IMPREVISTO": ["Test"],
            "DIFERENCIA": [1_000_000],
            "COMPAÑIA_DE_SEGUROS": ["SeguroX"],
            "ESTATUS": ["AUTORIZADO"],
            "FECHA_INGR": ["2026-03-01"],
            "FECHA_AUTO": ["2026-03-05"],
        }
    )


class PdfExporterFormattingTests(unittest.TestCase):
    def test_honorarios_kpi_muestra_solo_la_cifra(self):
        self.assertEqual(
            exporters._format_honorarios_kpi_value(1250000, 18.0),
            "$1,250,000",
        )

    def test_kpi_font_size_se_reduce_dos_puntos_adicionales_para_exportacion_pdf(self):
        self.assertEqual(exporters.PDF_KPI_FONT_SIZE, 10)


class GenerateExecutivePdfReportTests(unittest.TestCase):
    def test_generate_executive_pdf_report_retorna_bytesio(self):
        df = _make_minimal_df()
        result = exporters.generate_executive_pdf_report(df, mes=3, año=2026)
        self.assertIsInstance(result, io.BytesIO)
        self.assertGreater(result.getbuffer().nbytes, 1000)

    def test_generate_executive_pdf_report_con_honorarios(self):
        df = _make_minimal_df()
        result = exporters.generate_executive_pdf_report(
            df, mes=3, año=2026, include_honorarios=True
        )
        self.assertIsInstance(result, io.BytesIO)
        self.assertGreater(len(result.getvalue()), 0)

    def test_generate_executive_pdf_report_sin_honorarios(self):
        df = _make_minimal_df()
        result = exporters.generate_executive_pdf_report(
            df, mes=3, año=2026, include_honorarios=False
        )
        self.assertIsInstance(result, io.BytesIO)

    def test_generate_executive_pdf_report_mes_sin_datos(self):
        df = pd.DataFrame(
            columns=[
                "AÑO",
                "MES",
                "DIA",
                "PLACA",
                "CAUSAL",
                "ACCION",
                "IMPREVISTO",
                "DIFERENCIA",
                "COMPAÑIA_DE_SEGUROS",
                "ESTATUS",
                "FECHA_INGR",
                "FECHA_AUTO",
            ]
        )
        result = exporters.generate_executive_pdf_report(df, mes=3, año=2026)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, io.BytesIO)


class PdfStylesTests(unittest.TestCase):
    def test_pdf_styles_cargan_correctamente(self):
        styles = get_executive_styles()
        self.assertIsInstance(styles, dict)
        self.assertGreaterEqual(len(styles), 15)
        self.assertIn("teal_dark", EXEC_COLORS)
        self.assertIn("teal_chart", EXEC_COLORS)
        self.assertIn("gray_header", EXEC_COLORS)


class PdfExecutiveHelpersTests(unittest.TestCase):
    def test_pdf_executive_helpers_build_kpi_card(self):
        card = build_kpi_card("Ahorro", "$1.000.000", "💰", 100)
        self.assertIsInstance(card, Table)


class PdfChartsTests(unittest.TestCase):
    def test_pdf_charts_retornan_none_sin_datos(self):
        empty_df = pd.DataFrame()
        self.assertIsNone(generar_grafico_imprevistos_ejecutivo(empty_df))
        self.assertIsNone(generar_grafico_tasa_ejecutivo(empty_df))
        self.assertIsNone(
            generar_grafico_ahorro_comparativo_ejecutivo(empty_df, empty_df, ["Ene", "Feb"])
        )


class PdfNarrativeTests(unittest.TestCase):
    def test_pdf_narrative_retorna_lista(self):
        result = narrativa_introduccion("Marzo", 2026, 1_000_000, 200_000, 800_000)
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
