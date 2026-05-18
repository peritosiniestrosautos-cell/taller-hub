import unittest

import pandas as pd

from modules.imprevistos_visualizations import (
    _filtrar_demora_definicion_por_periodo_y_cia,
    _format_month_year_label,
    _preparar_reporte_cambio_repuesto_mes,
    _preparar_reporte_demora_definicion,
)


class ImprevistosVisualizationsTests(unittest.TestCase):
    def test_format_month_year_label_usa_el_anio_real_del_registro(self):
        self.assertEqual(_format_month_year_label(3, 2026), "March 2026")

    def test_prepara_reporte_cambio_repuesto_filtra_mes_y_columnas_solicitadas(self):
        df = pd.DataFrame(
            [
                {
                    "PLACA": " aaa111 ",
                    "COMPAÑIA_DE_SEGUROS": "SURA",
                    "IMPREVISTO": "farola rh",
                    "CAUSAL": "NO COTIZADO",
                    "ACCION": "CAMBIO",
                    "AÑO": 2026,
                    "MES": 3,
                },
                {
                    "PLACA": "BBB222",
                    "COMPAÑIA_DE_SEGUROS": "ALLIANZ",
                    "IMPREVISTO": "bomper",
                    "CAUSAL": "NO VISIBLE",
                    "ACCION": "CAMBIO",
                    "AÑO": 2026,
                    "MES": 4,
                },
                {
                    "PLACA": "CCC333",
                    "COMPAÑIA_DE_SEGUROS": "BOLIVAR",
                    "IMPREVISTO": "puerta",
                    "CAUSAL": "AJUSTE",
                    "ACCION": "AJUSTE",
                    "AÑO": 2026,
                    "MES": 3,
                },
            ]
        )

        result = _preparar_reporte_cambio_repuesto_mes(df, año=2026, mes=3)

        self.assertEqual(list(result.columns), ["PLACA", "LINEA", "CIA", "IMPREVISTO", "CAUSAL"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0].to_dict(), {
            "PLACA": "AAA111",
            "LINEA": "",
            "CIA": "SURA",
            "IMPREVISTO": "FAROLA RH",
            "CAUSAL": "NO COTIZADO",
        })

    def test_prepara_reporte_cambio_repuesto_acepta_columna_compania_sin_tilde(self):
        df = pd.DataFrame(
            [
                {
                    "PLACA": "DDD444",
                    "COMPAÑIA_DE_SEGUROS": "MAPFRE",
                    "IMPREVISTO": "persiana",
                    "CAUSAL": "PREDESARME",
                    "ACCION": "CAMBIO REPUESTO",
                    "AÑO": 2025,
                    "MES": 12,
                }
            ]
        )

        result = _preparar_reporte_cambio_repuesto_mes(df, año=2025, mes=12)

        self.assertEqual(result.iloc[0]["CIA"], "MAPFRE")

    def test_filtra_demora_definicion_por_cia_mes_trimestre_y_anio(self):
        df = pd.DataFrame(
            [
                {"AÑO": 2026, "MES": 1, "COMPAÑIA_DE_SEGUROS": "SURA", "PLACA": "AAA111"},
                {"AÑO": 2026, "MES": 2, "COMPAÑIA_DE_SEGUROS": "SURA", "PLACA": "BBB222"},
                {"AÑO": 2026, "MES": 4, "COMPAÑIA_DE_SEGUROS": "ALLIANZ", "PLACA": "CCC333"},
                {"AÑO": 2025, "MES": 1, "COMPAÑIA_DE_SEGUROS": "SURA", "PLACA": "DDD444"},
            ]
        )

        mes = _filtrar_demora_definicion_por_periodo_y_cia(df, cia="SURA", año=2026, mes=1)
        trimestre = _filtrar_demora_definicion_por_periodo_y_cia(df, cia="Todas", año=2026, trimestre="Q1")
        anio = _filtrar_demora_definicion_por_periodo_y_cia(df, cia="SURA", año=2026)

        self.assertEqual(mes["PLACA"].tolist(), ["AAA111"])
        self.assertEqual(set(trimestre["PLACA"].tolist()), {"AAA111", "BBB222"})
        self.assertEqual(set(anio["PLACA"].tolist()), {"AAA111", "BBB222"})

    def test_prepara_reporte_demora_definicion_incluye_resumen_y_detalle(self):
        df = pd.DataFrame(
            [
                {
                    "PLACA": " aaa111 ",
                    "SINIESTRO": "s1",
                    "COMPAÑIA_DE_SEGUROS": "SURA",
                    "ESTATUS": "AUTORIZADO",
                    "FECHA_INGR": "01/01/2026",
                    "FECHA_AUTO": "04/01/2026",
                    "IMPREVISTO": "farola",
                    "ACCION": "CAMBIO",
                    "CAUSAL": "NO COTIZADO",
                },
                {
                    "PLACA": "BBB222",
                    "SINIESTRO": "S2",
                    "COMPAÑIA_DE_SEGUROS": "SURA",
                    "ESTATUS": "RECHAZADO",
                    "FECHA_INGR": "10/01/2026",
                    "FECHA_AUTO": "15/01/2026",
                    "IMPREVISTO": "bomper",
                    "ACCION": "CAMBIO",
                    "CAUSAL": "PREDESARME",
                },
                {
                    "PLACA": "BBB222",
                    "SINIESTRO": "S2",
                    "COMPAÑIA_DE_SEGUROS": "SURA",
                    "ESTATUS": "RECHAZADO",
                    "FECHA_INGR": "10/01/2026",
                    "FECHA_AUTO": "20/01/2026",
                    "IMPREVISTO": "duplicado",
                    "ACCION": "CAMBIO",
                    "CAUSAL": "PREDESARME",
                },
            ]
        )

        resumen, detalle = _preparar_reporte_demora_definicion(df, "Mes 01/2026")

        self.assertEqual(
            list(resumen.columns),
            ["PERIODO", "CIA", "ESTATUS", "PROMEDIO_DEMORA_DIAS", "CONTEO"],
        )
        self.assertEqual(
            list(detalle.columns),
            [
                "PERIODO", "PLACA", "SINIESTRO", "CIA", "ESTATUS",
                "FECHA_INGR", "FECHA_AUTO", "DEMORA_DIAS", "IMPREVISTO",
                "ACCION", "CAUSAL",
            ],
        )
        self.assertEqual(len(detalle), 2)
        self.assertEqual(set(detalle["DEMORA_DIAS"].tolist()), {3, 5})
        self.assertEqual(
            set(zip(resumen["ESTATUS"].tolist(), resumen["PROMEDIO_DEMORA_DIAS"].tolist())),
            {("AUTORIZADO", 3.0), ("RECHAZADO", 5.0)},
        )


if __name__ == "__main__":
    unittest.main()
