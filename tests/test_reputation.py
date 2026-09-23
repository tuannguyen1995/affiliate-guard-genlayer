"""
Unit Test Suite for Creator Reputation and Dynamic Tiered Staking in AffiliateGuard.
Validates:
1. Default Creator Profile (Silver Tier, 100 points, 20% stake).
2. Gold Tier Qualification (>= 150 points, 10% stake discount).
3. Bronze Tier Demotion (< 100 points, 30% stake penalty).
4. Reputation updates upon successful payout release (+15 pts).
5. Stake slashing penalty upon confirmed dispute fraud (-50 pts).
6. get_creator_profile and get_required_stake views.
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
        sender_address = MockAddress("0xBrand")

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

class TestCreatorReputationSuite(unittest.TestCase):
    def setUp(self):
        self.contract = contract_module.Contract()
        self.contract._safe_transfer = MagicMock()

    def test_01_default_profile_is_silver_tier(self):
        creator = "0xCreatorWallet1"
        profile_json = self.contract.get_creator_profile(creator)
        profile = json.loads(profile_json)
        self.assertEqual(profile["tier"], "SILVER")
        self.assertEqual(int(profile["reputation_score"]), 100)
        self.assertEqual(profile["stake_percentage"], 20)

    def test_02_gold_tier_stake_calculation(self):
        creator = "0xGoldCreator"
        # Promote to Gold: 100 + 60 = 160
        self.contract._update_reputation(creator, MockBigInt(60))
        profile = json.loads(self.contract.get_creator_profile(creator))
        self.assertEqual(profile["tier"], "GOLD")
        self.assertEqual(int(profile["reputation_score"]), 160)
        self.assertEqual(profile["stake_percentage"], 10)

        # 1000 wei escrow should require 100 wei stake (10%)
        stake = self.contract._calculate_required_stake(MockBigInt(1000), creator)
        self.assertEqual(stake, 100)

    def test_03_bronze_tier_penalty_calculation(self):
        creator = "0xBronzeCreator"
        # Demote to Bronze: 100 - 25 = 75
        self.contract._update_reputation(creator, MockBigInt(-25))
        profile = json.loads(self.contract.get_creator_profile(creator))
        self.assertEqual(profile["tier"], "BRONZE")
        self.assertEqual(int(profile["reputation_score"]), 75)
        self.assertEqual(profile["stake_percentage"], 30)

        # 1000 wei escrow should require 300 wei stake (30%)
        stake = self.contract._calculate_required_stake(MockBigInt(1000), creator)
        self.assertEqual(stake, 300)

    def test_04_successful_release_promotes_reputation(self):
        creator = "0xProductiveCreator"
        self.contract._update_reputation(creator, MockBigInt(40)) # 140 (SILVER)
        
        # Reward +15 on RELEASE
        self.contract._update_reputation(creator, MockBigInt(15), is_completed=True)
        profile = json.loads(self.contract.get_creator_profile(creator))
        self.assertEqual(int(profile["reputation_score"]), 155)
        self.assertEqual(profile["tier"], "GOLD")
        self.assertEqual(int(profile["completed_campaigns"]), 1)

    def test_05_dispute_slashing_penalizes_reputation(self):
        creator = "0xBadActorCreator"
        # Slashed -50 pts
        self.contract._update_reputation(creator, MockBigInt(-50), is_slashed=True)
        profile = json.loads(self.contract.get_creator_profile(creator))
        self.assertEqual(int(profile["reputation_score"]), 50)
        self.assertEqual(profile["tier"], "BRONZE")
        self.assertEqual(int(profile["slashed_campaigns"]), 1)
        self.assertEqual(profile["stake_percentage"], 30)

if __name__ == '__main__':
    unittest.main()
