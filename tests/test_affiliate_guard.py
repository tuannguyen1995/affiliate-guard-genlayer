import sys
import os
import unittest
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
            self.owner = "0xowner"

    class public:
        @staticmethod
        def view(fn): return fn
        @staticmethod
        def write(fn): return fn

    class message:
        value = MockBigInt(0)
        sender_address = MockAddress("0xBrand")

    class nondet:
        class web:
            @staticmethod
            def render(url, mode="text"): pass
        @staticmethod
        def exec_prompt(prompt, response_format="json"): pass

    class vm:
        Return = MockReturn
        @staticmethod
        def run_nondet(leader_fn, validator_fn):
            res = leader_fn()
            ret = MockReturn(calldata=res)
            if not validator_fn(ret):
                raise MockUserError("Consensus Disagreement")
            return res

    def __init__(self):
        self.transfers = []
        self.message_raw = {"datetime": "2026-08-16T00:00:00+00:00"}

    def get_contract_at(self, address):
        return MockContractStub(address, self.transfers)

from tests.test_adversarial import mock_genlayer_mod, MockAddress, MockBigInt, MockUserError
import contract as contract_module

class TestAffiliateGuardRegressionSuite(unittest.TestCase):
    def setUp(self):
        self.gl = mock_genlayer_mod.gl
        self.gl.transfers = []
        self.gl.message_raw = {"datetime": "2026-08-16T00:00:00+00:00"}
        self.owner = MockAddress("0xowner")
        self.brand = MockAddress("0xbrand")
        self.creator = MockAddress("0xcreator")

        self.gl.message.sender_address = self.owner
        self.contract = contract_module.Contract()
        self.contract.campaigns = {}
        self.contract.campaign_ids = []
        self.contract.owner = self.owner.lower()

        # Step 1: Brand creates campaign (1000 GEN)
        self.cid = "camp_sandals_promo_01"
        self.gl.message.sender_address = self.brand
        self.gl.message.value = MockBigInt(1000)
        self.contract.create_campaign(
            self.cid,
            self.creator,
            "@creator",
            "scam, fake, cheap",
            "girl sandals",
            "buy now",
            "English",
            "Summer Sandals Campaign",
            "PetitPas",
            "https://logo.url/img.png"
        )

        # Step 2: Creator accepts with 20% stake (200 GEN)
        self.gl.message.sender_address = self.creator
        self.gl.message.value = MockBigInt(200)
        self.contract.accept_campaign(self.cid)

    def test_01_brand_cannot_finalize_immediately_before_24h(self):
        """REGRESSION: Brand attempts early finalization during cooling-off window -> MUST REVERT"""
        # Creator submits compliant video
        self.gl.message.sender_address = self.creator
        self.gl.nondet.web.render = lambda url, mode="text": MagicMock(content="Authentic video transcript: girl sandals buy now in English")
        self.gl.nondet.exec_prompt = lambda p, response_format="json": MagicMock(content='{"verdict": "RELEASE", "confidence": 100, "reason": "All campaign criteria met"}')
        self.contract.submit_video(self.cid, "https://youtube.com/watch?v=sandals_review")
        self.assertEqual(self.contract.campaigns[self.cid].status, "AWAITING_PAYOUT")

        # Brand tries to finalize early at T+6h -> MUST REVERT
        self.gl.message_raw = {"datetime": "2026-08-16T06:00:00+00:00"}
        self.gl.message.sender_address = self.brand
        with self.assertRaises(MockUserError):
            self.contract.finalize_payout(self.cid)

        # Creator tries to finalize early at T+6h -> MUST REVERT
        self.gl.message.sender_address = self.creator
        with self.assertRaises(MockUserError):
            self.contract.finalize_payout(self.cid)

        # Finalization at T+24h01m -> SUCCEEDS (1200 payout to creator)
        self.gl.message_raw = {"datetime": "2026-08-17T00:01:00+00:00"}
        self.contract.finalize_payout(self.cid)
        self.assertEqual(self.contract.campaigns[self.cid].status, "CLOSED")
        self.assertEqual(self.gl.transfers[0]["to"], self.creator)
        self.assertEqual(self.gl.transfers[0]["value"], 1200)

    def test_02_timestamp_failure_reverts_without_defaulting_to_zero(self):
        """REGRESSION: Missing or invalid datetime header in transaction context -> MUST RAISE UserError"""
        # Case A: Missing datetime field
        self.gl.message_raw = {}
        with self.assertRaises(MockUserError):
            self.contract._get_current_timestamp()

        # Case B: Malformed datetime string
        self.gl.message_raw = {"datetime": "invalid-timestamp"}
        with self.assertRaises(MockUserError):
            self.contract._get_current_timestamp()

        # Case C: Timestamp evaluates to 0
        self.gl.message_raw = {"datetime": "1970-01-01T00:00:00Z"}
        with self.assertRaises(MockUserError):
            self.contract._get_current_timestamp()

    def test_03_dispute_blocks_finalize_and_allows_arbitration(self):
        """Dispute flow transitions to DISPUTED and prevents early payout."""
        self.gl.message.sender_address = self.creator
        self.gl.nondet.web.render = lambda url, mode="text": MagicMock(content="Transcript content")
        self.gl.nondet.exec_prompt = lambda p, response_format="json": MagicMock(content='{"verdict": "RELEASE", "confidence": 100, "reason": "Passed"}')
        self.contract.submit_video(self.cid, "https://youtube.com/watch?v=review")

        # Brand disputes at T+10h
        self.gl.message_raw = {"datetime": "2026-08-16T10:00:00+00:00"}
        self.gl.message.sender_address = self.brand
        self.gl.nondet.exec_prompt = lambda p, response_format="json": MagicMock(content='{"verdict": "REFUND", "confidence": 100, "reason": "Dispute valid"}')
        self.contract.dispute_verdict(self.cid, "Disputing content compliance")
        self.assertEqual(self.contract.campaigns[self.cid].status, "CLOSED")

if __name__ == "__main__":
    unittest.main(verbosity=2)
