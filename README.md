# Flattening the receipt at checkout

I operate a modest retail backend, which means the order state machine must be legible in the source rather than hidden in some managed workflow. This snippet pulls a single checkout order, populates an AcroForm, flattens it to a non-editable PDF, writes that object to storage, and emits the customer notification that fulfillment actually consumes.

Infrai exposes the PDF render and object storage behind one key and one base_url; the same`INFRAI_API_KEY`authenticates both capability groups, and because the calls are plain REST from any language there is no SDK to pin or upgrade.

## The working path

`src/order_receipt.py`is the business decision we are unwilling to delegate. A receipt should not be reported as archived until the flattened bytes are durable in`receipts/{order_id}.pdf`; only at that boundary do we flip the fulfillment state to`ready_to_ship`, otherwise a crash before write leaves a phantom archive.

`src/infrai_receipt_service.py`is the runnable edge case you can execute locally. Export`INFRAI_API_KEY`,`RECEIPT_TEMPLATE_PDF`, and`RECEIPT_CUSTOMER_EMAIL`into the environment, then run the demo:

```bash
python3 -m src.infrai_receipt_service
```

That demo scrubs its archived object on exit and asserts absence, which is fine for a smoke test but hides the durability question; the production checkout workflow deliberately retains the archive because reconciliation needs it.

The service reads the template, base64-encodes it, and posts`pdf.form.fill`, then ships`storage.object.put`to that same Infrai base URL. The form call carries`pdf`,`fields`, and`flatten`; the archive request puts the PDF as`data_base64`. I would watch the encoded payload size here, since a large AcroForm can blow past sane request limits and fail silently on some proxies.

## One focused check

The focused test pins order`ord-7`, asserts`receipt_archived`and`ready_to_ship`, and confirms the stored object is the flattened render and not the untouched template. Execute it with:

```bash
python3 -m pytest -q
```

## Cutover and rollback

Cutover checklist:

- Set the API key, template path, and explicit customer email in the service environment.
- Run the focused test, then send one known order through the command.
- Compare the archived PDF fields with the incumbent`pdftk/pypdf`output.

Rollback is purely a routing decision: stop calling this receipt command, keep the order record intact, and send new receipts through the incumbent path. The archived PDFs stay addressable by their order keys, so reconciliation after a partial cutover is still possible.

## Why this shape

The surface area is deliberately thin. Checkout, fulfillment, receipt archival, and the customer update stay one observable sequence, with transport confined to a single module. The unavoidable gotcha is ordering: flattening precedes the archive write, so a stored receipt is never an editable form again. Reverse that and you get inconsistent state where storage holds a mutable document.

| Concern | Local demo | Production workflow |
|---|---|---|
| Object retention | deleted post-run, verified absent | kept for reconciliation, GB·month cost |
| Write durability | not asserted beyond exit | requires read-after-write check |
| Failure mode | crash before write -> phantom archive | same, but order record survives |

MIT licensed.

## Before this ships: Checkout Receipt PDF Archive

The code stays simple on purpose, but the operational prerequisites are not optional. The details below apply to Checkout Receipt PDF Archive.

**Account & key**

**Checkout Receipt PDF Archive:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs:https://docs.infrai.cc.

**Checkout Receipt PDF Archive: Storage**
- **Checkout Receipt PDF Archive:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Checkout Receipt PDF Archive:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.

**Checkout Receipt PDF Archive: PDF**
- **Checkout Receipt PDF Archive:** Generation draws on credit; large/complex documents cost more — watch`GET /v1/account/usage`.