"""Testes unitários do handler (rodam sem SAM e sem Docker): python3 -m unittest discover -s tests"""
import importlib
import json
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hello_world"))
import app  # noqa: E402


def evento(corpo):
    """Evento mínimo no formato que o API Gateway (proxy) entrega ao Lambda."""
    return {"httpMethod": "POST", "path": "/guias",
            "headers": {"Content-Type": "application/json"},
            "body": None if corpo is None else json.dumps(corpo)}


class HandlerTest(unittest.TestCase):
    def setUp(self):
        importlib.reload(app)   # simula "ambiente novo" (cold start): contador volta a 0

    def test_gera_guia_com_os_dados_do_pedido(self):
        r = app.lambda_handler(evento({"requisicaoId": "R-001", "hospital": "H-Recife",
                                       "bolsas": ["O-NEG-0142"]}), None)
        self.assertEqual(r["statusCode"], 201)
        guia = json.loads(r["body"])
        self.assertEqual(guia["guia"], "G-R-001")
        self.assertEqual(guia["hospital"], "H-Recife")
        self.assertEqual(guia["bolsas"], ["O-NEG-0142"])

    def test_sem_requisicaoId_devolve_400(self):
        r = app.lambda_handler(evento({"hospital": "H-Caruaru"}), None)
        self.assertEqual(r["statusCode"], 400)
        self.assertIn("requisicaoId", json.loads(r["body"])["erro"])

    def test_body_ausente_devolve_400(self):
        self.assertEqual(app.lambda_handler(evento(None), None)["statusCode"], 400)

    def test_contador_so_sobe_quando_o_ambiente_e_reaproveitado(self):
        """Mesmo módulo carregado = ambiente reaproveitado (warm): contador 1, 2, 3."""
        vistos = [json.loads(app.lambda_handler(evento({"requisicaoId": "R-002"}), None)["body"])
                  ["invocacaoNesteAmbiente"] for _ in range(3)]
        self.assertEqual(vistos, [1, 2, 3])
        importlib.reload(app)   # ambiente novo (cold start): volta a 1
        novo = app.lambda_handler(evento({"requisicaoId": "R-002"}), None)
        self.assertEqual(json.loads(novo["body"])["invocacaoNesteAmbiente"], 1)

    def test_evento_gerado_pelo_sam_com_body_em_base64(self):
        """events/pedido.json foi gerado por 'sam local generate-event': body em base64 + isBase64Encoded."""
        ev = json.loads((Path(__file__).resolve().parents[2] / "events" / "pedido.json").read_text())
        self.assertTrue(ev["isBase64Encoded"])
        r = app.lambda_handler(ev, None)
        self.assertEqual(r["statusCode"], 201)
        self.assertEqual(json.loads(r["body"])["guia"], "G-R-001")

    def test_demorar_dorme_5_segundos(self):
        """Verifica o sleep sem esperar de verdade (o limite de 3 s é imposto pelo Lambda/SAM, não pelo código)."""
        with mock.patch.object(app.time, "sleep") as dorme:
            r = app.lambda_handler(evento({"requisicaoId": "R-003", "demorar": True}), None)
        dorme.assert_called_once_with(5)
        self.assertEqual(r["statusCode"], 201)


if __name__ == "__main__":
    unittest.main()
