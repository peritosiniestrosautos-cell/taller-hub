import unittest

from modules.components import _default_include_honorarios_for_pdf


class ComponentsTests(unittest.TestCase):
    def test_pdf_ejecutivo_incluye_honorarios_por_defecto_aunque_modo_presentacion_oculte(self):
        fee_config = {"hide_fees_presentation": True}

        self.assertTrue(_default_include_honorarios_for_pdf(True, fee_config))

    def test_pdf_tecnico_respeta_modo_presentacion_para_honorarios(self):
        fee_config = {"hide_fees_presentation": True}

        self.assertFalse(_default_include_honorarios_for_pdf(False, fee_config))


if __name__ == "__main__":
    unittest.main()
