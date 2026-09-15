# AffiliateGuard

AffiliateGuard is a decentralized affiliate marketing escrow platform that uses GenLayer's Intelligent Contracts to automatically verify content requirements and process payouts via AI consensus.

## Deployed Contract
- **Contract Address:** `0x4c79bC7e88642625f677AFDc6d593048875065C5`
- **GenLayer Studio Explorer:** [https://explorer-studio.genlayer.com/address/0x4c79bC7e88642625f677AFDc6d593048875065C5](https://explorer-studio.genlayer.com/address/0x4c79bC7e88642625f677AFDc6d593048875065C5)

## Live App
- **Production URL:** [https://affiliateguard.vercel.app](https://affiliateguard.vercel.app)

## How it Works
1. **Brand Escrow:** Brands create a campaign with a designated Creator, escrow amount, product requirements, CTA, and blacklist keywords.
2. **Creator Acceptance & Staking:** The designated Creator deposits a mandatory 20% stake to accept the campaign terms (skin-in-the-game to prevent spam).
3. **Authentic Platform Evidence & Account Verification:** The Creator submits their media URL. The contract enforces:
   - **Canonical Hostname Matching:** Rejects loose URL substring matching (e.g. `attacker.com/youtube.com`). Submissions must originate from exact canonical hosts (`youtube.com`, `youtu.be`, `tiktok.com`, `instagram.com`, `x.com`, `twitter.com`) verified via `_is_authenticated_platform_host`.
   - **On-Chain Creator Account Registry:** Creators register their social handle on-chain (`register_creator_handle`). The contract verifies that platform metadata (JSON-LD author, oEmbed provider, meta author tags) matches the creator's registered handle bound to `creator_address`.
   - **Audio Transcript Provenance:** Spoken product mentions, CTA, and language subtitles are verified strictly from caption/subtitle metadata tracks.
   - **Non-Inference Visual Frame Provenance:** Plain webpage description text CANNOT certify visual frame pixels. If a Brand Logo is required, text-only evidence defaults to `PARTIAL` (forcing the mandatory 24-hour cooling-off window for Brand visual verification).
4. **Decentralized Validator Consensus Dispute Resolution (Ownerless Slashing):**
   - **RELEASE/PARTIAL:** Payout enters a mandatory 24-hour cooling-off delay (`AWAITING_PAYOUT`). If no dispute occurs within 24h, payout is finalized.
   - **Safe Stake Protection:** Automatic stake slashing is decoupled from heuristic web scrapes. On non-compliance (`REFUND`), Brand receives 100% escrow refund, and Creator stake is safely returned to prevent loss from scraper glitches.
   - **Trustless Validator Consensus Slashing:** Single-sig owner control is completely eliminated! If a dispute is raised, resolution and stake slashing (`SLASH`) are determined 100% by GenLayer Multi-Agent LLM Consensus (`gl.vm.run_nondet`) based on transcript/frame provenance and creator account authentication. Stale disputes (>30 days) can be recovered via automated 50/50 split and stake refund.

## Adversarial & Regression Test Suite

An exhaustive test suite is implemented in [`tests/test_adversarial.py`](./tests/test_adversarial.py) (13 tests), [`tests/test_affiliate_guard.py`](./tests/test_affiliate_guard.py) (3 tests), [`tests/test_evidence_binding.py`](./tests/test_evidence_binding.py) (6 tests), and [`tests/test_adversarial.js`](./tests/test_adversarial.js) (12 simulations) covering:
- **Canonical Domain & Substring Exploit Defense**: Rejects unauthenticated pastebins and substring URL tricks (e.g., `attacker.com/youtube.com`).
- **On-Chain Creator Account Registration**: Verifies handle binding via `register_creator_handle` and platform metadata author matching.
- **Transcript & Frame Provenance Verification**: Enforces non-inference rules (yielding `PARTIAL` rather than full `RELEASE` for text-only evidence when visual logo is required).
- **Safe Stake Protection**: Verifies Creator stake is never blindly slashed on heuristic scrapes.
- **Trustless Validator Consensus Slashing**: Slashing is exclusively executable via multi-agent validator consensus (`gl.vm.run_nondet`) on confirmed fraud, completely eliminating owner control.
- **Under-Staking Defense**: Rejects stake amounts < 20%.
- **Early/Unauthorized Payout Defense**: Enforces 24h cooling-off and caller authorization for all parties.
- **Anti-Timestamp-Manipulation**: Validates 7-day cancellation timeout using trusted context.
- **Validator Disagreement Handling**: Verifies consensus passes on semantic equivalence and reverts on disagreement.
- **Ownerless Dispute Resolution Defense**: Prevents malicious self-refunds and enforces consensus arbitration.
- **Terminal Fund Flows**: Release, Partial, Escrow Refund, Consensus Dispute Resolution, and Stale Recovery.
