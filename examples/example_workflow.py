import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from saturnix_harness.config import Settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.schemas import HarnessRequest


async def main() -> None:
    settings = Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_sqlite_path="./data/example.sqlite3",
    )
    orchestrator = CoreOrchestrator(settings=settings)
    result = await orchestrator.run(
        HarnessRequest(
            goal=(
                "Design a three-agent research workflow that can analyze a document, "
                "produce structured JSON, and verify the final answer."
            ),
            input="The system should prefer Claude for long context and Gemini for JSON.",
        )
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
