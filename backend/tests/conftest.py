from datetime import datetime, timezone

import pytest

from referee.adapty.client import MockAdaptyClient
from referee.adapty.normalize import build_history_input, build_test_input
from referee.catalog import Catalog
from referee.config import Settings
from referee.dossier import build_dossier

APP_ID = "9c35cea9-1655-4af3-9f05-ac16f383e91d"
NOW = datetime(2026, 11, 7, 17, 0, tzinfo=timezone.utc)
ONBOARDING = "b2c90b2b-59b0-48fc-b821-b90061d1ae1e"
MAIN_NA = "fa529c42-4d24-4dde-b63a-e15fda1aa93d"
SETTINGS = "35299a82-0d41-4b50-a874-bf86e11c33d0"
DRAFT = "7c4c06ef-f5da-45a3-9ec1-05d644e78f03"


@pytest.fixture
def client() -> MockAdaptyClient:
    return MockAdaptyClient(APP_ID)


@pytest.fixture
def catalog() -> Catalog:
    return Catalog.load()


@pytest.fixture
def settings(tmp_path) -> Settings:
    # The API tests pin the captured set: its numbers are the ones the assertions quote.
    return Settings(llm_provider="template", fixed_now=NOW, data_dir=tmp_path / "data", adapty_fixtures="captured")


@pytest.fixture
def make_dossier(client, catalog):
    history = build_history_input(client.analytics_conversion("trial-paid", "2026-07-01", "2026-11-07"))

    def _make(test_id: str, now: datetime = NOW, assumptions=None):
        detail = client.get_test(test_id)
        total = client.metrics_total(test_id)
        tree = client.metrics_tree(test_id)
        test_input = build_test_input(detail, total, tree, catalog, client.store.winners.get(test_id))
        return build_dossier(test_input, history, APP_ID, now, assumptions)

    return _make
