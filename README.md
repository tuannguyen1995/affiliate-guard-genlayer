# AffiliateGuard

AffiliateGuard is a decentralized affiliate marketing escrow platform that uses GenLayer's Intelligent Contracts to automatically verify content requirements and process payouts via AI consensus.

## Deployed Contract
- **Contract Address:** `0x21f926Fe674CCC44FbD6c2b2bAB4c87ECa4520D3`
- **GenLayer Studio Explorer:** [https://explorer-studio.genlayer.com/address/0x21f926Fe674CCC44FbD6c2b2bAB4c87ECa4520D3](https://explorer-studio.genlayer.com/address/0x21f926Fe674CCC44FbD6c2b2bAB4c87ECa4520D3)

## Live App
- **Production URL:** [https://affiliateguard.vercel.app](https://affiliateguard.vercel.app)

## How it Works
1. **Brand Escrow:** Brands create a campaign with a designated Creator, escrow amount, product requirements, CTA, and blacklist keywords.
2. **Creator Acceptance & Staking:** The designated Creator deposits a mandatory 20% stake to accept the campaign terms (skin-in-the-game to prevent spam).
3. **Authentic Platform Evidence & Account Verification:** The Creator submits their media URL. The contract enforces:
   - **Platform Host & Creator Account Authenticity:** Submissions must originate from authentic platform hosts (`youtube.com`, `tiktok.com`, `instagram.com`, `x.com`) AND be authored by the designated creator handle (`creator_handle`) associated with `creator_address` — raw unauthenticated pastebins and arbitrary creator-controlled sites are strictly rejected on-chain.
   - **Account & Campaign Binding:** The AI consensus nodes verify that the video/post belongs to the authentic creator channel and embeds the specific `[Campaign: <id>]`.
   - **Transcript & Audio Provenance Compliance:** Verifies spoken product mentions, verbal CTA, language subtitles, and zero blacklist keywords.
   - **Frame & Visual Provenance Certification:** Distinguishes verified media markers (`[Visual Frame: <logo>]`) from mutable web text, defaulting to `PARTIAL` if visual frames cannot be certified from text alone.
4. **Decentralized Validator Consensus Dispute Resolution (Ownerless Slashing):**
   - **RELEASE/PARTIAL:** Payout enters a mandatory 24-hour cooling-off delay (`AWAITING_PAYOUT`). If no dispute occurs within 24h, payout is finalized.
   - **Safe Stake Protection:** Automatic stake slashing is decoupled from heuristic web scrapes. On non-compliance (`REFUND`), Brand receives 100% escrow refund, and Creator stake is safely returned to prevent loss from scraper glitches.
   - **Trustless Validator Consensus Slashing:** Single-sig owner control is completely eliminated! If a dispute is raised, resolution and stake slashing (`SLASH`) are determined 100% by GenLayer Multi-Agent LLM Consensus (`gl.vm.run_nondet`) based on transcript/frame provenance and creator account authentication. Stale disputes (>30 days) can be recovered via automated 50/50 split and stake refund.

## Adversarial & Regression Test Suite

An exhaustive test suite is implemented in [`tests/test_adversarial.py`](./tests/test_adversarial.py) (13 tests), [`tests/test_affiliate_guard.py`](./tests/test_affiliate_guard.py) (3 tests), [`tests/test_evidence_binding.py`](./tests/test_evidence_binding.py) (4 tests), and [`tests/test_adversarial.js`](./tests/test_adversarial.js) (12 simulations) covering:
- **Authentic Platform Domain & Creator Account Enforcement**: Rejects unauthenticated pastebins and raw creator-controlled web URLs.
- **Evidence Binding & Anti-Replay Defense**: Rejects unauthenticated third-party content lacking campaign ID and creator handle proof.
- **Transcript & Frame Provenance Verification**: Distinguishes authentic visual media markers from plain mutable page text (yielding `PARTIAL` rather than full `RELEASE`).
- **Safe Stake Protection**: Verifies Creator stake is never blindly slashed on heuristic scrapes.
- **Trustless Validator Consensus Slashing**: Slashing is exclusively executable via multi-agent validator consensus (`gl.vm.run_nondet`) on confirmed fraud, completely eliminating owner control.
- **Under-Staking Defense**: Rejects stake amounts < 20%.
- **Early/Unauthorized Payout Defense**: Enforces 24h cooling-off and caller authorization for all parties.
- **Anti-Timestamp-Manipulation**: Validates 7-day cancellation timeout using trusted context.
- **Validator Disagreement Handling**: Verifies consensus passes on semantic equivalence and reverts on disagreement.
- **Ownerless Dispute Resolution Defense**: Prevents malicious self-refunds and enforces consensus arbitration.
- **Terminal Fund Flows**: Release, Partial, Escrow Refund, Consensus Dispute Resolution, and Stale Recovery.
