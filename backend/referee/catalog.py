"""Product prices and trial lengths, which the Adapty developer API does not expose for store products."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .models import TrialProduct

CATALOG_PATH = Path(__file__).resolve().parent / "data" / "catalog.json"


@dataclass
class Catalog:
    products: dict[str, TrialProduct] = field(default_factory=dict)       # by Adapty product id
    by_key: dict[str, TrialProduct] = field(default_factory=dict)         # by short key (weekly, annual, ...)
    by_title: dict[str, TrialProduct] = field(default_factory=dict)
    flow_products: dict[str, list[str]] = field(default_factory=dict)     # flow name -> product keys
    placement_flows: dict[str, list[str]] = field(default_factory=dict)   # placement developer id -> flow names

    @classmethod
    def load(cls, path: Path = CATALOG_PATH) -> "Catalog":
        raw = json.loads(path.read_text(encoding="utf-8"))
        cat = cls(flow_products=raw.get("flow_products", {}), placement_flows=raw.get("placement_flows", {}))
        for product_id, item in raw.get("products", {}).items():
            product = TrialProduct(product_id=product_id, title=item["title"], price_usd=float(item["price_usd"]),
                                   trial_days=int(item.get("trial_days", 0)))
            cat.products[product_id] = product
            cat.by_key[item["key"]] = product
            cat.by_title[item["title"]] = product
        return cat

    def resolve(self, product_ids: list[str], titles: list[str] | None = None) -> list[TrialProduct]:
        """Products by id, falling back to the paywall card title when the id is unknown (live data)."""
        found: list[TrialProduct] = []
        for index, product_id in enumerate(product_ids):
            product = self.products.get(product_id)
            if product is None and titles and index < len(titles):
                product = self.by_title.get(titles[index])
            if product is not None and product not in found:
                found.append(product)
        return found

    def products_for_flow(self, flow_name: str) -> list[TrialProduct]:
        return [self.by_key[k] for k in self.flow_products.get(flow_name, []) if k in self.by_key]

    def flows_for_placement(self, developer_id: str) -> list[str]:
        return list(self.placement_flows.get(developer_id, []))
