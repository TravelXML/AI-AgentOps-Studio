"""RAG (Phase 4): real chunking, real MockEmbedding vectors, real pgvector cosine search - no
mocking needed at the HTTP boundary since MockEmbedding is zero-network by default, the same
role MockLLM plays for chat completion. MockEmbedding has no real semantic understanding (it
hashes the literal text), so these tests prove the pipeline is wired correctly by using an exact
text match, which is guaranteed to score 1.0 and rank first - not by testing semantic relevance,
which would require a real embedding model."""

import json

from agentq_api.services.bootstrap import ensure_dev_workspace
from agentq_api.services.knowledge_service import KnowledgeService, PgVectorRetrievalService, chunk_text
from model_gateway import ModelGateway


def test_chunk_text_splits_long_text_with_overlap():
    text = "a" * 2000
    chunks = chunk_text(text, size=800, overlap=100)

    assert len(chunks) > 1
    assert all(len(c) <= 800 for c in chunks)


def test_chunk_text_empty_returns_no_chunks():
    assert chunk_text("   ") == []


async def test_create_and_list_knowledge_base_via_api(client):
    create = await client.post("/api/v1/knowledge-bases", json={"name": "Docs", "description": "test"})
    assert create.status_code == 201, create.text
    kb_id = create.json()["id"]

    listing = await client.get("/api/v1/knowledge-bases")
    assert listing.status_code == 200
    assert any(kb["id"] == kb_id for kb in listing.json())


async def test_ingest_document_via_api_becomes_ready(client):
    kb = await client.post("/api/v1/knowledge-bases", json={"name": "Docs"})
    kb_id = kb.json()["id"]

    doc = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        data={"name": "note.txt", "text": "Paris is the capital of France. It has the Eiffel Tower."},
    )
    assert doc.status_code == 201, doc.text
    body = doc.json()
    assert body["status"] == "ready"
    assert body["chunk_count"] >= 1

    docs = await client.get(f"/api/v1/knowledge-bases/{kb_id}/documents")
    assert len(docs.json()) == 1


async def test_ingest_empty_document_marks_failed(client):
    kb = await client.post("/api/v1/knowledge-bases", json={"name": "Docs"})
    kb_id = kb.json()["id"]

    doc = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents", data={"name": "empty.txt", "text": "   "}
    )
    assert doc.status_code == 201
    assert doc.json()["status"] == "failed"


async def test_retrieve_ranks_exact_match_first(db_session):
    gateway = ModelGateway()
    service = KnowledgeService(db_session, gateway)
    workspace = await ensure_dev_workspace(db_session)
    kb = await service.create_knowledge_base(workspace.id, "Docs", "")

    exact = "apple banana cherry delicious fruit salad"
    unrelated = "car truck bicycle transportation vehicle"
    await service.ingest_document(kb, "a.txt", exact, embedding_model=None)
    await service.ingest_document(kb, "b.txt", unrelated, embedding_model=None)

    retrieval = PgVectorRetrievalService(gateway)
    results = await retrieval.retrieve(str(kb.id), exact, top_k=2, min_score=0.0, embedding_model=None)

    assert results[0].content == exact
    assert results[0].score > 0.99


async def test_flow_with_rag_node_retrieves_context_end_to_end(client):
    kb = await client.post("/api/v1/knowledge-bases", json={"name": "Docs"})
    kb_id = kb.json()["id"]

    inputs = {"query": "hello rag world"}
    exact_text = json.dumps(inputs)  # matches what _as_text() will embed as the query
    await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents", data={"name": "note.txt", "text": exact_text}
    )

    spec = {
        "id": "placeholder",
        "name": "RAG Flow",
        "nodes": [
            {"id": "input-1", "type": "input", "label": "Input", "config": {}},
            {
                "id": "rag-1",
                "type": "rag",
                "label": "Retrieve",
                "config": {"knowledge_base_id": kb_id, "top_k": 1, "min_score": 0.0},
            },
            {"id": "output-1", "type": "output", "label": "Output", "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "input-1", "target": "rag-1"},
            {"id": "e2", "source": "rag-1", "target": "output-1"},
        ],
    }
    create = await client.post("/api/v1/flows", json={"name": "RAG Flow", "spec": spec})
    flow_id = create.json()["id"]

    run_response = await client.post(f"/api/v1/flows/{flow_id}/runs", json={"inputs": inputs})
    assert run_response.status_code == 200
    run_id = run_response.headers["x-run-id"]

    run = await client.get(f"/api/v1/runs/{run_id}")
    body = run.json()
    assert body["status"] == "SUCCEEDED", body
    assert "Relevant context" in body["output"]
    assert exact_text in body["output"]
