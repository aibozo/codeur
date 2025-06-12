from pathlib import Path

from src.rag_service import RAGService, RAGClient
from src.code_planner.rag_integration import CodePlannerRAGIntegration
from src.proto_gen import messages_pb2


def _mock_embedding_service(service: RAGService):
    dim = service.embedding_service.dimension
    service.embedding_service.enabled = True
    service.embedding_service.embed_batch = lambda texts: [[0.1] * dim for _ in texts]
    service.embedding_service.embed_text = lambda text: [0.1] * dim


def test_search_with_normalized_path(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    file_path = repo / "foo.py"
    file_path.write_text("def foo():\n" + "pass\n" * 60)

    rag_dir = repo / ".rag"
    service = RAGService(persist_directory=str(rag_dir), repo_path=str(repo))
    _mock_embedding_service(service)
    client = RAGClient(service=service)

    service.index_directory(str(repo), extensions=[".py"])

    results = client.search("foo", filters={"file_path": "foo.py"})
    assert results, "relative path filter should return results"

    abs_path = str(file_path.resolve())
    integration = CodePlannerRAGIntegration(str(repo), rag_client=client)
    step = messages_pb2.Step(goal="edit", kind=messages_pb2.STEP_KIND_EDIT)
    blobs = integration.prefetch_blobs_for_step(step, [abs_path], k=1)
    assert blobs, "prefetch should normalize absolute paths"


