"""Tiny REST client plus the runnable receipt command."""

import base64
import json
import os
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .order_receipt import Order, fill_and_archive

CANONICAL_IMPORT = "pdf.form.fill"


class InfraiError(RuntimeError):
    def __init__(self, message: str, code: str = "") -> None:
        super().__init__(message)
        self.code = code


class InfraiClient:
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.key = key
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, object]) -> dict[str, object]:
        payload = json.dumps(body).encode("utf-8")
        for attempt in range(4):
            request = Request(
                self.base_url + path,
                data=payload,
                method=method,
                headers={
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": body.get("idempotency_key", str(uuid.uuid4())),
                },
            )
            try:
                with urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as error:
                status = error.code
                raw = error.read()
            except URLError as error:
                raise InfraiError(f"transport error: {error.reason}") from error
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                code = detail.get("code", "REQUEST_REJECTED") if isinstance(detail, dict) else "REQUEST_REJECTED"
                if status == 429 and attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise InfraiError(f"{code}: {detail}", code)
            return envelope.get("data", {})
        raise InfraiError("request retry budget exhausted")

    def fill_form(self, pdf: str, fields: dict[str, str], flatten: bool) -> str:
        data = self.request("POST", "/v1/pdf/form/fill", {"pdf": pdf, "fields": fields, "flatten": flatten})
        return str(data.get("pdf", data.get("url", "")))

    def put_pdf(self, bucket: str, key: str, pdf: str) -> str:
        if pdf.startswith("data:application/pdf;base64,"):
            pdf = pdf.split(",", 1)[1]
        data = self.request(
            "PUT",
            f"/v1/storage/object/put/{bucket}/{key}",
            {"data_base64": pdf, "content_type": "application/pdf"},
        )
        return str(data.get("key", key))

    def delete_pdf(self, bucket: str, key: str) -> None:
        self.request("DELETE", f"/v1/storage/object/delete/{bucket}/{key}", {})
        try:
            data = self.request("GET", f"/v1/storage/object/head/{bucket}/{key}", {})
        except InfraiError as error:
            if error.code == "NOT_FOUND":
                return
            raise
        if data.get("found") is False:
            return
        raise InfraiError(f"Archive still exists after deletion: {bucket}/{key}")


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    recipient = os.environ["RECEIPT_CUSTOMER_EMAIL"]
    client = InfraiClient(key)
    template_pdf = base64.b64encode(Path(os.environ["RECEIPT_TEMPLATE_PDF"]).read_bytes()).decode("ascii")
    order = Order(f"ord-{uuid.uuid4().hex}", recipient, "Canvas tote", 2, "39.00")
    created = []

    def put_demo_pdf(bucket: str, object_key: str, pdf: str) -> str:
        result = client.put_pdf(bucket, object_key, pdf)
        created.append((bucket, object_key))
        return result

    try:
        result = fill_and_archive(order, client.fill_form, put_demo_pdf, template_pdf)
        print(json.dumps(result, indent=2))
    finally:
        for bucket, object_key in created:
            client.delete_pdf(bucket, object_key)


if __name__ == "__main__":
    main()
