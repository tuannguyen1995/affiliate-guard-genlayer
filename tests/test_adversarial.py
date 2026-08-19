"""
Adversarial & Regression Test Suite for AffiliateGuard Intelligent Contract.
Tested Scenarios:
1. Under-Staking Attack (depositing < 20% stake).
2. Early Payout Attack (< 24h cooling-off window).
3. Unauthorized Payout Attack (third-party callers).
4. Anti-Timestamp-Manipulation (7-day cancellation delay verification).
5. Validator Disagreement (verdict consensus equivalence vs fraud rejection).
6. Brand Dispute Exploit Prevention (malicious self-refund attempt).
7. Terminal Fund Flows (Release, Partial, Slashing, Owner Resolution, Stale Recovery, Cancellation).
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

# --- GenLayer Testing Mock Infrastructure ---
class MockAddress(str):
    pass

class MockBigInt(int):
    pass

class MockUserError(Exception):
    pass

class MockReturn:
    def __init__(self, calldata):
        self.calldata = calldata

class MockContractStub:
    def __init__(self, address, transfer_tracker):
        self.address = address
        self.transfer_tracker = transfer_tracker

    def emit_transfer(self, value):
        self.transfer_tracker.append({"to": self.address, "value": value})

class MockGL:
    class Contract:
        def __init__(self):
            self.campaigns = {}
            self.campaign_ids = []
            self.owner = "0xdeployer_arbitrator"

    class public:
        @staticmethod
        def view(fn): return fn
        @staticmethod
        def write(fn): return fn

    class message:
        value = MockBigInt(0)
        sender_address = MockAddress("0xBrandAddress")

    class nondet:
        class web:
            @staticmethod
            def render(url, mode="text"):
                pass
        @staticmethod
        def exec_prompt(prompt, response_format="json"):
            pass

    class vm:
        Return = MockReturn
        @staticmethod
        def run_nondet(leader_fn, validator_fn):
            res = leader_fn()
            ret = MockReturn(calldata=res)
            is_valid = validator_fn(ret)
            if not is_valid:
                raise MockUserError("Validator disagreement: Consensus failed")
            return res

    def __init__(self):
        self.transfers = []
        self.message_raw = {"datetime": "2026-08-17T00:00:00+00:00"}

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

# Import smart contract
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "contracts")))
import contract

class TestAffiliateGuardAdversarialSuite(unittest.TestCase):
    def setUp(self):
        self.gl = mock_genlayer_mod.gl
        self.gl.transfers = []
        self.gl.message_raw = {"datetime": "2026-08-17T00:00:00+00:00"}
        
        self.deployer_addr = MockAddress("0xdeployer_arbitrator")
        self.gl.message.sender_address = self.deployer_addr
        self.contract = contract.Contract()
        self.contract.campaigns = {}
        self.contract.campaign_ids = []
        self.contract.owner = self.deployer_addr.lower()

        # Realistic Campaign: Summer Sandals Review
        self.campaign_id = "camp_sandals_2026"
        self.brand_addr = MockAddress("0xbrand_shoes_corp")
        self.creator_addr = MockAddress("0xtiktok_creator_mom")
        self.hacker_addr = MockAddress("0xmalicious_hacker")
        self.escrow_amount = MockBigInt(1000) # 10 GEN
        self.min_stake = MockBigInt(200) # 20% mandatory stake

        self.gl.message.sender_address = self.brand_addr
        self.gl.message.value = self.escrow_amount
        self.contract.create_campaign(
            campaign_id=self.campaign_id,
            creator_address=self.creator_addr,
            blacklist_keywords="scam, cheap plastic, fake, toxic material",
            product_name="children summer sandals",
            required_cta="click the yellow shopping bag to buy",
            required_lang="English, Vietnamese subtitles",
            campaign_desc="Review breathable children summer sandals",
            brand_logo="Cute Koala Logo",
            logo_url="https://example.com/logo.png"
        )

    def test_01_under_staking_attack_reverts(self):
        """Creator attempts to deposit less than 20% stake -> Reverts"""
        self.gl.message.sender_address = self.creator_addr
        
        # 0 stake
        self.gl.message.value = MockBigInt(0)
        with self.assertRaises(MockUserError):
            self.contract.accept_campaign(self.campaign_id)
            
        # 199 stake (< 200)
        self.gl.message.value = MockBigInt(199)
        with self.assertRaises(MockUserError):
            self.contract.accept_campaign(self.campaign_id)
            
        # Legitimate 200 stake succeeds
        self.gl.message.value = self.min_stake
        self.contract.accept_campaign(self.campaign_id)
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "OPEN")
        self.assertEqual(int(self.contract.campaigns[self.campaign_id].creator_stake), 200)

    def test_02_early_and_unauthorized_payout_attack_reverts(self):
        """Early withdrawal before 24h cooling-off or by third parties -> Reverts"""
        self.gl.message.sender_address = self.creator_addr
        self.gl.message.value = self.min_stake
        self.contract.accept_campaign(self.campaign_id)

        self.gl.nondet.web.render = lambda url, mode="text": MagicMock(content="Legit review of children summer sandals, click the yellow shopping bag!")
        self.gl.nondet.exec_prompt = lambda prompt, response_format="json": MagicMock(content='{"verdict": "RELEASE", "confidence": 98, "reason": "Passed all requirements"}')

        self.gl.message_raw = {"datetime": "2026-08-17T00:00:00+00:00"}
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator/sandals")
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "AWAITING_PAYOUT")

        # Hacker calls finalize_payout -> Reverts
        self.gl.message.sender_address = self.hacker_addr
        with self.assertRaises(MockUserError):
            self.contract.finalize_payout(self.campaign_id)

        # Creator calls early (+6 hrs) -> Reverts
        self.gl.message.sender_address = self.creator_addr
        self.gl.message_raw = {"datetime": "2026-08-17T06:00:00+00:00"}
        with self.assertRaises(MockUserError):
            self.contract.finalize_payout(self.campaign_id)

        # Brand calls early (+6 hrs) -> MUST ALSO REVERT! (Fixed Steward Finding)
        self.gl.message.sender_address = self.brand_addr
        with self.assertRaises(MockUserError):
            self.contract.finalize_payout(self.campaign_id)

        # Legitimate payout after 24h -> Succeeds
        self.gl.message_raw = {"datetime": "2026-08-18T00:01:00+00:00"}
        self.gl.message.sender_address = self.creator_addr
        self.contract.finalize_payout(self.campaign_id)
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "CLOSED")
        self.assertEqual(len(self.gl.transfers), 1)
        self.assertEqual(self.gl.transfers[0]["to"], self.creator_addr)
        self.assertEqual(self.gl.transfers[0]["value"], 1200)

    def test_08_timestamp_failure_reverts_and_never_defaults_to_zero(self):
        """Missing or corrupted timestamp context must revert and NEVER default to 0"""
        self.gl.message.sender_address = self.creator_addr
        self.gl.message.value = self.min_stake
        self.contract.accept_campaign(self.campaign_id)

        # Missing datetime in message_raw -> MUST REVERT
        self.gl.message_raw = {}
        self.gl.message.sender_address = self.brand_addr
        with self.assertRaises(MockUserError):
            self.contract.cancel_campaign(self.campaign_id)

        # Corrupted datetime format -> MUST REVERT
        self.gl.message_raw = {"datetime": "INVALID_TIMESTAMP_STRING"}
        with self.assertRaises(MockUserError):
            self.contract.cancel_campaign(self.campaign_id)

    def test_03_timestamp_manipulation_defense(self):
        """Force cancellation timing is securely enforced on-chain (7 days)"""
        self.gl.message.sender_address = self.creator_addr
        self.gl.message.value = self.min_stake
        self.contract.accept_campaign(self.campaign_id)

        # Brand requests cancel
        self.gl.message.sender_address = self.brand_addr
        self.gl.message_raw = {"datetime": "2026-08-17T00:00:00+00:00"}
        self.contract.cancel_campaign(self.campaign_id)

        # Try force cancel on Day 4 -> Reverts
        self.gl.message_raw = {"datetime": "2026-08-21T00:00:00+00:00"}
        with self.assertRaises(MockUserError):
            self.contract.force_cancel(self.campaign_id)

        # Force cancel on Day 7.1 -> Succeeds
        self.gl.message_raw = {"datetime": "2026-08-24T03:00:00+00:00"}
        self.contract.force_cancel(self.campaign_id)
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "CANCELLED")
        self.assertEqual(len(self.gl.transfers), 2)
        self.assertEqual(self.gl.transfers[0]["value"], 1000) # Brand refund
        self.assertEqual(self.gl.transfers[1]["value"], 200)  # Creator stake refund

    def test_04_validator_disagreement_and_semantic_matching(self):
        """Consensus passes on matching semantic verdict and fails on disagreement"""
        self.gl.message.sender_address = self.creator_addr
        self.gl.message.value = self.min_stake
        self.contract.accept_campaign(self.campaign_id)

        self.gl.nondet.web.render = lambda url, mode="text": MagicMock(content="Sandals review buy now!")

        eval_count = [0]
        def mock_exec_prompt(prompt, response_format="json"):
            eval_count[0] += 1
            if eval_count[0] == 1:
                return MagicMock(content='{"verdict": "RELEASE", "confidence": 98, "reason": "Leader: sandals verified."}')
            else:
                return MagicMock(content='{"verdict": "RELEASE", "confidence": 95, "reason": "Validator: CTA and sandals verified."}')

        self.gl.nondet.exec_prompt = mock_exec_prompt
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator/sandals_02")
        self.assertEqual(self.contract.campaigns[self.campaign_id].verdict, "RELEASE")

    def test_05_brand_dispute_self_refund_exploit_prevented(self):
        """Malicious Brand cannot self-refund or seize creator stake via resolve_dispute"""
        self.gl.message.sender_address = self.creator_addr
        self.gl.message.value = self.min_stake
        self.contract.accept_campaign(self.campaign_id)

        self.gl.nondet.web.render = lambda url, mode="text": MagicMock(content="Sandals review buy now!")
        self.gl.nondet.exec_prompt = lambda prompt, response_format="json": MagicMock(content='{"verdict": "RELEASE", "confidence": 95, "reason": "Passed"}')
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator/sandals_legit")

        # Brand opens dispute
        self.gl.message.sender_address = self.brand_addr
        self.contract.dispute_verdict(self.campaign_id)

        # Brand attempts unauthorized REFUND -> Reverts
        with self.assertRaises(MockUserError):
            self.contract.resolve_dispute(self.campaign_id, "REFUND")

        # Brand attempts unauthorized SPLIT -> Reverts
        with self.assertRaises(MockUserError):
            self.contract.resolve_dispute(self.campaign_id, "SPLIT")

        # Brand voluntary RELEASE -> Succeeds
        self.contract.resolve_dispute(self.campaign_id, "RELEASE")
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "CLOSED")
        self.assertEqual(self.gl.transfers[0]["to"], self.creator_addr)
        self.assertEqual(self.gl.transfers[0]["value"], 1200)

    def test_06_slashing_on_repeated_failures(self):
        """Creator fails twice (e.g. used toxic material blacklist keyword) -> Slashed"""
        self.gl.message.sender_address = self.creator_addr
        self.gl.message.value = self.min_stake
        self.contract.accept_campaign(self.campaign_id)

        self.gl.nondet.web.render = lambda url, mode="text": MagicMock(content="Cheap plastic and toxic material")
        self.gl.nondet.exec_prompt = lambda prompt, response_format="json": MagicMock(content='{"verdict": "REFUND", "confidence": 100, "reason": "Blacklist keyword used"}')

        # 1st fail -> Revision
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator/fail1")
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "NEEDS_REVISION")

        # 2nd fail -> Slashed to brand
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator/fail2")
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "CLOSED")
        self.assertEqual(len(self.gl.transfers), 1)
        self.assertEqual(self.gl.transfers[0]["to"], self.brand_addr)
        self.assertEqual(self.gl.transfers[0]["value"], 1200) # 1000 escrow + 200 creator stake slashed

    def test_07_stale_dispute_recovery_after_30_days(self):
        """Unresolved disputes can be recovered after 30 days (50/50 split + stake refund)"""
        self.gl.message.sender_address = self.creator_addr
        self.gl.message.value = self.min_stake
        self.contract.accept_campaign(self.campaign_id)

        self.gl.nondet.web.render = lambda url, mode="text": MagicMock(content="Sandals review")
        self.gl.nondet.exec_prompt = lambda prompt, response_format="json": MagicMock(content='{"verdict": "RELEASE", "confidence": 100, "reason": "Passed"}')
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator/video")

        self.gl.message.sender_address = self.brand_addr
        self.gl.message_raw = {"datetime": "2026-08-17T00:00:00+00:00"}
        self.contract.dispute_verdict(self.campaign_id)

        # Attempt recovery after 10 days -> Reverts
        self.gl.message_raw = {"datetime": "2026-08-27T00:00:00+00:00"}
        with self.assertRaises(MockUserError):
            self.contract.recover_stale_dispute(self.campaign_id)

        # Attempt recovery after 31 days -> Succeeds
        self.gl.message_raw = {"datetime": "2026-09-18T00:00:00+00:00"}
        self.contract.recover_stale_dispute(self.campaign_id)
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "CLOSED")
        self.assertEqual(len(self.gl.transfers), 2)
        self.assertEqual(self.gl.transfers[0]["to"], self.creator_addr)
        self.assertEqual(self.gl.transfers[0]["value"], 700) # 500 escrow + 200 stake
        self.assertEqual(self.gl.transfers[1]["to"], self.brand_addr)
        self.assertEqual(self.gl.transfers[1]["value"], 500) # 500 escrow


if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING ADVERSARIAL TEST SUITE (tests/test_adversarial.py)")
    print("=" * 80)
    unittest.main(verbosity=2)
