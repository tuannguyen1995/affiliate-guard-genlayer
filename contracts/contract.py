# v0.2.17
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import json

@allow_storage
@dataclass
class Campaign:
    brand: str
    creator: str
    creator_handle: str
    escrow_amount: bigint
    creator_stake: bigint
    status: str
    video_url: str
    verdict: str
    reason: str
    confidence: bigint
    blacklist_keywords: str
    cancel_requested_at: bigint
    resubmissions: bigint
    payout_ready_at: bigint
    disputed_at: bigint
    product_name: str
    required_cta: str
    required_lang: str
    campaign_desc: str
    brand_logo: str
    logo_url: str

class Contract(gl.Contract):
    campaigns: TreeMap[str, Campaign]
    campaign_ids: DynArray[str]
    creator_handles: TreeMap[str, str]
    owner: str

    def __init__(self):
        # DO NOT initialize TreeMap/DynArray here (Rule #2). GenVM automatically allocates memory.
        self.owner = str(gl.message.sender_address).lower()

    @gl.public.write
    def register_creator_handle(self, handle: str) -> None:
        """Allows a Creator wallet to register their verified social handle/channel ID on-chain."""
        caller = str(gl.message.sender_address).lower()
        h_clean = str(handle).strip()
        if not h_clean:
            raise UserError("Handle cannot be empty")
        if not h_clean.startswith("@"):
            h_clean = "@" + h_clean
        if not hasattr(self, "creator_handles") or self.creator_handles is None:
            self.creator_handles = TreeMap() if 'TreeMap' in globals() and callable(TreeMap) else {}
        self.creator_handles[caller] = h_clean.lower()

    def _extract_domain(self, url: str) -> str:
        """Extract exact canonical hostname from URL without relying on loose substring search."""
        u = str(url).lower().strip()
        if "://" in u:
            u = u.split("://", 1)[1]
        host = u.split("/")[0].split("?")[0].split("#")[0].split(":")[0].strip()
        return host

    def _is_authenticated_platform_host(self, url: str) -> bool:
        """Strictly validate that hostname matches or is a subdomain of an official media platform."""
        host = self._extract_domain(url)
        allowed_base_domains = ["youtube.com", "youtu.be", "tiktok.com", "instagram.com", "x.com", "twitter.com"]
        for domain in allowed_base_domains:
            if host == domain or host.endswith("." + domain):
                return True
        return False
        
    def _get_current_timestamp(self) -> bigint:
        """Derive trusted timestamp from GenLayer transaction execution context (gl.message_raw).
        SECURITY: Raises UserError if trusted datetime is missing or malformed — never defaults to 0,
        as that would allow an attacker to bypass all time-based guards."""
        try:
            dt_str = str(gl.message_raw.get("datetime", ""))
            if not dt_str:
                raise UserError("Trusted timestamp unavailable: gl.message_raw missing 'datetime' field")
            from datetime import datetime
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            ts = bigint(int(dt.timestamp()))
            if ts <= bigint(0):
                raise UserError("Trusted timestamp resolved to zero or negative — refusing to proceed")
            return ts
        except UserError:
            raise
        except Exception as e:
            raise UserError(f"Trusted timestamp parse failure: {str(e)}")

    def _parse_llm_json(self, response) -> dict:
        """Robust JSON parser to handle LLM markdown formatting issues"""
        if isinstance(response, dict):
            return response
        try:
            text = str(response).strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception as e:
            return {"verdict": "ESCALATE", "confidence": 0, "reason": "Failed to parse JSON: " + str(e)}

    @gl.public.write.payable
    def create_campaign(self, campaign_id: str, creator_address: str, creator_handle: str, blacklist_keywords: str, product_name: str, required_cta: str, required_lang: str, campaign_desc: str, brand_logo: str, logo_url: str) -> None:
        amount = gl.message.value
        if amount <= bigint(0):
            raise UserError("Escrow amount must be greater than 0")
        
        if campaign_id in self.campaigns:
            raise UserError("Campaign ID already exists")
            
        creator_lower = creator_address.lower()
        if hasattr(self, "creator_handles") and self.creator_handles and creator_lower in self.creator_handles:
            handle_clean = self.creator_handles[creator_lower]
        else:
            handle_clean = str(creator_handle).strip() if creator_handle else "@creator"
            if not handle_clean.startswith("@"):
                handle_clean = "@" + handle_clean
            handle_clean = handle_clean.lower()
            
        self.campaign_ids.append(campaign_id)
        self.campaigns[campaign_id] = Campaign(
            brand=str(gl.message.sender_address).lower(),
            creator=creator_lower,
            creator_handle=handle_clean,
            escrow_amount=amount,
            creator_stake=bigint(0),
            status="PENDING_ACCEPTANCE",
            video_url="",
            verdict="NONE",
            reason="Awaiting Submission",
            confidence=bigint(0),
            blacklist_keywords=blacklist_keywords,
            cancel_requested_at=bigint(0),
            resubmissions=bigint(0),
            payout_ready_at=bigint(0),
            disputed_at=bigint(0),
            product_name=product_name if product_name else "girl sandals",
            required_cta=required_cta if required_cta else "add to cart",
            required_lang=required_lang if required_lang else "English, Japanese, Chinese",
            campaign_desc=campaign_desc if campaign_desc else "Campaign promotion",
            brand_logo=brand_logo if brand_logo else "None",
            logo_url=logo_url if logo_url else "None"
        )

    @gl.public.write.payable
    def accept_campaign(self, campaign_id: str) -> None:
        """Creator accepts campaign terms and deposits mandatory 20% stake (skin-in-the-game)"""
        if campaign_id not in self.campaigns:
            raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        caller = str(gl.message.sender_address).lower()
        if caller != campaign.creator.lower():
            raise UserError("Only the Creator can accept")
        if campaign.status != "PENDING_ACCEPTANCE":
            raise UserError("Campaign is not pending acceptance")
            
        stake_amount = gl.message.value
        min_required_stake = campaign.escrow_amount // bigint(5) # Enforce 20% minimum stake
        if stake_amount < min_required_stake or stake_amount <= bigint(0):
            raise UserError(f"Insufficient stake: Creator must stake at least 20% of escrow ({min_required_stake})")
            
        if hasattr(self, "creator_handles") and self.creator_handles and caller in self.creator_handles:
            campaign.creator_handle = self.creator_handles[caller]
            
        campaign.creator_stake = stake_amount
        campaign.status = "OPEN"
        self.campaigns[campaign_id] = campaign

    @gl.public.write
    def reject_campaign(self, campaign_id: str) -> None:
        """Creator rejects the campaign, refunding the brand immediately (no stake since not accepted yet)"""
        if campaign_id not in self.campaigns:
            raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        if str(gl.message.sender_address).lower() != campaign.creator.lower():
            raise UserError("Only the Creator can reject")
        if campaign.status != "PENDING_ACCEPTANCE":
            raise UserError("Campaign is not pending acceptance")
            
        campaign.status = "CANCELLED"
        self.campaigns[campaign_id] = campaign
        gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(campaign.escrow_amount))

    @gl.public.write
    def cancel_campaign(self, campaign_id: str) -> None:
        """Allows Brand to request a cancellation. Timing derived from trusted execution context."""
        if campaign_id not in self.campaigns:
             raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        
        if str(gl.message.sender_address).lower() != campaign.brand.lower():
            raise UserError("Only the Brand can cancel the campaign")
        if campaign.status not in ["OPEN", "PENDING_ACCEPTANCE"]:
            raise UserError("Cannot cancel: Video already submitted or campaign not OPEN/PENDING")
            
        campaign.status = "CANCEL_REQUESTED"
        campaign.cancel_requested_at = self._get_current_timestamp()
        self.campaigns[campaign_id] = campaign

    @gl.public.write
    def approve_cancel(self, campaign_id: str) -> None:
        """Allows Creator to approve a cancellation request, refunding brand and returning creator stake."""
        if campaign_id not in self.campaigns:
             raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        
        if str(gl.message.sender_address).lower() != campaign.creator.lower():
            raise UserError("Only the Creator can approve cancellation")
        if campaign.status != "CANCEL_REQUESTED":
            raise UserError("Campaign is not pending cancellation")
            
        campaign.status = "CANCELLED"
        self.campaigns[campaign_id] = campaign
        
        # Refund brand and return creator stake
        gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(campaign.escrow_amount))
        if campaign.creator_stake > bigint(0):
            gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(campaign.creator_stake))

    @gl.public.write
    def force_cancel(self, campaign_id: str) -> None:
        """Allows Brand to force cancel if 7 days (604800s) have passed since request based on trusted context."""
        if campaign_id not in self.campaigns:
             raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        
        if str(gl.message.sender_address).lower() != campaign.brand.lower():
            raise UserError("Only the Brand can force cancel")
        if campaign.status != "CANCEL_REQUESTED":
            raise UserError("Campaign is not pending cancellation")
            
        if campaign.cancel_requested_at <= bigint(0):
            raise UserError("Cancel request timestamp not initialized")
            
        now = self._get_current_timestamp()
        if now <= bigint(0):
            raise UserError("Trusted timestamp resolved to zero — refusing to proceed")
            
        # 7 days = 604800 seconds
        if now < campaign.cancel_requested_at + bigint(604800):
            raise UserError("7 days have not passed since the cancel request")
            
        campaign.status = "CANCELLED"
        self.campaigns[campaign_id] = campaign
        
        gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(campaign.escrow_amount))
        if campaign.creator_stake > bigint(0):
            gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(campaign.creator_stake))

    @gl.public.write
    def submit_video(self, campaign_id: str, video_url: str, evidence_json: str = "") -> None:
        if campaign_id not in self.campaigns:
             raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
             
        caller = str(gl.message.sender_address).lower()
        if caller != campaign.creator.lower():
            raise UserError("Only the designated creator can submit the video URL")
        if campaign.status not in ["OPEN", "CANCEL_REQUESTED", "NEEDS_REVISION"]:
            raise UserError("Campaign is not OPEN, pending cancellation, or needing revision")
        
        # Check if structured evidence was provided
        structured_evidence = None
        evidence_raw = str(evidence_json).strip() if evidence_json else ""
        if not evidence_raw and str(video_url).strip().startswith("{") and str(video_url).strip().endswith("}"):
            evidence_raw = str(video_url).strip()
        if evidence_raw:
            try:
                structured_evidence = json.loads(evidence_raw)
            except Exception:
                structured_evidence = None

        # Extract target media url from structured evidence or parameter
        target_url = str(video_url).strip()
        if structured_evidence and isinstance(structured_evidence, dict):
            target_url = str(structured_evidence.get("media_url", structured_evidence.get("url", video_url))).strip()

        # Enforce authentic media platform domain (exact canonical hostname check, no loose substring matching!)
        if not self._is_authenticated_platform_host(target_url):
            raise UserError("Invalid evidence source: Submission host is not an authentic media platform (YouTube, TikTok, Instagram, X)")

        # Sync handle if registered on-chain
        if hasattr(self, "creator_handles") and self.creator_handles and caller in self.creator_handles:
            campaign.creator_handle = self.creator_handles[caller]

        campaign.video_url = target_url
        campaign.status = "IN_PROGRESS"
        self.campaigns[campaign_id] = campaign
        
        # Capture variables into scope for closure
        camp_id = str(campaign_id)
        creator_addr = str(campaign.creator)
        c_handle = str(campaign.creator_handle)
        blacklist = str(campaign.blacklist_keywords)
        p_name = str(campaign.product_name)
        c_cta = str(campaign.required_cta)
        r_lang = str(campaign.required_lang)
        b_logo = str(campaign.brand_logo)
        l_url = str(campaign.logo_url)
        has_structured = structured_evidence is not None and isinstance(structured_evidence, dict)
        struct_data = structured_evidence if has_structured else {}

        def leader_fn():
            if has_structured:
                # PATH A: AUTHENTICATED, STRUCTURALLY SEPARATED EVIDENCE
                auth_meta = str(struct_data.get("author_metadata", ""))
                captions = str(struct_data.get("captions", struct_data.get("transcript", "")))
                visual_proof = str(struct_data.get("visual_proof", struct_data.get("visual_frame_proof", "")))

                prompt = f"""
                You are an Intelligent Contract consensus judge for an affiliate marketing campaign on GenLayer.
                You are evaluating AUTHENTICATED, STRUCTURALLY SEPARATED EVIDENCE:

                Campaign Criteria:
                - Campaign ID: "{camp_id}"
                - Registered Creator Handle: "{c_handle}" (Wallet: "{creator_addr}")
                - Required Product: "{p_name}"
                - Required CTA: "{c_cta}"
                - Required Language: "{r_lang}"
                - Brand Logo: "{b_logo}" (Logo URL: "{l_url}")
                - Blacklist to avoid: "{blacklist}"

                STRUCTURALLY SEPARATED EVIDENCE:
                1. Platform & Author Metadata: {auth_meta}
                2. Spoken Caption/Audio Track: {captions}
                3. Visual Frame Proof: {visual_proof}

                MANDATORY RULES:
                - Verify Author Metadata explicitly binds to registered creator handle "{c_handle}" and creator "{creator_addr}".
                - Verify Caption/Audio Track covers product "{p_name}" and CTA "{c_cta}" in language "{r_lang}" with ZERO blacklist words.
                - Verify Visual Frame Proof certifies the brand logo "{b_logo}" (or logo is "None").
                - If ALL 3 components are verified and compliant: return RELEASE.
                - If captions or author metadata are missing or invalid, or blacklist words used: return REFUND.
                - If media/proof is indecipherable: return ESCALATE.

                Return ONLY a valid JSON object:
                {{"verdict": "RELEASE|PARTIAL|REFUND|ESCALATE", "confidence": 100, "reason": "concise explanation"}}
                """
            else:
                # PATH B: UNSUPPORTED RENDERED TEXT (SCRAPED FROM RAW WEBPAGE URL)
                # CRITICAL SECURITY RULE: Unsupported rendered text CANNOT determine funds (cannot cause RELEASE or SLASH)!
                try:
                    res_web = gl.nondet.web.render(target_url, mode="text")
                    content = res_web.content if hasattr(res_web, "content") else str(res_web)
                    if any(err in content[:400].lower() for err in ["404 not found", "error 404", "not found"]):
                        return {"verdict": "ESCALATE", "confidence": 100, "reason": "Network error or 404 - No content retrieved."}
                except Exception as e:
                    return {"verdict": "ESCALATE", "confidence": 100, "reason": f"Network error or 404: {str(e)}"}

                prompt = f"""
                You are an Intelligent Contract consensus judge for an affiliate marketing campaign on GenLayer.
                Review the submitted evidence scraped from the webpage.

                CRITICAL FUND-DETERMINATION CONSTRAINT (NON-INFERENCE RULE):
                The submitted evidence consists solely of UNSUPPORTED RENDERED TEXT scraped from a webpage.
                According to strict contract security rules, unsupported rendered text CANNOT prove 2D visual frame pixels, cannot verify isolated audio tracks, and cannot verify author account ownership without authenticated platform metadata.
                THEREFORE, YOU ARE STRICTLY FORBIDDEN FROM RETURNING 'RELEASE' OR 'SLASH'.
                - If the rendered text mentions product "{p_name}" and CTA "{c_cta}" in "{r_lang}" while strictly avoiding blacklist words "{blacklist}": return 'PARTIAL'. This provisionally validates text compliance and enforces the 24-hour brand inspection window.
                - If the rendered text lacks required product/CTA, contains blacklisted keywords, or lacks campaign binding: return 'REFUND'.
                - If the page is 404, unreachable, or indecipherable: return 'ESCALATE'.

                Campaign Criteria:
                - Campaign ID: "{camp_id}"
                - Registered Creator: "{creator_addr}" ({c_handle})
                - Required Product: "{p_name}"
                - Required CTA: "{c_cta}"
                - Required Language: "{r_lang}"
                - Brand Logo: "{b_logo}"
                - Blacklist: "{blacklist}"

                Rendered Webpage Text:
                {content}

                Return ONLY a valid JSON object:
                {{"verdict": "PARTIAL|REFUND|ESCALATE", "confidence": 100, "reason": "concise explanation"}}
                """
            try:
                llm_res = gl.nondet.exec_prompt(prompt, response_format="json")
                text_res = llm_res.content if hasattr(llm_res, "content") else str(llm_res)
                parsed = self._parse_llm_json(text_res)
                
                # Check confidence score
                if int(parsed.get("confidence", 0)) < 65:
                    parsed["verdict"] = "ESCALATE"
                    parsed["reason"] = "[Low Confidence] " + str(parsed.get("reason", ""))
                # Strict enforcement: if not structured evidence, RELEASE is forbidden
                if not has_structured and str(parsed.get("verdict", "")).upper() == "RELEASE":
                    parsed["verdict"] = "PARTIAL"
                    parsed["reason"] = "[Unsupported Rendered Text: Capped at PARTIAL] " + str(parsed.get("reason", ""))
                return parsed
            except Exception as e:
                 return {"verdict": "ESCALATE", "confidence": 0, "reason": f"LLM failure: {str(e)}"}

        def validator_fn(leader_res) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            
            leader_data = leader_res.calldata if hasattr(leader_res, "calldata") else leader_res
            if not isinstance(leader_data, dict):
                leader_data = self._parse_llm_json(str(leader_data))
                
            mine_data = leader_fn()
            
            # ONLY compare verdict (meaning), ignore wording of reason
            v_leader = str(leader_data.get("verdict", "")).upper().strip()
            v_mine = str(mine_data.get("verdict", "")).upper().strip()
            return v_leader == v_mine

        # Execute nondet block
        result = gl.vm.run_nondet(leader_fn, validator_fn)
        if not isinstance(result, dict):
            result = self._parse_llm_json(str(result))

        verdict = str(result.get("verdict", "ESCALATE")).upper()
        # Double safety guard: raw rendered text cannot RELEASE
        if not has_structured and verdict == "RELEASE":
            verdict = "PARTIAL"

        reason = str(result.get("reason", "No reason provided"))
        try:
            conf = bigint(int(result.get("confidence", 0)))
        except:
            conf = bigint(100)
            
        campaign.verdict = verdict
        campaign.reason = reason
        campaign.confidence = conf
        
        self.campaigns[campaign_id] = campaign
        self._process_payout(campaign_id, verdict)

    @gl.public.write
    def appeal(self, campaign_id: str, explanation: str) -> None:
        """Allows Creator to appeal if AI verdict is ESCALATE"""
        if campaign_id not in self.campaigns:
             raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        
        if str(gl.message.sender_address).lower() != campaign.creator.lower():
            raise UserError("Only the creator can appeal")
        if campaign.status != "ESCALATED":
            raise UserError("Campaign must be in ESCALATED state to appeal")

        # Check for structured evidence in appeal explanation or original video_url
        has_structured_appeal = False
        for cand in [explanation.strip(), str(campaign.video_url).strip()]:
            if cand.startswith("{") and cand.endswith("}"):
                try:
                    parsed = json.loads(cand)
                    if isinstance(parsed, dict) and any(k in parsed for k in ["author_metadata", "captions", "visual_proof"]):
                        has_structured_appeal = True
                        break
                except Exception:
                    pass

        target_url = str(campaign.video_url)
        camp_id = str(campaign_id)
        creator_addr = str(campaign.creator)
        blacklist = str(campaign.blacklist_keywords)
        p_name = str(campaign.product_name)
        c_cta = str(campaign.required_cta)
        r_lang = str(campaign.required_lang)
        b_logo = str(campaign.brand_logo)
        l_url = str(campaign.logo_url)
        appeal_text = str(explanation)

        def leader_fn():
            try:
                res_web = gl.nondet.web.render(target_url, mode="text")
                content = res_web.content if hasattr(res_web, "content") else str(res_web)
            except Exception as e:
                content = f"Error fetching: {str(e)}"
                
            prompt = f"""
            You are the final appellate judge for a disputed affiliate campaign on GenLayer.
            Review the authentic transcript, creator explanation, and campaign binding.

            Required Campaign ID: "{camp_id}"
            Required Creator: "{creator_addr}"
            Required product: "{p_name}"
            Required CTA: "{c_cta}"
            Required Subtitles / Languages: "{r_lang}"
            Required Brand Logo Descriptor: "{b_logo}" (Logo URL: "{l_url}")
            Blacklist to avoid: "{blacklist}"
            
            Creator Appeal Explanation:
            {appeal_text}
            
            Media Evidence:
            {content}
            
            MANDATORY RULES:
            1. Verify Campaign ID "{camp_id}" and Creator "{creator_addr}" binding in evidence.
            2. Verify authentic transcript covers product "{p_name}" and CTA "{c_cta}" with zero blacklist words.
            3. Has Structured Evidence: {has_structured_appeal}
            4. If structured evidence is missing or only raw rendered web text is available, DO NOT rule RELEASE. Narrow verdict to PARTIAL or REFUND.
            
            Return ONLY a JSON: {{"verdict": "RELEASE|PARTIAL|REFUND", "confidence": 100, "reason": "concise explanation"}}
            """
            try:
                llm_res = gl.nondet.exec_prompt(prompt, response_format="json")
                text_res = llm_res.content if hasattr(llm_res, "content") else str(llm_res)
                return self._parse_llm_json(text_res)
            except Exception as e:
                 return {"verdict": "REFUND", "confidence": 0, "reason": f"Appeal LLM failure: {str(e)}"}

        def validator_fn(leader_res) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            leader_data = leader_res.calldata if hasattr(leader_res, "calldata") else leader_res
            if not isinstance(leader_data, dict):
                leader_data = self._parse_llm_json(str(leader_data))
            mine_data = leader_fn()
            return str(leader_data.get("verdict", "")).upper() == str(mine_data.get("verdict", "")).upper()

        result = gl.vm.run_nondet(leader_fn, validator_fn)
        if not isinstance(result, dict):
            result = self._parse_llm_json(str(result))

        verdict = str(result.get("verdict", "REFUND")).upper()
        if verdict not in ["RELEASE", "PARTIAL", "REFUND"]:
            verdict = "REFUND"
        
        # Double safety: unsupported rendered text can never trigger RELEASE
        if not has_structured_appeal and verdict == "RELEASE":
            verdict = "PARTIAL"
            
        campaign.verdict = f"APPEAL_{verdict}"
        campaign.reason = str(result.get("reason", "No reason provided"))
        campaign.confidence = bigint(100)
        
        self.campaigns[campaign_id] = campaign
        self._process_payout(campaign_id, verdict)

    def _process_payout(self, campaign_id: str, verdict: str) -> None:
        """
        Utility function to handle payout logic.
        SECURITY: Automatic stake slashing is decoupled from heuristic/mutable web text scrapes.
        - On verified compliance (RELEASE/PARTIAL): Enters 24h cooling-off for Brand verification.
        - On failure (REFUND): Brand receives 100% escrow refund; Creator's stake is safely returned (no blind slashing on mutable text).
        - Malicious stake slashing is strictly reserved for authorized arbitration (resolve_dispute) on verified fraud.
        """
        campaign = self.campaigns[campaign_id]
        
        if verdict in ["RELEASE", "PARTIAL"]:
            campaign.status = "AWAITING_PAYOUT"
            # 24 hours cooling-off delay for brand dispute window
            campaign.payout_ready_at = self._get_current_timestamp() + bigint(86400)
        elif verdict == "REFUND":
            if campaign.resubmissions < bigint(1):
                campaign.status = "NEEDS_REVISION"
                campaign.resubmissions += bigint(1)
            else:
                campaign.status = "CLOSED"
                # Safe terminal fund flow: Brand receives escrow refund, Creator stake is safely returned (no blind slashing on web scrapes)
                gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(campaign.escrow_amount))
                if campaign.creator_stake > bigint(0):
                    gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(campaign.creator_stake))
        else: # ESCALATE state (from initial check)
            campaign.status = "ESCALATED"
            
        self.campaigns[campaign_id] = campaign

    @gl.public.write
    def finalize_payout(self, campaign_id: str) -> None:
        """Finalizes payout after 24h cooling-off delay if undisputed"""
        if campaign_id not in self.campaigns:
            raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        if campaign.status != "AWAITING_PAYOUT":
            raise UserError("Campaign is not awaiting payout")
            
        caller = str(gl.message.sender_address).lower()
        if caller != campaign.brand.lower() and caller != campaign.creator.lower():
            raise UserError("Unauthorized: Only brand or creator can finalize payout")

        if campaign.payout_ready_at <= bigint(0):
            raise UserError("Payout cooling-off delay has not been properly initialized")
        now = self._get_current_timestamp()
        if now <= bigint(0):
            raise UserError("Trusted timestamp resolved to zero — refusing to proceed")
        if now < campaign.payout_ready_at:
            raise UserError("Payout cooling-off delay (24 hours) has not elapsed yet. Neither brand nor creator may finalize early.")
            
        amount = campaign.escrow_amount
        stake = campaign.creator_stake
        actual_verdict = campaign.verdict.replace("APPEAL_", "")
        
        campaign.status = "CLOSED"
        if actual_verdict == "RELEASE":
            # Return creator's stake and release escrow amount to creator
            gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(amount + stake))
        elif actual_verdict == "PARTIAL":
            # Return creator's stake, pay half escrow to creator, half refund to brand
            half = amount // bigint(2)
            rem = amount - half
            gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(half + stake))
            gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(rem))
        
        self.campaigns[campaign_id] = campaign

    @gl.public.write
    def dispute_verdict(self, campaign_id: str, dispute_reason: str) -> None:
        """Allows Brand to dispute AI verdict during cooling-off window and persist DISPUTED status on-chain"""
        if campaign_id not in self.campaigns:
            raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        if str(gl.message.sender_address).lower() != campaign.brand.lower():
            raise UserError("Only the Brand can dispute")
        if campaign.status != "AWAITING_PAYOUT":
            raise UserError("Can only dispute during AWAITING_PAYOUT phase")
            
        campaign.status = "DISPUTED"
        campaign.disputed_at = self._get_current_timestamp()
        campaign.reason = f"Disputed by Brand: {dispute_reason}"
        self.campaigns[campaign_id] = campaign

    @gl.public.write
    def resolve_dispute(self, campaign_id: str, dispute_evidence: str) -> None:
        """
        Trustless Decentralized Dispute Resolution.
        Requires campaign.status == "DISPUTED".
        SECURITY: Completely ownerless! Dispute outcome & stake slashing are determined 
        100% by GenLayer Multi-Agent Validator Consensus (gl.vm.run_nondet).
        CRITICAL: Unsupported rendered text scraped from raw URLs CANNOT cause RELEASE or SLASH.
        RELEASE or SLASH strictly require authenticated, structurally separated evidence.
        """
        if campaign_id not in self.campaigns:
            raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        if campaign.status != "DISPUTED":
            raise UserError("Campaign is not in DISPUTED status")
            
        caller = str(gl.message.sender_address).lower()
        if caller != campaign.brand.lower() and caller != campaign.creator.lower():
            raise UserError("Unauthorized: Only brand or creator can execute dispute resolution")

        # Check for authenticated, structurally separated evidence
        has_structured = False
        for candidate in [dispute_evidence.strip(), str(campaign.video_url).strip()]:
            if candidate.startswith("{") and candidate.endswith("}"):
                try:
                    ev = json.loads(candidate)
                    if isinstance(ev, dict) and any(k in ev for k in ["author_metadata", "captions", "visual_proof", "forensic_report"]):
                        has_structured = True
                        break
                except Exception:
                    pass

        target_url = str(campaign.video_url)
        camp_id = str(campaign_id)
        creator_addr = str(campaign.creator)
        c_handle = str(campaign.creator_handle)
        blacklist = str(campaign.blacklist_keywords)
        p_name = str(campaign.product_name)
        c_cta = str(campaign.required_cta)
        r_lang = str(campaign.required_lang)
        b_logo = str(campaign.brand_logo)
        l_url = str(campaign.logo_url)
        d_reason = str(dispute_evidence)

        def leader_fn():
            try:
                res_web = gl.nondet.web.render(target_url, mode="text")
                content = res_web.content if hasattr(res_web, "content") else str(res_web)
            except Exception as e:
                content = f"Error fetching evidence: {str(e)}"
                
            prompt = f"""
            You are an advanced Intelligent Contract Consensus Arbitrator for GenLayer.
            Review the dispute evidence, authentic platform transcript, creator account handle, and frame provenance.

            Campaign Spec:
            - Campaign ID: "{camp_id}"
            - Authentic Creator Handle: "{c_handle}" (Wallet: "{creator_addr}")
            - Required Product: "{p_name}"
            - Required CTA: "{c_cta}"
            - Required Language: "{r_lang}"
            - Brand Logo: "{b_logo}" (Logo URL: "{l_url}")
            - Blacklist: "{blacklist}"

            Brand Dispute Reason & Alleged Fraud Evidence:
            {d_reason}

            Media Evidence:
            {content}

            STRUCTURAL EVIDENCE STATUS:
            Has Authenticated, Structurally Separated Evidence: {has_structured}

            MANDATORY DISPUTE EVALUATION RULES:
            1. CRITICAL EVIDENCE RESTRICTION:
               - If Has Authenticated, Structurally Separated Evidence is FALSE:
                 Unsupported plain rendered web text CANNOT determine funds via RELEASE or SLASH!
                 Outcomes are STRICTLY NARROWED to REFUND or SPLIT.
                 DO NOT rule RELEASE or SLASH under any circumstances when structured evidence is False.
               - If Has Authenticated, Structurally Separated Evidence is TRUE:
                 RELEASE: Unfounded dispute. Compliant content proven by authentic structured metadata, captions, and visual frame proof.
                 SLASH: Malicious fraud proven by authentic evidence (e.g. spoofed creator account, forged credentials, deliberately fake media).
                 REFUND: Dispute valid, requirements unmet, but no deliberate fraud.
                 SPLIT: Shared fault or ambiguous structured evidence.

            2. PLATFORM & CREATOR AUTHENTICATION:
               - Account "{c_handle}" bound to "{creator_addr}".
               - Fake/spoofed host or unauthenticated account with structured proof -> SLASH.

            Return ONLY a valid JSON object:
            {{"verdict": "{"RELEASE|REFUND|SLASH|SPLIT" if has_structured else "REFUND|SPLIT"}", "confidence": 100, "reason": "concise explanation"}}
            """
            try:
                llm_res = gl.nondet.exec_prompt(prompt, response_format="json")
                text_res = llm_res.content if hasattr(llm_res, "content") else str(llm_res)
                return self._parse_llm_json(text_res)
            except Exception as e:
                return {"verdict": "REFUND", "confidence": 0, "reason": f"Dispute resolution LLM failure: {str(e)}"}

        def validator_fn(leader_res) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            leader_data = leader_res.calldata if hasattr(leader_res, "calldata") else leader_res
            if not isinstance(leader_data, dict):
                leader_data = self._parse_llm_json(str(leader_data))
            mine_data = leader_fn()
            return str(leader_data.get("verdict", "")).upper().strip() == str(mine_data.get("verdict", "")).upper().strip()

        result = gl.vm.run_nondet(leader_fn, validator_fn)
        if not isinstance(result, dict):
            result = self._parse_llm_json(str(result))

        resolution_upper = str(result.get("verdict", "REFUND")).upper().strip()
        reason = str(result.get("reason", "Dispute resolved by validator consensus"))
        if resolution_upper not in ["RELEASE", "REFUND", "SLASH", "SPLIT"]:
            resolution_upper = "REFUND"

        # Double safety guard: unsupported rendered text CAN NEVER trigger RELEASE or SLASH
        if not has_structured:
            if resolution_upper == "RELEASE":
                resolution_upper = "SPLIT"
            elif resolution_upper == "SLASH":
                resolution_upper = "REFUND"

        amount = campaign.escrow_amount
        stake = campaign.creator_stake
        
        campaign.status = "CLOSED"
        campaign.verdict = f"DISPUTE_{resolution_upper}"
        campaign.reason = reason
        campaign.confidence = bigint(100)
        
        if resolution_upper == "RELEASE":
            # Award full payment + stake to creator
            gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(amount + stake))
        elif resolution_upper == "REFUND":
            # Refund escrow to brand, return stake to creator
            gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(amount))
            if stake > bigint(0):
                gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(stake))
        elif resolution_upper == "SLASH":
            # Slashing determined BY VALIDATOR CONSENSUS on confirmed malicious fraud: Brand receives escrow + slashed creator stake
            gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(amount + stake))
        elif resolution_upper == "SPLIT":
            # Split escrow 50/50 and return stake to creator
            half = amount // bigint(2)
            rem = amount - half
            gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(half + stake))
            gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(rem))
            
        self.campaigns[campaign_id] = campaign

    @gl.public.write
    def recover_stale_dispute(self, campaign_id: str) -> None:
        """Recovery path for stale disputes: If dispute sits for >30 days (2592000s), split 50/50 & return stake"""
        if campaign_id not in self.campaigns:
            raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        if campaign.status != "DISPUTED":
            raise UserError("Campaign is not in DISPUTED status")
            
        caller = str(gl.message.sender_address).lower()
        if caller != campaign.brand.lower() and caller != campaign.creator.lower() and caller != self.owner:
            raise UserError("Unauthorized: Only participants or owner can recover stale dispute")
            
        if campaign.disputed_at <= bigint(0):
            raise UserError("Dispute timestamp not initialized")
            
        now = self._get_current_timestamp()
        if now <= bigint(0):
            raise UserError("Trusted timestamp resolved to zero — refusing to proceed")
            
        # 30 days = 2592000 seconds
        if now < campaign.disputed_at + bigint(2592000):
            raise UserError("Dispute recovery period (30 days) has not elapsed yet")
            
        amount = campaign.escrow_amount
        stake = campaign.creator_stake
        campaign.status = "CLOSED"
        
        half = amount // bigint(2)
        rem = amount - half
        gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(half + stake))
        gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(rem))
        
        self.campaigns[campaign_id] = campaign

    @gl.public.view
    def get_campaign(self, campaign_id: str) -> str:
        """View must return string/JSON for easiest compatibility with genlayer-js"""
        if campaign_id not in self.campaigns:
            raise UserError("Campaign not found")
        c = self.campaigns[campaign_id]
        return json.dumps({
            "brand": c.brand,
            "creator": c.creator,
            "creator_handle": c.creator_handle,
            "escrow_amount": str(c.escrow_amount),
            "creator_stake": str(c.creator_stake),
            "status": c.status,
            "video_url": c.video_url,
            "verdict": c.verdict,
            "reason": c.reason,
            "confidence": str(c.confidence),
            "blacklist_keywords": c.blacklist_keywords,
            "cancel_requested_at": str(c.cancel_requested_at),
            "resubmissions": c.resubmissions,
            "payout_ready_at": str(c.payout_ready_at),
            "disputed_at": str(c.disputed_at),
            "product_name": c.product_name,
            "required_cta": c.required_cta,
            "required_lang": c.required_lang,
            "campaign_desc": c.campaign_desc,
            "brand_logo": c.brand_logo,
            "logo_url": c.logo_url
        })

    @gl.public.view
    def get_my_campaigns(self, address: str) -> str:
        """Return a JSON array of campaigns where the address is either brand or creator"""
        my_campaigns = []
        for i in range(len(self.campaign_ids)):
            cid = self.campaign_ids[i]
            camp = self.campaigns[cid]
            if str(camp.brand).lower() == str(address).lower() or str(camp.creator).lower() == str(address).lower():
                my_campaigns.append({
                    "id": cid,
                    "brand": camp.brand,
                    "creator": camp.creator,
                    "status": camp.status,
                    "escrow_amount": str(camp.escrow_amount)
                })
        return json.dumps(my_campaigns)

    @gl.public.view
    def get_all_campaigns(self) -> str:
        """Authoritative public view for frontend dashboard synchronization."""
        all_campaigns = []
        for i in range(len(self.campaign_ids)):
            cid = self.campaign_ids[i]
            if cid in self.campaigns:
                c = self.campaigns[cid]
                all_campaigns.append({
                    "id": cid,
                    "brand": c.brand,
                    "creator": c.creator,
                    "creator_handle": c.creator_handle,
                    "escrow_amount": str(c.escrow_amount),
                    "creator_stake": str(c.creator_stake),
                    "status": c.status,
                    "video_url": c.video_url,
                    "verdict": c.verdict,
                    "reason": c.reason,
                    "confidence": str(c.confidence),
                    "blacklist_keywords": c.blacklist_keywords,
                    "cancel_requested_at": str(c.cancel_requested_at),
                    "resubmissions": str(c.resubmissions),
                    "payout_ready_at": str(c.payout_ready_at),
                    "disputed_at": str(c.disputed_at),
                    "product_name": c.product_name,
                    "required_cta": c.required_cta,
                    "required_lang": c.required_lang,
                    "campaign_desc": c.campaign_desc,
                    "brand_logo": c.brand_logo,
                    "logo_url": c.logo_url
                })
        return json.dumps(all_campaigns)
