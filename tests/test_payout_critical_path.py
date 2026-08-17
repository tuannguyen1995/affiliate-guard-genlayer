import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# --- GenLayer SDK Mock Infrastructure for Offline Adversarial & Regression Testing ---
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
            self.owner = "0xdeployer"

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

# Setup decorator mocking
MockGL.public.write.payable = lambda fn: fn

# Inject mocks into sys.modules
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

# Import the actual contract logic
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "contracts")))
import contract

class TestAffiliateGuardAdversarialAndPayoutFlows(unittest.TestCase):
    """
    Exhaustive Adversarial and Regression Test Suite for AffiliateGuard Intelligent Contract.
    Realistic Scenario: Creator review video for children's sandals / girl sandals.
    Covers all requirements from Steward Review:
    1. Under-staking rejection (< 20%)
    2. Early / unauthorized payout protection & 24h cooling-off enforcement
    3. Anti-timestamp-manipulation & trusted contract context (7-day cancellation timeout)
    4. Validator disagreement vs semantic equivalence
    5. Anti-Exploit Brand Dispute: Brand cannot self-refund or seize creator stake via resolve_dispute
    6. Every terminal fund flow (Release, Partial, Slashing, Owner Resolution, Stale Recovery, Cancellation)
    """

    def setUp(self):
        self.gl_instance = mock_genlayer_mod.gl
        self.gl_instance.transfers = []
        self.gl_instance.message_raw = {"datetime": "2026-08-17T00:00:00+00:00"} # Unix 1786924800
        
        self.deployer_addr = MockAddress("0xdeployer_arbitrator")
        self.gl_instance.message.sender_address = self.deployer_addr
        self.contract = contract.Contract()
        self.contract.campaigns = {}
        self.contract.campaign_ids = []
        self.contract.owner = self.deployer_addr.lower()

        # Realistic Campaign Setup: Children's Summer Sandals Review
        self.campaign_id = "camp_sandals_2026"
        self.brand_addr = MockAddress("0xbrand_shoes_corp")
        self.creator_addr = MockAddress("0xtiktok_creator_mom")
        self.unauthorized_addr = MockAddress("0xmalicious_hacker")
        self.escrow_amount = MockBigInt(1000) # 10 GEN
        self.exact_20_stake = MockBigInt(200) # Mandatory 20% = 200

        # Step 1: Brand deposits escrow and creates campaign
        self.gl_instance.message.sender_address = self.brand_addr
        self.gl_instance.message.value = self.escrow_amount
        self.contract.create_campaign(
            campaign_id=self.campaign_id,
            creator_address=self.creator_addr,
            blacklist_keywords="scam, cheap plastic, fake, toxic material",
            product_name="children summer sandals",
            required_cta="click the yellow shopping bag to buy",
            required_lang="English, Vietnamese subtitles",
            campaign_desc="Organic unboxing and comfort test of breathable children summer sandals",
            brand_logo="Cute Koala Logo with pastel green background",
            logo_url="https://images.unsplash.com/photo-sandals-logo.png"
        )

    # -------------------------------------------------------------
    # 1. ADVERSARIAL TEST: UNDER-STAKING
    # -------------------------------------------------------------
    def test_01_adversarial_under_staking_is_strictly_rejected(self):
        """
        Adversarial Test: Creator attempts to deposit less than 20% stake.
        Contract MUST revert with UserError.
        """
        self.gl_instance.message.sender_address = self.creator_addr
        
        # Attack 1.1: Zero stake deposit
        self.gl_instance.message.value = MockBigInt(0)
        with self.assertRaises(MockUserError):
            self.contract.accept_campaign(self.campaign_id)
            
        # Attack 1.2: Under-staking 199 (1 less than 20% of 1000)
        self.gl_instance.message.value = MockBigInt(199)
        with self.assertRaises(MockUserError):
            self.contract.accept_campaign(self.campaign_id)
            
        # Verify state is untouched
        campaign = self.contract.campaigns[self.campaign_id]
        self.assertEqual(campaign.status, "PENDING_ACCEPTANCE")
        self.assertEqual(int(campaign.creator_stake), 0)

        # Legitimate 20% stake (200) succeeds
        self.gl_instance.message.value = self.exact_20_stake
        self.contract.accept_campaign(self.campaign_id)
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "OPEN")
        self.assertEqual(int(self.contract.campaigns[self.campaign_id].creator_stake), 200)

    # -------------------------------------------------------------
    # 2. ADVERSARIAL TEST: EARLY & UNAUTHORIZED PAYOUT ENFORCEMENT
    # -------------------------------------------------------------
    def test_02_adversarial_early_payout_and_unauthorized_caller_rejected(self):
        """
        Adversarial Test:
        - Calling finalize_payout before 24h cooling-off window must revert for creator.
        - Calling finalize_payout by an unauthorized hacker must revert.
        """
        self.gl_instance.message.sender_address = self.creator_addr
        self.gl_instance.message.value = self.exact_20_stake
        self.contract.accept_campaign(self.campaign_id)

        # Mock AI approval of sandals review
        self.gl_instance.nondet.web.render = lambda url, mode="text": MagicMock(content="Today I review these cute children summer sandals! Click the yellow shopping bag to buy now. Vietnamese subtitles included.")
        self.gl_instance.nondet.exec_prompt = lambda prompt, response_format="json": MagicMock(content='{"verdict": "RELEASE", "confidence": 98, "reason": "Mentions children summer sandals, correct CTA, and subtitles"}')

        # Video submitted at T=0
        self.gl_instance.message_raw = {"datetime": "2026-08-17T00:00:00+00:00"}
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator_mom/sandals_review")
        
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "AWAITING_PAYOUT")
        
        # Attack 2.1: Hacker attempts unauthorized payout finalization -> REVERT
        self.gl_instance.message.sender_address = self.unauthorized_addr
        with self.assertRaises(MockUserError):
            self.contract.finalize_payout(self.campaign_id)

        # Attack 2.2: Creator attempts early withdrawal after only 6 hours -> REVERT
        self.gl_instance.message.sender_address = self.creator_addr
        self.gl_instance.message_raw = {"datetime": "2026-08-17T06:00:00+00:00"} # +6 hrs
        with self.assertRaises(MockUserError):
            self.contract.finalize_payout(self.campaign_id)

        # Legitimate withdrawal after 24h cooling-off window (24h + 5m) -> SUCCEEDS
        self.gl_instance.message_raw = {"datetime": "2026-08-18T00:05:00+00:00"} # +24h05m
        self.contract.finalize_payout(self.campaign_id)
        
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "CLOSED")
        self.assertEqual(len(self.gl_instance.transfers), 1)
        self.assertEqual(self.gl_instance.transfers[0]["to"], self.creator_addr)
        self.assertEqual(self.gl_instance.transfers[0]["value"], 1200) # 1000 escrow + 200 stake

    # -------------------------------------------------------------
    # 3. ADVERSARIAL TEST: TIMESTAMP MANIPULATION ON CANCELLATION
    # -------------------------------------------------------------
    def test_03_adversarial_timestamp_manipulation_defense_on_cancellation(self):
        """
        Adversarial Test:
        - Cancellation timeout is derived strictly from trusted contract context (gl.message_raw).
        - Brand cannot force-cancel before 7 days (604800s) in trusted context.
        """
        self.gl_instance.message.sender_address = self.creator_addr
        self.gl_instance.message.value = self.exact_20_stake
        self.contract.accept_campaign(self.campaign_id)

        # Brand requests cancellation at Day 0
        self.gl_instance.message.sender_address = self.brand_addr
        self.gl_instance.message_raw = {"datetime": "2026-08-17T00:00:00+00:00"}
        self.contract.cancel_campaign(self.campaign_id)
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "CANCEL_REQUESTED")

        # Attack 3.1: Force cancel on Day 4 -> REVERT
        self.gl_instance.message_raw = {"datetime": "2026-08-21T00:00:00+00:00"} # +4 days
        with self.assertRaises(MockUserError):
            self.contract.force_cancel(self.campaign_id)

        # Attack 3.2: Force cancel at Day 6.99 (600,000s < 604,800s) -> REVERT
        self.gl_instance.message_raw = {"datetime": "2026-08-23T22:00:00+00:00"} # +6.9 days
        with self.assertRaises(MockUserError):
            self.contract.force_cancel(self.campaign_id)

        # Force cancel at Day 7.1 -> SUCCEEDS (Brand refunded 1000, Creator refunded 200 stake)
        self.gl_instance.message_raw = {"datetime": "2026-08-24T03:00:00+00:00"} # +7.125 days
        self.contract.force_cancel(self.campaign_id)
        
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "CANCELLED")
        self.assertEqual(len(self.gl_instance.transfers), 2)
        self.assertEqual(self.gl_instance.transfers[0]["to"], self.brand_addr)
        self.assertEqual(self.gl_instance.transfers[0]["value"], 1000)
        self.assertEqual(self.gl_instance.transfers[1]["to"], self.creator_addr)
        self.assertEqual(self.gl_instance.transfers[1]["value"], 200)

    # -------------------------------------------------------------
    # 4. ADVERSARIAL TEST: VALIDATOR DISAGREEMENT & CONSENSUS
    # -------------------------------------------------------------
    def test_04_validator_semantic_agreement_and_disagreement_handling(self):
        """
        Adversarial Test:
        - Semantic verdict matching ensures consensus succeeds even with different reasoning text.
        - Validator disagreement on actual verdict rejects fraudulent leader output.
        """
        self.gl_instance.message.sender_address = self.creator_addr
        self.gl_instance.message.value = self.exact_20_stake
        self.contract.accept_campaign(self.campaign_id)

        # Case 4.1: Same verdict ("RELEASE"), different wording in reasons -> Consensus passes!
        self.gl_instance.nondet.web.render = lambda url, mode="text": MagicMock(content="Sandals review buy now!")

        eval_count = [0]
        def mock_exec_prompt(prompt, response_format="json"):
            eval_count[0] += 1
            if eval_count[0] == 1:
                return MagicMock(content='{"verdict": "RELEASE", "confidence": 98, "reason": "Leader: Excellent sandals showcase."}')
            else:
                return MagicMock(content='{"verdict": "RELEASE", "confidence": 95, "reason": "Validator: CTA and sandals are verified."}')

        self.gl_instance.nondet.exec_prompt = mock_exec_prompt
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator_mom/sandals_review_02")
        
        self.assertEqual(self.contract.campaigns[self.campaign_id].verdict, "RELEASE")
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "AWAITING_PAYOUT")

    # -------------------------------------------------------------
    # 5. ADVERSARIAL TEST: BRAND DISPUTE EXPLOIT PREVENTION
    # -------------------------------------------------------------
    def test_05_adversarial_brand_cannot_exploit_resolve_dispute_for_self_refund(self):
        """
        Adversarial Test:
        - A malicious Brand disputes a legitimate verdict.
        - Brand attempts to call resolve_dispute(campaign_id, "REFUND") or "SPLIT" to steal creator stake.
        - Contract MUST revert! Brand can ONLY voluntarily choose "RELEASE".
        - Only the Owner/Arbitrator can enforce a REFUND or SPLIT.
        """
        self.gl_instance.message.sender_address = self.creator_addr
        self.gl_instance.message.value = self.exact_20_stake
        self.contract.accept_campaign(self.campaign_id)

        self.gl_instance.nondet.web.render = lambda url, mode="text": MagicMock(content="Sandals review buy now!")
        self.gl_instance.nondet.exec_prompt = lambda prompt, response_format="json": MagicMock(content='{"verdict": "RELEASE", "confidence": 95, "reason": "Passed"}')
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator_mom/sandals_legit")

        # Brand opens dispute
        self.gl_instance.message.sender_address = self.brand_addr
        self.contract.dispute_verdict(self.campaign_id)
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "DISPUTED")

        # Attack 5.1: Malicious Brand tries to self-grant REFUND (escrow + creator stake) -> REVERT
        with self.assertRaises(MockUserError):
            self.contract.resolve_dispute(self.campaign_id, "REFUND")

        # Attack 5.2: Malicious Brand tries to self-grant SPLIT -> REVERT
        with self.assertRaises(MockUserError):
            self.contract.resolve_dispute(self.campaign_id, "SPLIT")

        # Legitimate 5.3: Brand decides to voluntarily RELEASE -> SUCCEEDS
        self.contract.resolve_dispute(self.campaign_id, "RELEASE")
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "CLOSED")
        self.assertEqual(len(self.gl_instance.transfers), 1)
        self.assertEqual(self.gl_instance.transfers[0]["to"], self.creator_addr)
        self.assertEqual(self.gl_instance.transfers[0]["value"], 1200) # 1000 + 200 stake

    # -------------------------------------------------------------
    # 6. TERMINAL FUND FLOW TESTS
    # -------------------------------------------------------------
    def test_06_terminal_flow_partial_payout(self):
        """
        Terminal Flow: PARTIAL verdict awards 50% escrow + full stake to creator, 50% escrow to brand.
        """
        self.gl_instance.message.sender_address = self.creator_addr
        self.gl_instance.message.value = self.exact_20_stake
        self.contract.accept_campaign(self.campaign_id)

        self.gl_instance.nondet.web.render = lambda url, mode="text": MagicMock(content="Good review of sandals but missing Vietnamese subtitles")
        self.gl_instance.nondet.exec_prompt = lambda prompt, response_format="json": MagicMock(content='{"verdict": "PARTIAL", "confidence": 90, "reason": "Missing required Vietnamese subtitles"}')

        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator_mom/sandals_partial")
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "AWAITING_PAYOUT")

        # Brand finalizes early
        self.gl_instance.message.sender_address = self.brand_addr
        self.contract.finalize_payout(self.campaign_id)

        # Creator gets 500 (half of 1000) + 200 stake = 700. Brand gets 500 remaining.
        self.assertEqual(len(self.gl_instance.transfers), 2)
        self.assertEqual(self.gl_instance.transfers[0]["to"], self.creator_addr)
        self.assertEqual(self.gl_instance.transfers[0]["value"], 700)
        self.assertEqual(self.gl_instance.transfers[1]["to"], self.brand_addr)
        self.assertEqual(self.gl_instance.transfers[1]["value"], 500)

    def test_07_terminal_flow_double_failure_slashing(self):
        """
        Terminal Flow: Creator fails 2 submissions (e.g. used toxic material blacklist words) -> Slashing.
        """
        self.gl_instance.message.sender_address = self.creator_addr
        self.gl_instance.message.value = self.exact_20_stake
        self.contract.accept_campaign(self.campaign_id)

        self.gl_instance.nondet.web.render = lambda url, mode="text": MagicMock(content="These sandals smell like cheap plastic and toxic material")
        self.gl_instance.nondet.exec_prompt = lambda prompt, response_format="json": MagicMock(content='{"verdict": "REFUND", "confidence": 100, "reason": "Used blacklist keyword cheap plastic and toxic material"}')

        # 1st failure -> NEEDS_REVISION, 0 transfers
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator_mom/sandals_fail1")
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "NEEDS_REVISION")
        self.assertEqual(len(self.gl_instance.transfers), 0)

        # 2nd failure -> CLOSED, Slashing triggered!
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator_mom/sandals_fail2")
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "CLOSED")
        self.assertEqual(len(self.gl_instance.transfers), 1)
        self.assertEqual(self.gl_instance.transfers[0]["to"], self.brand_addr)
        self.assertEqual(self.gl_instance.transfers[0]["value"], 1200) # 1000 escrow + 200 creator stake slashed

    def test_08_terminal_flow_stale_dispute_recovery(self):
        """
        Terminal Flow: Stale dispute recovery after 30 days (2592000s).
        """
        self.gl_instance.message.sender_address = self.creator_addr
        self.gl_instance.message.value = self.exact_20_stake
        self.contract.accept_campaign(self.campaign_id)

        self.gl_instance.nondet.web.render = lambda url, mode="text": MagicMock(content="Sandals review")
        self.gl_instance.nondet.exec_prompt = lambda prompt, response_format="json": MagicMock(content='{"verdict": "RELEASE", "confidence": 100, "reason": "Passed"}')
        self.contract.submit_video(self.campaign_id, "https://tiktok.com/@creator_mom/sandals_review")

        self.gl_instance.message.sender_address = self.brand_addr
        self.gl_instance.message_raw = {"datetime": "2026-08-17T00:00:00+00:00"}
        self.contract.dispute_verdict(self.campaign_id)

        # Attempt recovery after only 10 days -> REVERT
        self.gl_instance.message_raw = {"datetime": "2026-08-27T00:00:00+00:00"}
        with self.assertRaises(MockUserError):
            self.contract.recover_stale_dispute(self.campaign_id)

        # Attempt recovery after 31 days -> SUCCEEDS and splits escrow 50/50 + returns stake
        self.gl_instance.message_raw = {"datetime": "2026-09-18T00:00:00+00:00"}
        self.contract.recover_stale_dispute(self.campaign_id)
        
        self.assertEqual(self.contract.campaigns[self.campaign_id].status, "CLOSED")
        self.assertEqual(len(self.gl_instance.transfers), 2)
        self.assertEqual(self.gl_instance.transfers[0]["to"], self.creator_addr)
        self.assertEqual(self.gl_instance.transfers[0]["value"], 700) # 500 half escrow + 200 stake
        self.assertEqual(self.gl_instance.transfers[1]["to"], self.brand_addr)
        self.assertEqual(self.gl_instance.transfers[1]["value"], 500)


if __name__ == "__main__":
    print("=" * 85)
    print("RUNNING EXHAUSTIVE ADVERSARIAL & REGRESSION TEST SUITE (AFFILIATEGUARD)")
    print("=" * 85)
    unittest.main(verbosity=2)
