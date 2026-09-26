import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models.asset import Asset
from app.repositories.asset_repository import list_assets, save_asset


class AssetRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_empty_asset_database_returns_empty_list(self):
        self.assertEqual(list_assets(self.session), [])

    def test_multiple_assets_are_returned_in_stable_order(self):
        save_asset(
            self.session,
            Asset(
                asset_id="asset-z",
                hostname="host-z",
                ip_address="192.0.2.20",
                asset_type="server",
            ),
        )
        save_asset(
            self.session,
            Asset(
                asset_id="asset-a",
                hostname="host-a",
                ip_address="192.0.2.10",
                asset_type="workstation",
                operating_system="Linux",
                criticality="high",
            ),
        )

        assets = list_assets(self.session)
        self.assertEqual([asset.asset_id for asset in assets], ["asset-a", "asset-z"])

    def test_records_contain_only_existing_asset_fields(self):
        save_asset(
            self.session,
            Asset(
                asset_id="asset-1",
                hostname="host-1",
                ip_address="192.0.2.1",
                asset_type="server",
                operating_system="Windows Server",
                criticality="critical",
            ),
        )

        asset = list_assets(self.session)[0]
        self.assertEqual(
            {
                "asset_id": asset.asset_id,
                "hostname": asset.hostname,
                "ip_address": asset.ip_address,
                "asset_type": asset.asset_type,
                "operating_system": asset.operating_system,
                "criticality": asset.criticality,
            },
            {
                "asset_id": "asset-1",
                "hostname": "host-1",
                "ip_address": "192.0.2.1",
                "asset_type": "server",
                "operating_system": "Windows Server",
                "criticality": "critical",
            },
        )


if __name__ == "__main__":
    unittest.main()
