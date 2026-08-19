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
    owner: str

    def __init__(self):
        # DO NOT initialize TreeMap/DynArray here (Rule #2). GenVM automatically allocates memory.
        self.owner = str(gl.message.sender_address).lower()
        
    def _get_current_timestamp(self) -> bigint:
        """Derive trusted timestamp from GenLayer transaction execution context (gl.message_raw)"""
        dt_raw = gl.message_raw.get("datetime", None) if isinstance(gl.message_raw, dict) else None
        if not dt_raw:
            raise UserError("Trusted execution timestamp missing from transaction context")
        try:
            dt_str = str(dt_raw).strip()
            if dt_str:
                from datetime import datetime
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                ts = int(dt.timestamp())
                if ts > 0:
                    return bigint(ts)
        except Exception as e:
            raise UserError(f"Failed to parse trusted execution timestamp: {str(e)}")
        raise UserError("Invalid trusted execution timestamp in transaction context")

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
    def create_campaign(self, campaign_id: str, creator_address: str, blacklist_keywords: str, product_name: str, required_cta: str, required_lang: str, campaign_desc: str, brand_logo: str, logo_url: str) -> None:
        amount = gl.message.value
        if amount <= bigint(0):
            raise UserError("Escrow amount must be greater than 0")
        
        if campaign_id in self.campaigns:
            raise UserError("Campaign ID already exists")
            
        self.campaign_ids.append(campaign_id)
        self.campaigns[campaign_id] = Campaign(
            brand=str(gl.message.sender_address).lower(),
            creator=creator_address.lower(),
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
        if str(gl.message.sender_address).lower() != campaign.creator.lower():
            raise UserError("Only the Creator can accept")
        if campaign.status != "PENDING_ACCEPTANCE":
            raise UserError("Campaign is not pending acceptance")
            
        stake_amount = gl.message.value
        min_required_stake = campaign.escrow_amount // bigint(5) # Enforce 20% minimum stake
        if stake_amount < min_required_stake or stake_amount <= bigint(0):
            raise UserError(f"Insufficient stake: Creator must stake at least 20% of escrow ({min_required_stake})")
            
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
        if campaign.cancel_requested_at == bigint(0):
            raise UserError("Cancel request timestamp was not set")
            
        now = self._get_current_timestamp()
        # 7 days = 604800 seconds
        if now < campaign.cancel_requested_at + bigint(604800):
            raise UserError("7 days have not passed since the cancel request")
            
        campaign.status = "CANCELLED"
        self.campaigns[campaign_id] = campaign
        
        gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(campaign.escrow_amount))
        if campaign.creator_stake > bigint(0):
            gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(campaign.creator_stake))

    @gl.public.write
    def submit_video(self, campaign_id: str, video_url: str) -> None:
        if campaign_id not in self.campaigns:
             raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
             
        if str(gl.message.sender_address).lower() != campaign.creator.lower():
            raise UserError("Only the designated creator can submit the video URL")
        if campaign.status not in ["OPEN", "CANCEL_REQUESTED", "NEEDS_REVISION"]:
            raise UserError("Campaign is not OPEN, pending cancellation, or needing revision")
        
        campaign.video_url = video_url
        campaign.status = "IN_PROGRESS"
        self.campaigns[campaign_id] = campaign
        
        # Capture variables into scope for closure
        target_url = str(video_url)
        blacklist = str(campaign.blacklist_keywords)
        p_name = str(campaign.product_name)
        c_cta = str(campaign.required_cta)
        r_lang = str(campaign.required_lang)
        b_logo = str(campaign.brand_logo)
        l_url = str(campaign.logo_url)

        def leader_fn():
            try:
                res_web = gl.nondet.web.render(target_url, mode="text")
                content = res_web.content if hasattr(res_web, "content") else str(res_web)
                if any(err in content[:400].lower() for err in ["404 not found", "error 404", "not found"]):
                    return {"verdict": "ESCALATE", "confidence": 100, "reason": "Network error or 404 - No content retrieved."}
            except Exception as e:
                return {"verdict": "ESCALATE", "confidence": 100, "reason": f"Network error or 404: {str(e)}"}
                
            prompt = f"""
            You are an advanced AI consensus judge for an affiliate marketing campaign.
            The required product to review is: {p_name}.
            Required brand logo visual descriptor: {b_logo}.
            Reference logo image URL (if provided): {l_url}.
            Review the following video content meticulously.

            Check strictly if:
            1. The required product ({p_name}) is mentioned clearly.
            2. There is a clear Call-To-Action (CTA) matching this requirement: {c_cta}.
            3. There are localized subtitles or speech in these required languages: {r_lang}.
            4. The creator strictly AVOIDED these blacklist keywords: {blacklist}.
            5. If a brand logo is required (descriptor: "{b_logo}" is not "None"), verify if the brand logo/identity/watermark is visually mentioned, displayed, overlayed, or captioned in the video content.

            Return ONLY a JSON with this format:
            {{"verdict": "RELEASE|PARTIAL|REFUND|ESCALATE", "confidence": 100, "reason": "str"}}

            - RELEASE: All criteria met, no blacklist words used.
            - PARTIAL: Good video but missing localized subtitles/languages, or missing required logo visual check.
            - REFUND: Missing product mention, missing CTA, or used blacklist words.
            - ESCALATE: Cannot determine the video content.

            Video Content:
            {content[:3000]}
            """
            try:
                llm_res = gl.nondet.exec_prompt(prompt, response_format="json")
                text_res = llm_res.content if hasattr(llm_res, "content") else str(llm_res)
                parsed = self._parse_llm_json(text_res)
                
                # Check confidence score
                if int(parsed.get("confidence", 0)) < 65:
                    parsed["verdict"] = "ESCALATE"
                    parsed["reason"] = "[Low Confidence] " + str(parsed.get("reason", ""))
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

        target_url = str(campaign.video_url)
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
            You are the final appellate judge for a disputed affiliate campaign.
            The required product was: {p_name}
            Required CTA: {c_cta}
            Required Subtitles / Languages: {r_lang}
            Required Brand Logo Descriptor: {b_logo}
            Reference Logo Image URL: {l_url}
            Blacklist to avoid: {blacklist}
            
            The creator's video was previously flagged. They have submitted an explanation:
            {appeal_text}
            
            Video Content to review:
            {content[:3000]}
            
            Based on their explanation and the video content, decide the final outcome.
            Return ONLY a JSON: {{"verdict": "RELEASE|PARTIAL|REFUND", "confidence": 100, "reason": "str"}}
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
            
        campaign.verdict = f"APPEAL_{verdict}"
        campaign.reason = str(result.get("reason", "No reason provided"))
        campaign.confidence = bigint(100)
        
        self.campaigns[campaign_id] = campaign
        self._process_payout(campaign_id, verdict)

    def _process_payout(self, campaign_id: str, verdict: str) -> None:
        """Utility function to handle payout logic with Slashing/Staking and Payout Delay"""
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
                # SLASHING APPLIED: Creator failed twice. Brand receives the escrow AND seizes the Creator's stake.
                total_refund = campaign.escrow_amount + campaign.creator_stake
                gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(total_refund))
        else: # ESCALATE state (from initial check)
            campaign.status = "ESCALATED"
            
        self.campaigns[campaign_id] = campaign

    @gl.public.write
    def dispute_verdict(self, campaign_id: str) -> None:
        """Allows Brand to dispute AI verdict during cooling-off window"""
        if campaign_id not in self.campaigns:
            raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        if str(gl.message.sender_address).lower() != campaign.brand.lower():
            raise UserError("Only the Brand can dispute")
        if campaign.status != "AWAITING_PAYOUT":
            raise UserError("Can only dispute during AWAITING_PAYOUT phase")
            
        campaign.status = "DISPUTED"
        campaign.disputed_at = self._get_current_timestamp()
        self.campaigns[campaign_id] = campaign

    @gl.public.write
    def finalize_payout(self, campaign_id: str) -> None:
        """Finalizes payout after 24h cooling-off delay for all authorized participants"""
        if campaign_id not in self.campaigns:
            raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        if campaign.status != "AWAITING_PAYOUT":
            raise UserError("Campaign is not awaiting payout")
            
        caller = str(gl.message.sender_address).lower()
        if caller != campaign.brand.lower() and caller != campaign.creator.lower():
            raise UserError("Unauthorized: Only brand or creator can finalize payout")

        if campaign.payout_ready_at == bigint(0):
            raise UserError("Payout ready timestamp was not properly initialized")

        # Enforce cooling-off delay strictly for ALL callers (including Brand and Creator)
        now = self._get_current_timestamp()
        if now < campaign.payout_ready_at:
            raise UserError("Payout cooling-off delay (24 hours) has not elapsed yet")
            
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
    def resolve_dispute(self, campaign_id: str, resolution: str) -> None:
        """
        Authorized resolution path for disputed escrow.
        SECURITY: 
        - Owner/Arbitrator can decide RELEASE, REFUND, or SPLIT.
        - Brand can ONLY voluntarily RELEASE funds (concession). Brand cannot self-refund or seize creator stake!
        """
        if campaign_id not in self.campaigns:
            raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        if campaign.status != "DISPUTED":
            raise UserError("Campaign is not in DISPUTED status")
            
        caller = str(gl.message.sender_address).lower()
        if caller != self.owner and caller != campaign.brand.lower():
            raise UserError("Unauthorized: Only contract owner/arbitrator or brand can execute dispute resolution")

        resolution_upper = str(resolution).upper().strip()
        
        # Anti-exploit check: Brand can only voluntarily release funds to creator
        if caller == campaign.brand.lower() and caller != self.owner and resolution_upper != "RELEASE":
            raise UserError("Brand can only voluntarily RELEASE funds to creator. Only owner/arbitrator can enforce REFUND or SPLIT.")

        amount = campaign.escrow_amount
        stake = campaign.creator_stake
        
        campaign.status = "CLOSED"
        if resolution_upper == "RELEASE":
            # Award full payment + stake to creator
            gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(amount + stake))
        elif resolution_upper == "REFUND":
            # Refund escrow + slashed stake to brand (only owner/arbitrator can trigger this)
            gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(amount + stake))
        elif resolution_upper == "SPLIT":
            # Split escrow 50/50 and return stake to creator
            half = amount // bigint(2)
            rem = amount - half
            gl.get_contract_at(Address(campaign.creator)).emit_transfer(value=u256(half + stake))
            gl.get_contract_at(Address(campaign.brand)).emit_transfer(value=u256(rem))
        else:
            raise UserError("Invalid resolution: Must be RELEASE, REFUND, or SPLIT")
            
        self.campaigns[campaign_id] = campaign

    @gl.public.write
    def recover_stale_dispute(self, campaign_id: str) -> None:
        """Recovery path for stale disputes: If dispute sits for >30 days (2592000s), split 50/50 & return stake"""
        if campaign_id not in self.campaigns:
            raise UserError("Campaign not found")
        campaign = self.campaigns[campaign_id]
        if campaign.status != "DISPUTED":
            raise UserError("Campaign is not in DISPUTED status")
        if campaign.disputed_at == bigint(0):
            raise UserError("Dispute timestamp was not set")
            
        caller = str(gl.message.sender_address).lower()
        if caller != campaign.brand.lower() and caller != campaign.creator.lower() and caller != self.owner:
            raise UserError("Unauthorized: Only participants or owner can recover stale dispute")
            
        now = self._get_current_timestamp()
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
