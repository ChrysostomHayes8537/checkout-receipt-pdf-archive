import base64

from src.infrai_receipt_service import InfraiClient


def test_archive_preserves_pdf_bytes_from_data_url():
    client = InfraiClient("test")
    calls = []
    client.request = lambda *args: calls.append(args) or {}
    pdf = b"%PDF-1.4\nreceipt"
    client.put_pdf("receipts", "test.pdf", "data:application/pdf;base64," + base64.b64encode(pdf).decode())
    assert base64.b64decode(calls[0][2]["data_base64"]) == pdf


def test_delete_accepts_head_found_false():
    client = InfraiClient("test")
    calls = []

    def request(method, path, body):
        calls.append(method)
        return {"found": False} if method == "GET" else {}

    client.request = request
    client.delete_pdf("receipts", "test.pdf")
    assert calls == ["DELETE", "GET"]
