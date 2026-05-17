from saturnix_harness.config import Settings


def test_settings_accept_local_paths(tmp_path):
    settings = Settings(
        saturnix_env="test",
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
        saturnix_chroma_path=tmp_path / "chroma",
        saturnix_enable_chroma=False,
    )

    assert settings.sqlite_path.name == "memory.sqlite3"
    assert settings.chroma_path.name == "chroma"
    assert settings.saturnix_env == "test"

