# AffiliateGuard

AffiliateGuard is a decentralized affiliate marketing escrow platform that uses GenLayer's Intelligent Contracts to automatically verify content requirements and process payouts via AI consensus.

## Deployed Contract
- **Contract Address:** `0x8A319a554212c9AF4343EB30Aa904a480a9F0136`
- **GenLayer Explorer:** [https://genlayer-explorer.vercel.app/address/0x8A319a554212c9AF4343EB30Aa904a480a9F0136](https://genlayer-explorer.vercel.app/address/0x8A319a554212c9AF4343EB30Aa904a480a9F0136)

## Live App
- **Production URL:** [https://affiliateguard.vercel.app](https://affiliateguard.vercel.app)

## How it Works
1. **Brand Escrow:** Brands create a campaign with a designated Creator, escrow amount, product requirements, CTA, and blacklist keywords.
2. **Creator Acceptance & Staking:** The designated Creator deposits a mandatory 20% stake to accept the campaign terms (skin-in-the-game to prevent spam).
3. **Authentic Platform Evidence Verification:** The Creator submits their media URL. The contract enforces:
   - **Platform Domain Authenticity:** Submissions must originate from authentic platform hosts (`youtube.com`, `tiktok.com`, `instagram.com`, `x.com`) — raw unauthenticated pastebins and arbitrary creator-controlled sites are strictly rejected on-chain.
   - **Account & Campaign Binding:** The AI consensus nodes verify that the video/post belongs to the authentic creator channel and embeds the specific `[Campaign: <id>]`.
   - **Transcript & Audio Compliance:** Verifies spoken product mentions, verbal CTA, language subtitles, and zero blacklist keywords.
   - **Visual Compliance Authenticity:** Distinguishes verified media markers (`[Visual: <logo>]`) from mutable web text, defaulting to `PARTIAL` if visual frames cannot be certified from text alone.
4. **Decoupled Stake Protection & Dispute Flow:**
   - **RELEASE/PARTIAL:** Payout enters a mandatory 24-hour cooling-off delay (`AWAITING_PAYOUT`). If no dispute occurs within 24h, payout is finalized.
   - **Safe Stake Protection:** Automatic stake slashing is decoupled from heuristic web scrapes. On content non-compliance (`REFUND`), the Brand receives 100% escrow refund, and the Creator's stake is safely returned to prevent unjust loss from scraper glitches.
   - **Authorized Stake Slashing & Dispute Resolution:** Stake slashing is strictly reserved for authorized arbitration (`resolve_dispute` with `SLASH` by contract owner) upon verified malicious fraud. Stale disputes (>30 days) can be recovered via automated 50/50 split and stake refund.

## Adversarial & Regression Test Suite

An exhaustive test suite is implemented in [`tests/test_adversarial.py`](./tests/test_adversarial.py) (12 tests), [`tests/test_evidence_binding.py`](./tests/test_evidence_binding.py) (4 tests), and [`tests/test_adversarial.js`](./tests/test_adversarial.js) (11 simulations) covering:
- **Authentic Platform Domain Enforcement**: Rejects unauthenticated pastebins and raw creator-controlled web URLs.
- **Evidence Binding & Anti-Replay Defense**: Rejects unauthenticated third-party content lacking campaign ID and creator proof.
- **Visual Compliance Authenticity**: Distinguishes authentic visual media markers from plain mutable page text (yielding `PARTIAL` rather than full `RELEASE`).
- **Safe Stake Protection**: Verifies Creator stake is never blindly slashed on heuristic scrapes.
- **Authorized Arbitrator Slashing**: Slashing is exclusively executable by contract arbitrator on confirmed fraud.
- **Under-Staking Defense**: Rejects stake amounts < 20%.
- **Early/Unauthorized Payout Defense**: Enforces 24h cooling-off and caller authorization for all parties.
- **Anti-Timestamp-Manipulation**: Validates 7-day cancellation timeout using trusted context.
- **Validator Disagreement Handling**: Verifies consensus passes on semantic equivalence and reverts on disagreement.
- **Brand Dispute Exploit Defense**: Prevents malicious self-refunds.
- **Terminal Fund Flows**: Release, Partial, Escrow Refund, Dispute Resolution, and Stale Recovery.
