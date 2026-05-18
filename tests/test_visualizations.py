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

    def test_filtrar_top_causales_por_mes_trimestre_y_anio(self):
        df = pd.DataFrame(
            [
                {"AÑO": 2026, "MES": 1, "CAUSAL": "NO COTIZADO", "DIFERENCIA": 100},
                {"AÑO": 2026, "MES": 2, "CAUSAL": "PREDESARME", "DIFERENCIA": 200},
                {"AÑO": 2026, "MES": 4, "CAUSAL": "DIGITACION", "DIFERENCIA": 300},
                {"AÑO": 2025, "MES": 1, "CAUSAL": "NO COTIZADO", "DIFERENCIA": 400},
            ]
        )

        mes = visualizations._filtrar_df_causales_por_periodo(df, "Mes", "2026-01")
        trimestre = visualizations._filtrar_df_causales_por_periodo(df, "Trimestre", "2026-T1")
        anio = visualizations._filtrar_df_causales_por_periodo(df, "Año", "2026")

        self.assertEqual(mes["DIFERENCIA"].sum(), 100)
        self.assertEqual(trimestre["DIFERENCIA"].sum(), 300)
        self.assertEqual(anio["DIFERENCIA"].sum(), 600)

    def test_filtrar_top_causales_por_multiples_anios(self):
        df = pd.DataFrame(
            [
                {"AÑO": 2026, "MES": 1, "CAUSAL": "NO COTIZADO", "DIFERENCIA": 100},
                {"AÑO": 2026, "MES": 2, "CAUSAL": "PREDESARME", "DIFERENCIA": 200},
                {"AÑO": 2025, "MES": 1, "CAUSAL": "DIGITACION", "DIFERENCIA": 300},
                {"AÑO": 2024, "MES": 3, "CAUSAL": "NO COTIZADO", "DIFERENCIA": 400},
            ]
        )

        # Múltiples años
        multi_anio = visualizations._filtrar_df_causales_por_periodo(df, "Año", ["2026", "2024"])
        self.assertEqual(multi_anio["DIFERENCIA"].sum(), 700)
        self.assertEqual(len(multi_anio), 3)

        # Un solo año (lista con un elemento)
        single_anio = visualizations._filtrar_df_causales_por_periodo(df, "Año", ["2025"])
        self.assertEqual(single_anio["DIFERENCIA"].sum(), 300)

        # Múltiples meses
        multi_mes = visualizations._filtrar_df_causales_por_periodo(df, "Mes", ["2026-01", "2025-01"])
        self.assertEqual(multi_mes["DIFERENCIA"].sum(), 400)
        self.assertEqual(len(multi_mes), 2)

        # Múltiples trimestres
        multi_trim = visualizations._filtrar_df_causales_por_periodo(df, "Trimestre", ["2026-T1", "2024-T1"])
        self.assertEqual(multi_trim["DIFERENCIA"].sum(), 700)

    def test_period_label_from_key_con_multiples_periodos(self):
        # Hasta 3 labels se muestran completos
        label_tres = visualizations._period_label_from_key("Año", ["2026", "2025", "2024"])
        self.assertEqual(label_tres, "Año 2026, Año 2025, Año 2024")

        # Dos años
        label_dos = visualizations._period_label_from_key("Año", ["2026", "2025"])
        self.assertEqual(label_dos, "Año 2026, Año 2025")

        # Un solo año
        label_uno = visualizations._period_label_from_key("Año", ["2026"])
        self.assertEqual(label_uno, "Año 2026")

        # Año como string simple (backward compat)
        label_str = visualizations._period_label_from_key("Año", "2026")
        self.assertEqual(label_str, "Año 2026")

        # Más de 3 se resumen
        label_cuatro = visualizations._period_label_from_key("Año", ["2026", "2025", "2024", "2023"])
        self.assertEqual(label_cuatro, "Año 2026, Año 2025 y 2 más")

    def test_preparar_reporte_top_causales_incluye_resumen_y_detalle(self):
        df = pd.DataFrame(
            [
                {
                    "AÑO": 2026,
                    "MES": 1,
                    "PLACA": " aaa111 ",
                    "COMPAÑIA_DE_SEGUROS": "SURA",
                    "IMPREVISTO": "farola",
                    "ACCION": "CAMBIO",
                    "CAUSAL": "NO COTIZADO",
                    "DIFERENCIA": 100,
                    "ESTATUS": "AUTORIZADO",
                },
                {
                    "AÑO": 2026,
                    "MES": 1,
                    "PLACA": "BBB222",
                    "COMPAÑIA_DE_SEGUROS": "SURA",
                    "IMPREVISTO": "bomper",
                    "ACCION": "CAMBIO",
                    "CAUSAL": "NO COTIZADO",
                    "DIFERENCIA": 250,
                    "ESTATUS": "RECHAZADO",
                },
            ]
        )

        resumen, detalle = visualizations._preparar_reporte_top_causales_ahorro(
            df,
            "Mes 01/2026",
        )

        self.assertEqual(
            list(resumen.columns),
            ["PERIODO", "CAUSAL", "RECUPERACION", "PORCENTAJE_EQUIVALENTE", "VEHICULOS"],
        )
        self.assertEqual(resumen.iloc[0]["RECUPERACION"], 350)
        self.assertEqual(resumen.iloc[0]["PORCENTAJE_EQUIVALENTE"], 100.0)
        self.assertEqual(resumen.iloc[0]["VEHICULOS"], 2)
        self.assertEqual(
            list(detalle.columns),
            [
                "PERIODO", "PLACA", "CIA", "IMPREVISTO", "ACCION",
                "CAUSAL", "DIFERENCIA", "ESTATUS",
            ],
        )
        self.assertEqual(detalle.iloc[0]["PLACA"], "BBB222")
        self.assertEqual(set(detalle["PLACA"].tolist()), {"AAA111", "BBB222"})


if __name__ == "__main__":
    unittest.main()
