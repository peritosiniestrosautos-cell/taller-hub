import io
import unittest
from unittest.mock import patch

import matplotlib.axes
import pandas as pd
from reportlab.platypus import Table

from modules import exporters
from modules.pdf_charts import (
    generar_grafico_ahorro_comparativo_ejecutivo,
    generar_grafico_ahorro_comparativo_historico_ejecutivo,
    generar_grafico_demora_definicion_ejecutivo,
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

    def test_generate_executive_pdf_report_alinea_gestion_imprevistos_con_grafico_cambio(self):
        df = pd.DataFrame(
            {
                "AÑO": [2026, 2026, 2026, 2026],
                "MES": [2, 3, 3, 3],
                "DIA": [10, 11, 12, 13],
                "PLACA": ["FEB111", "MAR111", "MAR222", "MAR333"],
                "SINIESTRO": ["S1", "S2", "S3", "S4"],
                "CAUSAL": ["NO COTIZADO", "NO COTIZADO", "PREDESARME", "DAÑO EN PROCESO"],
                "ACCION": ["CAMBIO", "CAMBIO", "CAMBIO", "REPARACIÓN"],
                "IMPREVISTO": ["farola", "bumper", "capo", "pintura"],
                "DIFERENCIA": [100_000, 200_000, 300_000, 400_000],
                "COMPAÑIA_DE_SEGUROS": ["SURA", "SURA", "SURA", "SURA"],
                "ESTATUS": ["AUTORIZADO", "AUTORIZADO", "AUTORIZADO", "AUTORIZADO"],
                "FECHA_INGR": ["2026-02-01", "2026-03-01", "2026-03-02", "2026-03-03"],
                "FECHA_AUTO": ["2026-02-05", "2026-03-05", "2026-03-06", "2026-03-07"],
            }
        )

        captured = {}

        def fake_narrativa_gestion_imprevistos(cantidad_mes_actual, cantidad_mes_anterior):
            captured["args"] = (cantidad_mes_actual, cantidad_mes_anterior)
            return []

        with patch.object(exporters, "narrativa_gestion_imprevistos", side_effect=fake_narrativa_gestion_imprevistos):
            exporters.generate_executive_pdf_report(df, mes=3, año=2026)

        self.assertEqual(captured["args"], (2, 1))

    def test_generate_executive_pdf_report_grafica_ahorro_mes_comparativa_hasta_periodo(self):
        df = pd.DataFrame(
            {
                "AÑO": [2025, 2025, 2026, 2026, 2026, 2026, 2026],
                "MES": [11, 12, 1, 2, 3, 4, 5],
                "DIA": [1, 1, 1, 1, 1, 1, 1],
                "PLACA": ["A111", "A222", "A333", "A444", "A555", "A666", "A777"],
                "SINIESTRO": ["S1", "S2", "S3", "S4", "S5", "S6", "S7"],
                "CAUSAL": ["NO COTIZADO"] * 7,
                "ACCION": ["CAMBIO"] * 7,
                "IMPREVISTO": ["pieza"] * 7,
                "DIFERENCIA": [110, 120, 10, 20, 30, 40, 50],
                "COMPAÑIA_DE_SEGUROS": ["SURA"] * 7,
                "ESTATUS": ["AUTORIZADO"] * 7,
                "FECHA_INGR": ["2025-11-01", "2025-12-01", "2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01"],
                "FECHA_AUTO": ["2025-11-02", "2025-12-02", "2026-01-02", "2026-02-02", "2026-03-02", "2026-04-02", "2026-05-02"],
            }
        )

        captured = {}

        def fake_grafico_ahorro_comparativo(df_grafico, *args, **kwargs):
            captured["periodos"] = df_grafico["periodo"].tolist()
            captured["valores"] = df_grafico["DIFERENCIA"].tolist()
            return None

        with patch.object(
            exporters,
            "generar_grafico_ahorro_comparativo_historico_ejecutivo",
            side_effect=fake_grafico_ahorro_comparativo,
        ):
            exporters.generate_executive_pdf_report(df, mes=4, año=2026)

        self.assertEqual(
            captured["periodos"],
            ["Nov 2025", "Dic 2025", "Ene 2026", "Feb 2026", "Mar 2026", "Abr 2026"],
        )
        self.assertEqual(captured["valores"], [110, 120, 10, 20, 30, 40])


class PdfSavingsComparisonTests(unittest.TestCase):
    def test_comparativo_trimestral_sin_historico_homologo_no_falla(self):
        df = pd.DataFrame(
            {
                "AÑO": [2026, 2026, 2026, 2026],
                "MES": [1, 2, 4, 5],
                "DIFERENCIA": [100_000, 200_000, 150_000, 300_000],
            }
        )

        mensual, trimestral = exporters._calcular_comparativo_ahorro_pdf(df)

        self.assertFalse(mensual.empty)
        self.assertTrue(trimestral.empty)


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
        self.assertIsNone(generar_grafico_demora_definicion_ejecutivo(empty_df))

    def test_grafico_demora_definicion_ejecutivo_retorna_png(self):
        df = pd.DataFrame(
            {
                "COMPAÑIA_DE_SEGUROS": ["SeguroA", "SeguroB"],
                "promedio_demora_AUTORIZADO": [5.2, 3.1],
                "promedio_demora_RECHAZADO": [8.5, 4.0],
                "conteo_AUTORIZADO": [10, 5],
                "conteo_RECHAZADO": [3, 2],
            }
        )

        result = generar_grafico_demora_definicion_ejecutivo(df)

        self.assertIsInstance(result, io.BytesIO)
        self.assertGreater(result.getbuffer().nbytes, 1000)

    def test_grafico_ahorro_comparativo_historico_retorna_png(self):
        df = pd.DataFrame(
            {
                "AÑO": [2025, 2025, 2026, 2026],
                "MES": [11, 12, 1, 2],
                "DIFERENCIA": [100_000, 120_000, 80_000, 90_000],
            }
        )

        result = generar_grafico_ahorro_comparativo_historico_ejecutivo(df)

        self.assertIsInstance(result, io.BytesIO)
        self.assertGreater(result.getbuffer().nbytes, 1000)

    def test_grafico_ahorro_comparativo_historico_etiqueta_puntos_con_valor(self):
        df = pd.DataFrame(
            {
                "AÑO": [2025, 2025, 2026],
                "MES": [1, 2, 1],
                "DIFERENCIA": [100_000, 120_000, 80_000],
            }
        )

        with patch.object(matplotlib.axes.Axes, "annotate", autospec=True) as annotate_mock:
            result = generar_grafico_ahorro_comparativo_historico_ejecutivo(df)

        self.assertIsInstance(result, io.BytesIO)
        self.assertGreaterEqual(annotate_mock.call_count, 3)


class PdfNarrativeTests(unittest.TestCase):
    def test_pdf_narrative_retorna_lista(self):
        result = narrativa_introduccion("Marzo", 2026, 1_000_000, 200_000, 800_000)
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
