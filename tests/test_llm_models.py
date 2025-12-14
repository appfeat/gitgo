import gup
import gup.__main__ as impl

def test_list_llm_models(monkeypatch):
    fake_output = """
Models:
openai:gpt-4.1
openai:gpt-4.1-mini
invalid model name
"""

    monkeypatch.setattr(impl, "safe", lambda _: fake_output)

    models = gup.list_llm_models()
    ids = [m["id"] for m in models]

    assert "gpt-4.1" in ids
    assert "gpt-4.1-mini" in ids
    assert all(" " not in i for i in ids)
