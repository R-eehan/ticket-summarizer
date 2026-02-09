"""
Diagnostics Analysis Module for Zendesk Ticket Summarizer.

This module analyzes synthesized tickets to determine:
1. Was Diagnostics feature used? (by customer OR support team)
2. Could Diagnostics have helped? (to diagnose OR resolve the issue)
   - Phase 6 Enhancement: Split into TRIAGE (identification) vs FIX (resolution) assessments
   - Phase 7 Enhancement: Gap analysis when Diagnostics cannot help

Phase 3c: Multi-Model Support
Phase 6: Triage vs Fix split assessment with derived overall_assessment
Phase 7: Gap area taxonomy for coverage analysis (triage_gap_area, fix_gap_area)
Uses LLM provider abstraction (Gemini or Azure OpenAI) with Whatfix Diagnostics product knowledge.
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Callable
import config
import utils
from llm_provider import LLMProviderFactory


class DiagnosticsAnalyzer:
    """
    Async Diagnostics analyzer using LLM provider abstraction.

    Phase 3c: Now supports both Gemini and Azure OpenAI via LLMProviderFactory.
    Analyzes ticket synthesis to assess Diagnostics feature applicability,
    considering both custom field data and ticket content.
    """

    def __init__(self, model_provider: str = "gemini"):
        """
        Initialize Diagnostics analyzer with specified LLM provider.

        Args:
            model_provider: LLM provider name ("gemini" or "azure")
                           Defaults to "gemini" for backward compatibility

        Raises:
            ValueError: If provider credentials are missing or invalid
        """
        self.logger = logging.getLogger("ticket_summarizer.diagnostics_analyzer")
        self.model_provider = model_provider

        # Initialize LLM provider using factory pattern
        self.logger.info(f"Initializing Diagnostics analyzer with model provider: {model_provider}")
        self.llm_client = LLMProviderFactory.get_provider(model_provider)

        # Rate limiting: sequential processing for free tier
        self.semaphore = asyncio.Semaphore(config.GEMINI_MAX_CONCURRENT)
        self.request_delay = config.GEMINI_REQUEST_DELAY

        self.logger.info(f"Diagnostics analyzer initialized with {model_provider} provider")

    async def analyze_ticket(self, ticket_data: Dict) -> Dict:
        """
        Analyze a single ticket for Diagnostics applicability.

        Args:
            ticket_data: Dictionary containing ticket synthesis and custom fields

        Returns:
            Dictionary with diagnostics analysis results

        Raises:
            GeminiAPIError: If LLM call fails
        """
        ticket_id = ticket_data.get("ticket_id", "unknown")

        async with self.semaphore:
            self.logger.debug(f"Analyzing ticket {ticket_id} for Diagnostics applicability")

            try:
                # Extract synthesis data
                synthesis = ticket_data.get("synthesis", {})
                subject = ticket_data.get("subject", "No subject")
                issue_reported = synthesis.get("issue_reported", "Not available")
                root_cause = synthesis.get("root_cause", "Not available")
                summary = synthesis.get("summary", "Not available")
                resolution = synthesis.get("resolution", "Not available")

                # Extract custom field value
                custom_fields = ticket_data.get("custom_fields", {})
                custom_field_value = custom_fields.get("was_diagnostics_used", "unknown")

                # Extract escalation data (Phase 5)
                escalation = custom_fields.get("escalation", {})
                is_escalated = escalation.get("is_escalated", False)
                jira_ticket_id = escalation.get("jira_ticket_id", "None")

                # Extract support agent's root cause (Phase 6)
                support_root_cause = custom_fields.get("support_root_cause", "Not provided")

                # Format the prompt with ticket data
                prompt = self._format_diagnostics_prompt(
                    subject=subject,
                    issue_reported=issue_reported,
                    root_cause=root_cause,
                    summary=summary,
                    resolution=resolution,
                    custom_field_value=custom_field_value,
                    is_escalated=is_escalated,
                    jira_ticket_id=jira_ticket_id,
                    support_root_cause=support_root_cause
                )

                # Call LLM API (via provider abstraction)
                self.logger.debug(f"Calling LLM API for ticket {ticket_id}")
                response = await asyncio.to_thread(
                    self.llm_client.generate_content, prompt
                )

                # Parse response
                analysis_result = self._parse_diagnostics_response(response.text, ticket_id)

                # Add custom field value and derived overall assessment to the result
                if analysis_result:
                    analysis_result["was_diagnostics_used"]["custom_field_value"] = custom_field_value
                    analysis_result["metadata"]["analysis_timestamp"] = utils.get_current_ist_timestamp()

                    # Phase 6: Derive overall_assessment from triage + fix
                    could_help = analysis_result.get("could_diagnostics_help", {})
                    triage = could_help.get("triage_assessment", "maybe")
                    fix = could_help.get("fix_assessment", "no")
                    overall = self._derive_overall_assessment(triage, fix)
                    analysis_result["could_diagnostics_help"]["overall_assessment"] = overall

                    # Generate overall_reasoning
                    if overall == "yes":
                        overall_reasoning = "Diagnostics could both identify and help fix the issue."
                    elif overall == "maybe":
                        if triage == "yes":
                            overall_reasoning = "Diagnostics could help identify the issue but not resolve it."
                        else:
                            overall_reasoning = "Partial help possible - details uncertain."
                    else:
                        overall_reasoning = "Diagnostics could not help with this issue."
                    analysis_result["could_diagnostics_help"]["overall_reasoning"] = overall_reasoning

                self.logger.info(f"Successfully analyzed ticket {ticket_id}")

                # Add rate limiting delay
                await asyncio.sleep(self.request_delay)

                return analysis_result

            except Exception as e:
                self.logger.error(f"Failed to analyze ticket {ticket_id}: {e}")
                raise utils.GeminiAPIError(f"Diagnostics analysis failed for ticket {ticket_id}: {e}")

    def _format_diagnostics_prompt(
        self,
        subject: str,
        issue_reported: str,
        root_cause: str,
        summary: str,
        resolution: str,
        custom_field_value: str,
        is_escalated: bool,
        jira_ticket_id: str,
        support_root_cause: str = "Not provided"
    ) -> str:
        """
        Format the Diagnostics analysis prompt with ticket data.

        Args:
            subject: Ticket subject
            issue_reported: Issue reported from synthesis
            root_cause: Root cause from synthesis (LLM-inferred)
            summary: Summary from synthesis
            resolution: Resolution from synthesis
            custom_field_value: Normalized custom field value
            is_escalated: Whether ticket was escalated to Engineering (Phase 5)
            jira_ticket_id: JIRA ticket ID if escalated (Phase 5)
            support_root_cause: Support agent's root cause from Zendesk field (Phase 6)

        Returns:
            Formatted prompt string
        """
        return config.DIAGNOSTICS_ANALYSIS_PROMPT.format(
            subject=subject,
            issue_reported=issue_reported,
            root_cause=root_cause,
            summary=summary,
            resolution=resolution,
            custom_field_value=custom_field_value,
            is_escalated=is_escalated,
            jira_ticket_id=jira_ticket_id,
            support_root_cause=support_root_cause
        )

    def _parse_diagnostics_response(self, response_text: str, ticket_id: str) -> Optional[Dict]:
        """
        Parse LLM response and extract diagnostics analysis in JSON format.

        Phase 6 Update: The LLM now returns triage and fix assessments separately.
        The overall_assessment is derived programmatically after parsing.

        Phase 7 Update: Gap areas are normalized before validation - invalid values
        are auto-remapped to "other_*_gap" with original value preserved in description.

        Expected JSON structure:
        - was_diagnostics_used: {llm_assessment, confidence, reasoning}
        - could_diagnostics_help: {triage_assessment, triage_reasoning, fix_assessment, fix_reasoning,
                                   confidence, diagnostics_capability_matched, limitation_notes}
        - metadata: {ticket_type}

        Args:
            response_text: Raw response from LLM
            ticket_id: Ticket ID for logging

        Returns:
            Parsed diagnostics analysis dictionary, or None if parsing fails
        """
        try:
            # Extract JSON from response (LLM may wrap it in markdown code blocks)
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in LLM response")

            # Parse JSON
            analysis_data = json.loads(json_str)

            # Phase 7: Normalize gap areas before validation
            # This auto-remaps invalid values to "other_*_gap" with original value in description
            analysis_data = self._normalize_gap_areas(analysis_data, ticket_id)

            # Validate required fields
            if not self._validate_analysis_structure(analysis_data, ticket_id):
                return None

            self.logger.debug(f"Successfully parsed diagnostics analysis for ticket {ticket_id}")
            return analysis_data

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON for ticket {ticket_id}: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to parse diagnostics response for ticket {ticket_id}: {e}")
            return None

    def _normalize_gap_areas(self, analysis_data: Dict, ticket_id: str) -> Dict:
        """
        Normalize gap area values, auto-remapping invalid values to "other_*_gap".

        Phase 7 Enhancement: Instead of failing validation on invalid gap areas,
        this method preserves the LLM's intent by:
        1. Remapping invalid triage_gap_area to "other_triage_gap"
        2. Remapping invalid fix_gap_area to "other_fix_gap"
        3. Storing the original invalid value in the corresponding description field

        This ensures:
        - No data loss (original LLM value is preserved)
        - Pivot tables remain clean (only valid taxonomy values in gap_area columns)
        - PM can review "other" descriptions to evolve taxonomy over time

        Args:
            analysis_data: Parsed analysis dictionary from LLM
            ticket_id: Ticket ID for logging

        Returns:
            Analysis data with normalized gap areas
        """
        could_help = analysis_data.get("could_diagnostics_help", {})

        # Normalize triage_gap_area
        triage_gap = could_help.get("triage_gap_area")
        if triage_gap is not None and triage_gap not in config.TRIAGE_GAP_AREAS:
            original_value = triage_gap
            existing_description = could_help.get("triage_gap_description") or ""

            # Build new description with original value
            if existing_description:
                new_description = f"[Auto-remapped from '{original_value}'] {existing_description}"
            else:
                new_description = f"[Auto-remapped from '{original_value}'] LLM suggested this gap area which is not in the predefined taxonomy."

            could_help["triage_gap_area"] = "other_triage_gap"
            could_help["triage_gap_description"] = new_description

            self.logger.warning(
                f"Ticket {ticket_id}: Invalid triage_gap_area '{original_value}' auto-remapped to 'other_triage_gap'. "
                f"Original value preserved in triage_gap_description."
            )

        # Normalize fix_gap_area
        fix_gap = could_help.get("fix_gap_area")
        if fix_gap is not None and fix_gap not in config.FIX_GAP_AREAS:
            original_value = fix_gap
            existing_description = could_help.get("fix_gap_description") or ""

            # Build new description with original value
            if existing_description:
                new_description = f"[Auto-remapped from '{original_value}'] {existing_description}"
            else:
                new_description = f"[Auto-remapped from '{original_value}'] LLM suggested this gap area which is not in the predefined taxonomy."

            could_help["fix_gap_area"] = "other_fix_gap"
            could_help["fix_gap_description"] = new_description

            self.logger.warning(
                f"Ticket {ticket_id}: Invalid fix_gap_area '{original_value}' auto-remapped to 'other_fix_gap'. "
                f"Original value preserved in fix_gap_description."
            )

        # Update the analysis data
        analysis_data["could_diagnostics_help"] = could_help
        return analysis_data

    def _validate_analysis_structure(self, analysis_data: Dict, ticket_id: str) -> bool:
        """
        Validate the structure and values of the diagnostics analysis.

        Phase 6 Update: Now validates triage_assessment and fix_assessment instead of single assessment.
        Phase 7 Update: Gap area validation is now a safety net - invalid values are normalized
        to "other_*_gap" BEFORE this method is called (see _normalize_gap_areas).

        Checks:
        - Required fields exist
        - Enum values are valid (yes/no/unknown, yes/no/maybe, confident/not confident)
        - Reasoning fields are not empty
        - Gap areas are present when assessment is "no" or "maybe"
        - Gap area values are in the predefined taxonomy (safety check after normalization)

        Args:
            analysis_data: Parsed analysis dictionary (already normalized)
            ticket_id: Ticket ID for logging

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check top-level structure
            if "was_diagnostics_used" not in analysis_data:
                self.logger.error(f"Missing 'was_diagnostics_used' in ticket {ticket_id}")
                return False
            if "could_diagnostics_help" not in analysis_data:
                self.logger.error(f"Missing 'could_diagnostics_help' in ticket {ticket_id}")
                return False
            if "metadata" not in analysis_data:
                self.logger.error(f"Missing 'metadata' in ticket {ticket_id}")
                return False

            # Validate was_diagnostics_used
            was_used = analysis_data["was_diagnostics_used"]
            llm_assessment = was_used.get("llm_assessment", "").strip().lower()

            if not utils.validate_diagnostics_usage(llm_assessment):
                self.logger.warning(
                    f"Invalid llm_assessment '{llm_assessment}' for ticket {ticket_id}. "
                    f"Expected: yes, no, or unknown"
                )
                return False

            if not utils.validate_confidence(was_used.get("confidence", "")):
                self.logger.warning(
                    f"Invalid confidence for was_diagnostics_used in ticket {ticket_id}"
                )
                return False

            if not was_used.get("reasoning"):
                self.logger.warning(
                    f"Empty reasoning for was_diagnostics_used in ticket {ticket_id}"
                )
                return False

            # Validate could_diagnostics_help (Phase 6: triage + fix assessments)
            could_help = analysis_data["could_diagnostics_help"]

            # Validate triage_assessment
            triage_assessment = could_help.get("triage_assessment", "").strip().lower()
            if not utils.validate_diagnostics_assessment(triage_assessment):
                self.logger.warning(
                    f"Invalid triage_assessment '{triage_assessment}' for ticket {ticket_id}. "
                    f"Expected: yes, no, or maybe"
                )
                return False

            if not could_help.get("triage_reasoning"):
                self.logger.warning(
                    f"Empty triage_reasoning for ticket {ticket_id}"
                )
                return False

            # Validate fix_assessment
            fix_assessment = could_help.get("fix_assessment", "").strip().lower()
            if not utils.validate_diagnostics_assessment(fix_assessment):
                self.logger.warning(
                    f"Invalid fix_assessment '{fix_assessment}' for ticket {ticket_id}. "
                    f"Expected: yes, no, or maybe"
                )
                return False

            if not could_help.get("fix_reasoning"):
                self.logger.warning(
                    f"Empty fix_reasoning for ticket {ticket_id}"
                )
                return False

            # Phase 7: Validate triage_gap_area (required when triage_assessment != "yes")
            if triage_assessment in ["no", "maybe"]:
                triage_gap = could_help.get("triage_gap_area")
                if not triage_gap:
                    self.logger.warning(
                        f"Missing triage_gap_area for ticket {ticket_id} "
                        f"(required when triage_assessment={triage_assessment})"
                    )
                    return False
                if not utils.validate_triage_gap_area(triage_gap):
                    self.logger.warning(
                        f"Invalid triage_gap_area '{triage_gap}' for ticket {ticket_id}. "
                        f"Expected one of: {config.TRIAGE_GAP_AREAS}"
                    )
                    return False
                # If other_triage_gap, description is required
                if triage_gap == "other_triage_gap" and not could_help.get("triage_gap_description"):
                    self.logger.warning(
                        f"Missing triage_gap_description for other_triage_gap in ticket {ticket_id}"
                    )
                    return False

            # Phase 7: Validate fix_gap_area (required when fix_assessment != "yes")
            if fix_assessment in ["no", "maybe"]:
                fix_gap = could_help.get("fix_gap_area")
                if not fix_gap:
                    self.logger.warning(
                        f"Missing fix_gap_area for ticket {ticket_id} "
                        f"(required when fix_assessment={fix_assessment})"
                    )
                    return False
                if not utils.validate_fix_gap_area(fix_gap):
                    self.logger.warning(
                        f"Invalid fix_gap_area '{fix_gap}' for ticket {ticket_id}. "
                        f"Expected one of: {config.FIX_GAP_AREAS}"
                    )
                    return False
                # If other_fix_gap, description is required
                if fix_gap == "other_fix_gap" and not could_help.get("fix_gap_description"):
                    self.logger.warning(
                        f"Missing fix_gap_description for other_fix_gap in ticket {ticket_id}"
                    )
                    return False

            # Validate confidence
            if not utils.validate_confidence(could_help.get("confidence", "")):
                self.logger.warning(
                    f"Invalid confidence for could_diagnostics_help in ticket {ticket_id}"
                )
                return False

            # Validate metadata
            metadata = analysis_data["metadata"]
            ticket_type = metadata.get("ticket_type", "")
            valid_types = ["troubleshooting", "feature_request", "technical_request", "unclear"]

            if ticket_type not in valid_types:
                self.logger.warning(
                    f"Invalid ticket_type '{ticket_type}' for ticket {ticket_id}. "
                    f"Expected one of: {valid_types}"
                )
                return False

            self.logger.debug(f"Validation passed for ticket {ticket_id}")
            return True

        except Exception as e:
            self.logger.error(f"Validation error for ticket {ticket_id}: {e}")
            return False

    def _derive_overall_assessment(self, triage: str, fix: str) -> str:
        """
        Derive overall_assessment from triage and fix assessments.

        Phase 6: Programmatic derivation ensures consistency.

        Logic:
        - triage=yes AND fix=yes → "yes" (full self-service possible)
        - triage=yes AND fix=no/maybe → "maybe" (partial help - can identify but not fix)
        - triage=maybe → "maybe"
        - triage=no → "no"

        Args:
            triage: Triage assessment ("yes", "no", or "maybe")
            fix: Fix assessment ("yes", "no", or "maybe")

        Returns:
            Overall assessment ("yes", "no", or "maybe")
        """
        triage = triage.strip().lower()
        fix = fix.strip().lower()

        if triage == "yes" and fix == "yes":
            return "yes"
        elif triage == "yes" and fix in ["no", "maybe"]:
            return "maybe"  # Partial help - can identify but not fix
        elif triage == "maybe":
            return "maybe"
        else:  # triage == "no"
            return "no"

    async def analyze_multiple(
        self,
        tickets: List[Dict],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """
        Analyze multiple tickets for Diagnostics applicability.

        Args:
            tickets: List of ticket dictionaries with synthesis data
            progress_callback: Optional callback for progress updates

        Returns:
            List of tickets with diagnostics analysis added
        """
        self.logger.info(f"Starting Diagnostics analysis for {len(tickets)} tickets")
        analyzed_tickets = []

        for ticket in tickets:
            ticket_id = ticket.get("ticket_id", "unknown")

            # Skip tickets that failed synthesis
            if ticket.get("processing_status") == "failed":
                self.logger.warning(
                    f"Skipping ticket {ticket_id} - synthesis failed"
                )
                ticket["diagnostics_analysis_status"] = "skipped"
                ticket["diagnostics_analysis_error"] = "Synthesis failed"
                analyzed_tickets.append(ticket)

                if progress_callback:
                    progress_callback(ticket_id, ticket)

                continue

            # Analyze ticket
            try:
                analysis_result = await self.analyze_ticket(ticket)

                if analysis_result:
                    ticket["diagnostics_analysis"] = analysis_result
                    ticket["diagnostics_analysis_status"] = "success"
                else:
                    ticket["diagnostics_analysis_status"] = "failed"
                    ticket["diagnostics_analysis_error"] = "Failed to parse LLM response"

                analyzed_tickets.append(ticket)

                if progress_callback:
                    progress_callback(ticket_id, ticket)

            except Exception as e:
                self.logger.error(f"Failed to analyze ticket {ticket_id}: {e}")
                ticket["diagnostics_analysis_status"] = "failed"
                ticket["diagnostics_analysis_error"] = str(e)
                analyzed_tickets.append(ticket)

                if progress_callback:
                    progress_callback(ticket_id, ticket)

        self.logger.info(
            f"Completed Diagnostics analysis: "
            f"{len([t for t in analyzed_tickets if t.get('diagnostics_analysis_status') == 'success'])} succeeded, "
            f"{len([t for t in analyzed_tickets if t.get('diagnostics_analysis_status') == 'failed'])} failed"
        )

        return analyzed_tickets
