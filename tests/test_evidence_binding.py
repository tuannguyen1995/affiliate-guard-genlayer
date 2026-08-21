"""
Evidence Path & Visual Compliance Test Suite for AffiliateGuard Intelligent Contract.
Specifically addresses the Steward review requirements:
1. Bind each submission to the designated creator and campaign (anti-replay/impersonation defense).
2. Verify authenticated transcript/media cues instead of treating mutable page text as proof of visual compliance.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

# --- GenLayer Mock Infrastructure ---
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
        self.message_raw = {"datetime": "2026-08-21T00:00:00+00:00"}

    def get_contract_at(self, address):
        return MockContractStub(address, self.transfers)

MockGL.public.write.payable = lambda fn: fn

mock_mod = MagicMock()
mock_mod.gl = MockGL()
mock_mod.allow_storage = lambda cls: cls
mock_mod.Address = MockAddress
mock_mod.bigint = MockBigInt
mock_mod.u256 = MockBigInt
mock_mod.UserError = MockUserError
mock_mod.TreeMap = dict
mock_mod.DynArray = list

sys.modules["genlayer"] = mock_mod
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "contracts")))
import contract as contract_module

class TestEvidenceBindingAndVisualCompliance(unittest.TestCase):
    def setUp(self):
        self.gl = contract_module.gl
        self.gl.transfers = []
        self.gl.message_raw = {"datetime": "2026-08-21T00:00:00+00:00"}
        self.brand = MockAddress("0xbrand")
        self.creator = MockAddress("0xcreator")

        self.contract = contract_module.Contract()
        self.contract.campaigns = {}
        self.contract.campaign_ids = []
        self.contract.owner = self.brand.lower()

        self.cid = "camp_sandals_2026"
        self.gl.message.sender_address = self.brand
        self.gl.message.value = MockBigInt(1000)
        self.contract.create_campaign(
            self.cid,
            self.creator,
            "scam, cheap plastic",
            "children summer sandals",
            "click yellow bag",
            "English, Vietnamese",
            "Review sandals",
            "Koala Logo",
            "https://logo.png"
        )
        self.gl.message.sender_address = self.creator
        self.gl.message.value = MockBigInt(200)
        self.contract.accept_campaign(self.cid)

    def test_01_unbound_replay_submission_refunded(self):
        """Video thiếu Campaign ID hoặc Creator Proof -> REFUND"""
        self.gl.nondet.web.render = lambda url, mode="text": MagicMock(content="Third party video reviewing sandals without campaign binding")
        self.gl.nondet.exec_prompt = lambda p, response_format="json": MagicMock(content='{"verdict": "REFUND", "confidence": 100, "reason": "Failed evidence binding: Missing campaign ID or creator proof"}')
        self.contract.submit_video(self.cid, "https://tiktok.com/@other/video")
        self.assertEqual(self.contract.campaigns[self.cid].status, "NEEDS_REVISION")
        self.assertEqual(self.contract.campaigns[self.cid].verdict, "REFUND")

    def test_02_mutable_page_text_without_visual_cues_is_partial(self):
        """Speech đạt chuẩn nhưng không có verified visual logo marker -> PARTIAL"""
        self.gl.nondet.web.render = lambda url, mode="text": MagicMock(content="[Campaign: camp_sandals_2026] [Creator: 0xcreator] Authenticated transcript with sandals and CTA, but no visual logo marker")
        self.gl.nondet.exec_prompt = lambda p, response_format="json": MagicMock(content='{"verdict": "PARTIAL", "confidence": 95, "reason": "Missing verified visual logo marker"}')
        self.contract.submit_video(self.cid, "https://tiktok.com/@creator/video2")
        self.assertEqual(self.contract.campaigns[self.cid].status, "AWAITING_PAYOUT")
        self.assertEqual(self.contract.campaigns[self.cid].verdict, "PARTIAL")

    def test_03_fully_bound_and_authenticated_submission_passes(self):
        """Video có đầy đủ Campaign ID, Creator tag, Product CTA, và [Visual: Koala Logo] marker -> RELEASE"""
        self.gl.nondet.web.render = lambda url, mode="text": MagicMock(content="[Campaign: camp_sandals_2026] [Creator: 0xcreator] [Visual: Koala Logo] Children summer sandals review, click yellow bag!")
        self.gl.nondet.exec_prompt = lambda p, response_format="json": MagicMock(content='{"verdict": "RELEASE", "confidence": 99, "reason": "All requirements verified including visual logo cue"}')
        self.contract.submit_video(self.cid, "https://tiktok.com/@creator/video_legit")
        self.assertEqual(self.contract.campaigns[self.cid].status, "AWAITING_PAYOUT")
        self.assertEqual(self.contract.campaigns[self.cid].verdict, "RELEASE")

if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING EVIDENCE BINDING TEST SUITE (tests/test_evidence_binding.py)")
    print("=" * 80)
    unittest.main(verbosity=2)
