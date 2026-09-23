import json

from dwg.runfiles import calls_path, decider_meta_path, decider_slug, load_calls, load_decider_metas


def test_slug_is_filesystem_safe():
    assert decider_slug("llm:openrouter/openai/gpt-oss-20b") == "llm_openrouter_openai_gpt-oss-20b"
    assert decider_slug("kev-4b") == "kev-4b"


def test_each_decider_gets_its_own_files_and_loading_merges_them(tmp_path):
    for decider, n in (("jev", 2), ("kev-4b", 3)):
        with calls_path(tmp_path, decider).open("w") as fh:
            for i in range(n):
                fh.write(json.dumps({"decider": decider, "i": i}) + "\n")
        decider_meta_path(tmp_path, decider).write_text(json.dumps({"decider": decider}))
    (tmp_path / "meta.json").write_text("{}")  # run-level meta is not a decider meta

    assert calls_path(tmp_path, "jev") != calls_path(tmp_path, "kev-4b")
    assert len(load_calls(tmp_path)) == 5
    assert set(load_decider_metas(tmp_path)) == {"jev", "kev-4b"}
