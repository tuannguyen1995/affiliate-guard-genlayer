"""
Unit Test Suite for Soulbound Badges & Protocol Analytics in AffiliateGuard.
Validates:
1. First Blood badge awarded upon first completed campaign payout.
2. Gold Tier badge awarded upon reaching >= 150 reputation score.
3. High Roller badge awarded on high-value escrow payouts.
4. get_creator_badges view returns on-chain unlocked badges.
5. get_protocol_analytics view aggregates volume, counts, and security metrics.
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
            self.creator_badges = {}
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
        self.message_raw = {"datetime": "2026-10-14T00:00:00+00:00"}

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

class TestBadgesAndAnalyticsSuite(unittest.TestCase):
    def setUp(self):
        self.gl = contract_module.gl
        self.contract = contract_module.Contract()
        self.contract.campaigns = {}
        self.contract.campaign_ids = []
        self.contract.creator_profiles = {}
        self.contract.creator_handles = {}
        self.contract.creator_badges = {}
        self.contract._safe_transfer = MagicMock()

    def test_01_first_blood_badge_unlocked_on_completion(self):
        creator = "0xcreator_first"
        self.contract._update_reputation(creator, MockBigInt(15), is_completed=True)
        self.contract._check_and_award_badges(creator, MockBigInt(100))

        badges_json = self.contract.get_creator_badges(creator)
        badges = json.loads(badges_json)
        self.assertIn("FIRST_BLOOD", badges)

    def test_02_gold_tier_badge_unlocked_at_150_reputation(self):
        creator = "0xcreator_gold"
        # 100 default + 4 * 15 = 160 (GOLD tier)
        for _ in range(4):
            self.contract._update_reputation(creator, MockBigInt(15), is_completed=True)
        self.contract._check_and_award_badges(creator, MockBigInt(200))

        badges_json = self.contract.get_creator_badges(creator)
        badges = json.loads(badges_json)
        self.assertIn("GOLD_TIER", badges)
        self.assertIn("FIRST_BLOOD", badges)

    def test_03_high_roller_badge_awarded_on_large_escrow(self):
        creator = "0xcreator_whale"
        self.contract._update_reputation(creator, MockBigInt(15), is_completed=True)
        self.contract._check_and_award_badges(creator, MockBigInt(1000))

        badges_json = self.contract.get_creator_badges(creator)
        badges = json.loads(badges_json)
        self.assertIn("HIGH_ROLLER", badges)

    def test_04_protocol_analytics_aggregation(self):
        # Create campaign 1
        self.gl.message.sender_address = MockAddress("0xbrand1")
        self.gl.message.value = MockBigInt(1000)
        self.contract.create_campaign(
            "camp_analytics_01",
            "0xcreator1",
            "@creator1",
            "scam",
            "Shoes",
            "buy",
            "en",
            "desc",
            "",
            ""
        )
        # Create open bounty
        self.gl.message.value = MockBigInt(500)
        self.contract.create_open_bounty(
            "bounty_analytics_01",
            "",
            "Shirt",
            "order",
            "en",
            "desc",
            "",
            ""
        )

        analytics_json = self.contract.get_protocol_analytics()
        data = json.loads(analytics_json)

        self.assertEqual(data["total_campaigns"], 2)
        self.assertEqual(data["total_escrow_volume"], "1500")
        self.assertEqual(data["active_bounties"], 1)
        self.assertTrue(data["canary_defense_active"])
