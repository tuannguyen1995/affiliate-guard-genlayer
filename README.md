# AffiliateGuard

AffiliateGuard is a decentralized affiliate marketing escrow platform that uses GenLayer's Intelligent Contracts to automatically verify content requirements and process payouts via AI consensus.

## Deployed Contract
- **Contract Address:** `0xfb07EA145187d51B1AC8a7D97F21d9a3069B40d0`
- **GenLayer Explorer:** [https://genlayer-explorer.vercel.app/address/0xfb07EA145187d51B1AC8a7D97F21d9a3069B40d0](https://genlayer-explorer.vercel.app/address/0xfb07EA145187d51B1AC8a7D97F21d9a3069B40d0)

## Live App
- **Production URL:** [https://affiliateguard-one.vercel.app](https://affiliateguard-one.vercel.app)

## How it Works
1. **Brand Escrow:** Brands create a campaign with a designated Creator, escrow amount, and blacklist keywords.
2. **Creator Acceptance & Staking:** The designated Creator deposits a mandatory 20% stake to accept the campaign terms (skin-in-the-game to prevent spam).
3. **AI Video Verification:** The Creator submits their video. GenLayer's built-in AI consensus nodes fetch the content (`gl.nondet.web.render`), check for keywords, verify product mentions, verify CTA, and check visual brand logo requirements.
4. **Auto Payout / Revision / Dispute:**
   - **RELEASE/PARTIAL:** Payout enters a 24-hour cooling-off delay (`AWAITING_PAYOUT`). The Brand can dispute the AI consensus if needed. If no dispute occurs within 24h, payout is finalized.
   - **REFUND / SLASHING:** If the video fails, the Creator gets 1 chance to revise and resubmit. If it fails twice, the Creator's stake is slashed and refunded along with the escrow to the Brand.
   - **DISPUTE RESOLUTION:** Authorized arbitrator can resolve disputes with `RELEASE`, `REFUND`, or `SPLIT`. Stale disputes (>30 days) can be recovered via automated 50/50 split and stake refund.

## Adversarial & Regression Test Suite

An exhaustive test suite is implemented in [`tests/test_adversarial.py`](./tests/test_adversarial.py) and [`tests/test_adversarial.js`](./tests/test_adversarial.js) covering:
- **Under-Staking Defense**: Rejects stake amounts < 20%.
- **Early/Unauthorized Payout Defense**: Enforces 24h cooling-off and caller authorization.
- **Anti-Timestamp-Manipulation**: Validates 7-day cancellation timeout using trusted context.
- **Validator Disagreement Handling**: Verifies consensus passes on semantic equivalence and reverts on disagreement.
- **Brand Dispute Exploit Defense**: Prevents malicious self-refunds.
- **Terminal Fund Flows**: Release, Partial, Slashing, Dispute Resolution, and Stale Recovery.
