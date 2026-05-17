from saturnix_harness.prompts import load_prompt


def test_prompt_loader_reads_packaged_prompt():
    prompt = load_prompt("architect.md")

    assert "SATURNIX-HARNESS" in prompt
    assert "Agent Architecture Designer" in prompt

