"""
Unit Test Suite for Open Bounty Campaigns & Marketplace in AffiliateGuard.
Validates:
1. create_open_bounty creates a marketplace bounty with OPEN_BOUNTY status.
2. get_open_bounties view lists all available unallocated bounties.
3. claim_open_bounty binds claiming creator and deposits dynamic stake.
4. Brand cannot claim their own bounty.
5. Unclaimed open bounty can be cancelled immediately with full escrow refund.
"""

import sys
import os
import unittest
import json
from unittest.mock import MagicMock

class MockAddress(str): pass
class MockBigInt(int): pass
class MockUserError(Exception): pass

class MockReturn:
    def __init__(self, calldata):
        self.calldata = calldata

class MockContractStub:
    def __init__(self, address, tracker):
        self.address = address
        self.tracker = tracker

    def emit_transfer(self, value):
        self.tracker.append({"to": self.address, "value": value})

class MockGL:
    class Contract:
        def __init__(self):
            self.campaigns = {}
            self.campaign_ids = []
            self.creator_handles = {}
            self.creator_profiles = {}
            self.owner = "0xdeployer"

    class public:
        @staticmethod
        def view(fn): return fn
        @staticmethod
        def write(fn): return fn

    class message:
        value = MockBigInt(0)
        sender_address = MockAddress("0xBrandAddress")

    def __init__(self):
        self.transfers = []
        self.message_raw = {"datetime": "2026-08-16T00:00:00+00:00"}

    def get_contract_at(self, address):
        return MockContractStub(address, self.transfers)

MockGL.public.write.payable = lambda fn: fn

mock_genlayer_mod = MagicMock()
mock_genlayer_mod.gl = MockGL()
mock_genlayer_mod.allow_storage = lambda cls: cls
mock_genlayer_mod.Address = MockAddress
mock_genlayer_mod.bigint = MockBigInt
mock_genlayer_mod.u256 = MockBigInt
mock_genlayer_mod.UserError = MockUserError
mock_genlayer_mod.TreeMap = dict
mock_genlayer_mod.DynArray = list
sys.modules["genlayer"] = mock_genlayer_mod

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "contracts")))
import contract as contract_module

class TestOpenBountiesSuite(unittest.TestCase):
    def setUp(self):
        self.gl = contract_module.gl
        self.contract = contract_module.Contract()
        self.contract.campaigns = {}
        self.contract.campaign_ids = []
        self.contract.creator_profiles = {}
        self.contract.creator_handles = {}
        self.contract._safe_transfer = MagicMock()

    def test_01_create_open_bounty_and_list_marketplace(self):
        self.gl.message.sender_address = MockAddress("0xBrand123")
        self.gl.message.value = MockBigInt(1000)

        self.contract.create_open_bounty(
            bounty_id="bounty_summer_01",
            blacklist_keywords="scam, fake",
            product_name="Summer Shoes",
            required_cta="shop now",
            required_lang="English",
            campaign_desc="Summer shoes promotion open bounty",
            brand_logo="Logo Description",
            logo_url="https://example.com/logo.png"
        )

        bounties_json = self.contract.get_open_bounties()
        bounties = json.loads(bounties_json)
        self.assertEqual(len(bounties), 1)
        self.assertEqual(bounties[0]["id"], "bounty_summer_01")
        self.assertEqual(bounties[0]["product_name"], "Summer Shoes")
        self.assertEqual(bounties[0]["escrow_amount"], "1000")

    def test_02_claim_open_bounty_with_dynamic_stake(self):
        self.gl.message.sender_address = MockAddress("0xBrand123")
        self.gl.message.value = MockBigInt(1000)
        self.contract.create_open_bounty(
            bounty_id="bounty_claim_test",
            blacklist_keywords="scam",
            product_name="Product X",
            required_cta="buy now",
            required_lang="English",
            campaign_desc="Desc",
            brand_logo="Logo",
            logo_url="https://logo.png"
        )

        # Creator claims bounty (default SILVER requires 20% = 200 wei)
        self.gl.message.sender_address = MockAddress("0xCreatorWallet")
        self.gl.message.value = MockBigInt(200)
        self.contract.claim_open_bounty("bounty_claim_test")

        camp_json = self.contract.get_campaign("bounty_claim_test")
        camp = json.loads(camp_json)
        self.assertEqual(camp["status"], "OPEN")
        self.assertEqual(camp["creator"], "0xcreatorwallet")
        self.assertEqual(camp["creator_stake"], "200")

    def test_03_brand_cannot_claim_own_bounty(self):
        self.gl.message.sender_address = MockAddress("0xBrandOwner")
        self.gl.message.value = MockBigInt(1000)
        self.contract.create_open_bounty(
            bounty_id="bounty_self_claim",
            blacklist_keywords="scam",
            product_name="Product X",
            required_cta="buy now",
            required_lang="English",
            campaign_desc="Desc",
            brand_logo="Logo",
            logo_url="https://logo.png"
        )

        with self.assertRaises(Exception) as ctx:
            self.contract.claim_open_bounty("bounty_self_claim")
        self.assertIn("Brand cannot claim their own bounty", str(ctx.exception))

    def test_04_unclaimed_open_bounty_direct_cancel_refunds_brand(self):
        self.gl.message.sender_address = MockAddress("0xBrandOwner")
        self.gl.message.value = MockBigInt(500)
        self.contract.create_open_bounty(
            bounty_id="bounty_cancel_test",
            blacklist_keywords="",
            product_name="Product",
            required_cta="cta",
            required_lang="en",
            campaign_desc="desc",
            brand_logo="",
            logo_url=""
        )

        self.contract.cancel_campaign("bounty_cancel_test")
        camp = json.loads(self.contract.get_campaign("bounty_cancel_test"))
        self.assertEqual(camp["status"], "CANCELLED")
        self.contract._safe_transfer.assert_called_with("0xbrandowner", 500)

if __name__ == '__main__':
    unittest.main()
