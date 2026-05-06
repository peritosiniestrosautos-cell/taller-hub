import unittest

from modules import exporters


class PdfExporterFormattingTests(unittest.TestCase):
    def test_honorarios_kpi_muestra_solo_la_cifra(self):
        self.assertEqual(
            exporters._format_honorarios_kpi_value(1250000, 18.0),
            "$1,250,000",
        )

    def test_kpi_font_size_se_reduce_dos_puntos_adicionales_para_exportacion_pdf(self):
        self.assertEqual(exporters.PDF_KPI_FONT_SIZE, 10)


if __name__ == "__main__":
    unittest.main()
