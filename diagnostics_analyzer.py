"""
Diagnostics Analysis Module for Zendesk Ticket Summarizer.

This module analyzes synthesized tickets to determine:
1. Was Diagnostics feature used? (by customer OR support team)
2. Could Diagnostics have helped? (to diagnose OR resolve the issue)

Phase 3c: Multi-Model Support
Phase 4: Added OpenTelemetry tracing (Tier 2 - Business Logic Spans)
Uses LLM provider abstraction (Gemini or Azure OpenAI) with Whatfix Diagnostics product knowledge.
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Callable
from opentelemetry import trace

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

        # Initialize OpenTelemetry tracer (Phase 4 - Tier 2)
        self.tracer = trace.get_tracer(__name__)

        self.logger.info(f"Diagnostics analyzer initialized with {model_provider} provider")

    async def analyze_ticket(self, ticket_data: Dict) -> Dict:
        """
        Analyze a single ticket for Diagnostics applicability.

        Phase 4: Added OpenTelemetry parent span (Tier 2 - Business Logic)
        This creates a parent span that groups all LLM calls for diagnostics analysis.

        Args:
            ticket_data: Dictionary containing ticket synthesis and custom fields

        Returns:
            Dictionary with diagnostics analysis results

        Raises:
            GeminiAPIError: If LLM call fails
        """
        ticket_id = ticket_data.get("ticket_id", "unknown")

        # Phase 4: Create parent span for entire diagnostics analysis operation
        with self.tracer.start_as_current_span(
            "ticket.diagnostics_analysis",
            attributes={
                "ticket.id": str(ticket_id),
                "operation.type": "diagnostics_analysis",
                "model.provider": self.model_provider,
            }
        ) as span:
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

                    # Format the prompt with ticket data
                    prompt = self._format_diagnostics_prompt(
                        subject=subject,
                        issue_reported=issue_reported,
                        root_cause=root_cause,
                        summary=summary,
                        resolution=resolution,
                        custom_field_value=custom_field_value
                    )

                    # Call LLM API (via provider abstraction)
                    self.logger.debug(f"Calling LLM API for ticket {ticket_id}")
                    response = await asyncio.to_thread(
                        self.llm_client.generate_content, prompt
                    )

                    # Parse response
                    analysis_result = self._parse_diagnostics_response(response.text, ticket_id)

                    # Add custom field value to the result
                    if analysis_result:
                        analysis_result["was_diagnostics_used"]["custom_field_value"] = custom_field_value
                        analysis_result["metadata"]["analysis_timestamp"] = utils.get_current_ist_timestamp()

                    # Add span attributes for observability
                    span.set_attribute("diagnostics_analysis.success", True)
                    span.set_attribute("was_diagnostics_used", analysis_result.get("was_diagnostics_used", {}).get("llm_assessment", "unknown"))
                    span.set_attribute("could_diagnostics_help", analysis_result.get("could_diagnostics_help", {}).get("assessment", "unknown"))
                    span.set_attribute("response.length", len(response.text))

                    self.logger.info(f"Successfully analyzed ticket {ticket_id}")

                    # Add rate limiting delay
                    await asyncio.sleep(self.request_delay)

                    return analysis_result

                except Exception as e:
                    self.logger.error(f"Failed to analyze ticket {ticket_id}: {e}")

                    # Mark span as error
                    span.set_attribute("diagnostics_analysis.success", False)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)

                    raise utils.GeminiAPIError(f"Diagnostics analysis failed for ticket {ticket_id}: {e}")

    def _format_diagnostics_prompt(
        self,
        subject: str,
        issue_reported: str,
        root_cause: str,
        summary: str,
        resolution: str,
        custom_field_value: str
    ) -> str:
        """
        Format the Diagnostics analysis prompt with ticket data.

        Args:
            subject: Ticket subject
            issue_reported: Issue reported from synthesis
            root_cause: Root cause from synthesis
            summary: Summary from synthesis
            resolution: Resolution from synthesis
            custom_field_value: Normalized custom field value

        Returns:
            Formatted prompt string
        """
        return config.DIAGNOSTICS_ANALYSIS_PROMPT.format(
            subject=subject,
            issue_reported=issue_reported,
            root_cause=root_cause,
            summary=summary,
            resolution=resolution,
            custom_field_value=custom_field_value
        )

    def _parse_diagnostics_response(self, response_text: str, ticket_id: str) -> Optional[Dict]:
        """
        Parse LLM response and extract diagnostics analysis in JSON format.

        The LLM is expected to return a JSON structure with:
        - was_diagnostics_used: {llm_assessment, confidence, reasoning}
        - could_diagnostics_help: {assessment, confidence, reasoning, diagnostics_capability_matched, limitation_notes}
        - metadata: {ticket_type}

        Args:
            response_text: Raw response from Gemini
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

    def _validate_analysis_structure(self, analysis_data: Dict, ticket_id: str) -> bool:
        """
        Validate the structure and values of the diagnostics analysis.

        Checks:
        - Required fields exist
        - Enum values are valid (yes/no/unknown, yes/no/maybe, confident/not confident)
        - Reasoning fields are not empty

        Args:
            analysis_data: Parsed analysis dictionary
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

            # Validate could_diagnostics_help
            could_help = analysis_data["could_diagnostics_help"]
            assessment = could_help.get("assessment", "").strip().lower()

            if not utils.validate_diagnostics_assessment(assessment):
                self.logger.warning(
                    f"Invalid assessment '{assessment}' for ticket {ticket_id}. "
                    f"Expected: yes, no, or maybe"
                )
                return False

            if not utils.validate_confidence(could_help.get("confidence", "")):
                self.logger.warning(
                    f"Invalid confidence for could_diagnostics_help in ticket {ticket_id}"
                )
                return False

            if not could_help.get("reasoning"):
                self.logger.warning(
                    f"Empty reasoning for could_diagnostics_help in ticket {ticket_id}"
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
