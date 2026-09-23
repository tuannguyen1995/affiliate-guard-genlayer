# AffiliateGuard Security & Threat Model Specification

## 1. Threat Model & Adversary Analysis

AffiliateGuard operates under the assumption that both Brands and Creators may act maliciously, collude, or attempt to exploit external web scraper and LLM non-determinism.

| Threat Actor | Motivation | Attack Vector | Mitigation in AffiliateGuard |
|---|---|---|---|
| **Malicious Creator** | Claim escrow without producing valid media | Substring URL tricks (e.g. `attacker.com/youtube.com`), unauthenticated pastebins, AI prompt injection in video titles, replaying another creator's video | **Canonical Host Enforcement** (`_is_authenticated_platform_host`), **On-Chain Handle Binding** (`register_creator_handle`), **Transcript & Frame Provenance Verification**. |
| **Malicious Brand** | Get free promo by refusing to release escrow or seizing creator's stake | Filing frivolous disputes, claiming fraud to slash creator stake, stalling resolution | **Ownerless Multi-Agent Slashing** (`resolve_dispute` via `gl.vm.run_nondet`), **Safe Stake Decoupling** (routine scrape failures never slash stake), **30-Day Stale Recovery** (`recover_stale_dispute`). |
| **Unreliable Scraper** | Network latency, anti-bot Cloudflare screens, transient 404s | Maliciously causing false REFUND or slashing honest creators | Scraper errors result in `ESCALATE` (allowing creator appeal) rather than slashing. Unstructured text scrape is strictly capped at `PARTIAL`. |
| **Validator Disagreement** | Differing natural language explanations between validator LLMs | Consensus deadlock causing transaction failure | **Semantic Verdict Comparison**: `validator_fn` compares only the uppercase outcome enum (`RELEASE`, `PARTIAL`, `REFUND`, `SLASH`, `SPLIT`), completely disregarding variations in the explanation string. |

---

## 2. The 5 Core Invariant Defenses

### Invariant 1: Canonical Host Filtering
```python
def _is_authenticated_platform_host(self, url: str) -> bool:
    host = self._extract_domain(url)
    allowed_base_domains = ["youtube.com", "youtu.be", "tiktok.com", "instagram.com", "x.com", "twitter.com"]
    for domain in allowed_base_domains:
        if host == domain or host.endswith("." + domain):
            return True
    return False
```
*Guarantees*: Rejects pastebin URLs, URL spoofing (`youtube.com.attacker.com`), and substring exploits (`attacker.com/youtube.com`).

### Invariant 2: Creator Identity & Handle Provenance
Creators register their handle on-chain (`register_creator_handle`). The consensus prompt requires structured platform metadata (JSON-LD author, oEmbed provider) to bind to this registered handle and the creator's wallet address.

### Invariant 3: The Non-Inference Rule for Visual Media
A webpage's text content cannot prove 2D visual frames. When a brand requires a visual logo or product appearance:
- Plain rendered text is **strictly capped at `PARTIAL`**.
- Full `RELEASE` strictly requires structured visual frame metadata.
- `PARTIAL` enforces a 24-hour brand cooling-off window for human visual verification.

### Invariant 4: Decoupling Scrapes from Stake Slashing
Routine non-compliance (e.g., forgetting a CTA keyword or minor wording issues) results in `REFUND` (brand receives escrow refund) while **safely returning the Creator's stake**. Creator stake is **never** blindly slashed due to heuristic scraper results.

### Invariant 5: Ownerless Dispute Slashing
Only deliberate, malicious fraud confirmed through multi-agent consensus (`gl.vm.run_nondet`) in `resolve_dispute()` can trigger `SLASH`. Single-sig owners or brands have zero ability to unilaterally seize or slash funds.

---

## 3. Automated Test Verification Matrix

All invariants are continuously verified by the automated test suite in `tests/`:

| Test Case | Scenario | Expected Outcome | Verified By |
|---|---|---|---|
| `test_01_under_staking_attack_reverts` | Creator stakes < 20% | Reverts with `UserError` | `test_adversarial.py` |
| `test_02_early_and_unauthorized_payout` | Finalizing payout before 24h cooling off | Reverts with `UserError` | `test_adversarial.py` |
| `test_03_timestamp_manipulation_defense` | Force cancel before 7 days | Reverts with `UserError` | `test_adversarial.py` |
| `test_04_validator_disagreement` | Validators agree on verdict but differ on wording | Consensus succeeds | `test_adversarial.py` |
| `test_05_brand_dispute_self_refund` | Brand attempts unilateral fund withdrawal | Must route through consensus | `test_adversarial.py` |
| `test_06_safe_stake_protection` | Repeated non-compliance | Escrow refunded, stake returned | `test_adversarial.py` |
| `test_07_stale_dispute_recovery` | Dispute stale for >30 days | 50/50 escrow split, stake returned | `test_adversarial.py` |
| `test_08_unbound_submission_replay` | Third-party URL submitted | Reverts or refunds | `test_adversarial.py` |
| `test_09_mutable_page_text_without_visual_cue` | Missing visual proof with brand logo | Capped at `PARTIAL` | `test_adversarial.py` |
| `test_10_unauthenticated_raw_web_domain` | Non-whitelisted domain | Reverts with `UserError` | `test_adversarial.py` |
| `test_11_validator_consensus_slashing` | Confirmed fraud during dispute | Slashing executed via consensus | `test_adversarial.py` |
| `test_12_unsupported_rendered_text_in_dispute` | Dispute based solely on raw scraped text | Cannot trigger `SLASH` or `RELEASE` | `test_adversarial.py` |
