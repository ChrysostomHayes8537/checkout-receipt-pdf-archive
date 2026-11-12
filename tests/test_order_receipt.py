from src.order_receipt import Order, fill_and_archive


def test_paid_order_is_flattened_then_archived_and_ready_to_ship():
    calls = []

    def fill(pdf, fields, flatten):
        calls.append(("fill", pdf, fields, flatten))
        return "flattened-pdf"

    def put(bucket, key, pdf):
        calls.append(("put", bucket, key, pdf))
        return "stored"

    result = fill_and_archive(Order("ord-7", "a@b.test", "Mug", 1, "12.00"), fill, put, "template.pdf")

    assert result["status"] == "receipt_archived"
    assert result["fulfillment_status"] == "ready_to_ship"
    assert calls[0][3] is True
    assert calls[1][1:] == ("receipts", "receipts/ord-7.pdf", "flattened-pdf")
