from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from threading import Event

from fastapi.testclient import TestClient
from sqlalchemy import event

from app.db import engine
from app.main import app
from tests.integration.test_governance import approve, ready

client = TestClient(app, raise_server_exceptions=False)
operation = ContextVar("publication_regression_operation", default="")


def test_publication_and_product_edit_have_consistent_lock_order():
    product, _ = ready()
    pid = product["id"]
    approve(pid)
    generation = client.get(f"/api/products/{pid}").json()["draft"]["generation"]
    publication_first, edit_first = Event(), Event()
    seen = set()

    def first_lock(conn, cursor, statement, parameters, context, executemany):
        label = operation.get()
        if not label or "FOR " not in statement or label in seen:
            return
        seen.add(label)
        if label == "publish":
            publication_first.set()
            # Old opposing locks allow the editor to acquire Product while
            # publication holds Revision. Consistent locks make it wait.
            edit_first.wait(0.5)
        else:
            edit_first.set()

    def publish():
        operation.set("publish")
        return client.post(f"/api/products/{pid}/releases").status_code

    def edit():
        operation.set("edit")
        return client.patch(f"/api/products/{pid}", json={"expected_generation": generation, "purpose": "Concurrent edit"}).status_code

    event.listen(engine, "after_cursor_execute", first_lock)
    try:
        with ThreadPoolExecutor(2) as pool:
            publication = pool.submit(publish)
            assert publication_first.wait(5)
            editing = pool.submit(edit)
            statuses = [publication.result(timeout=10), editing.result(timeout=10)]
    finally:
        event.remove(engine, "after_cursor_execute", first_lock)
    assert statuses == [201, 409], f"Concurrent requests returned {statuses}"
    assert client.get(f"/api/products/{pid}").json()["active_release_id"]
