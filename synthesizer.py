"""
LLM client for synthesizing ticket summaries.
Supports multiple LLM providers (Gemini, Azure OpenAI) via factory pattern.

Phase 3c: Multi-Model Support
Phase 4: Added OpenTelemetry tracing (Tier 2 - Business Logic Spans)
Implements rate limiting, retry logic, and response parsing.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Callable
from opentelemetry import trace

import config
import utils
from llm_provider import LLMProviderFactory


class GeminiSynthesizer:
    """
    Async LLM client for ticket synthesis with rate limiting.

    Phase 3c: Renamed from "GeminiSynthesizer" but kept class name for backward compatibility.
    Now supports both Gemini and Azure OpenAI via LLMProviderFactory.
    """

    def __init__(self, model_provider: str = "gemini"):
        """
        Initialize synthesizer with specified LLM provider.

        Args:
            model_provider: LLM provider name ("gemini" or "azure")
                           Defaults to "gemini" for backward compatibility

        Raises:
            ValueError: If provider credentials are missing or invalid
        """
        self.logger = logging.getLogger("ticket_summarizer.synthesizer")
        self.model_provider = model_provider

        # Initialize LLM provider using factory pattern
        self.logger.info(f"Initializing synthesizer with model provider: {model_provider}")
        self.llm_client = LLMProviderFactory.get_provider(model_provider)

        # Rate limiting
        self.semaphore = asyncio.Semaphore(config.GEMINI_MAX_CONCURRENT)

        # Initialize OpenTelemetry tracer (Phase 4 - Tier 2)
        self.tracer = trace.get_tracer(__name__)

        self.logger.info(f"Synthesizer initialized with {model_provider} provider")

    def format_prompt(self, ticket_data: Dict) -> str:
        """
        Format ticket data into LLM prompt.

        Args:
            ticket_data: Dictionary containing ticket information

        Returns:
            Formatted prompt string
        """
        subject = ticket_data.get('subject', 'No subject')
        description = utils.strip_html(ticket_data.get('description', 'No description'))
        comments = ticket_data.get('comments', [])

        # Format comment thread
        comment_thread = utils.format_comment_thread(comments)

        # Fill in the prompt template
        prompt = config.LLM_PROMPT_TEMPLATE.format(
            subject=subject,
            description=description,
            all_comments=comment_thread
        )

        return prompt

    def parse_response(self, response_text: str) -> Dict:
        """
        Parse LLM response into structured synthesis data.

        Args:
            response_text: Raw response text from LLM

        Returns:
            Dictionary with parsed synthesis fields
        """
        # Initialize with empty values
        synthesis = {
            "issue_reported": "",
            "root_cause": "",
            "summary": "",
            "resolution": ""
        }

        try:
            # Extract each section using regex
            # Pattern: **Field Name:**\n[content]

            # Issue Reported
            issue_match = re.search(
                r'\*\*Issue Reported:\*\*\s*\n(.*?)(?=\n\*\*|\Z)',
                response_text,
                re.DOTALL
            )
            if issue_match:
                synthesis["issue_reported"] = issue_match.group(1).strip()

            # Root Cause
            root_cause_match = re.search(
                r'\*\*Root Cause:\*\*\s*\n(.*?)(?=\n\*\*|\Z)',
                response_text,
                re.DOTALL
            )
            if root_cause_match:
                synthesis["root_cause"] = root_cause_match.group(1).strip()

            # Summary
            summary_match = re.search(
                r'\*\*Summary:\*\*\s*\n(.*?)(?=\n\*\*|\Z)',
                response_text,
                re.DOTALL
            )
            if summary_match:
                synthesis["summary"] = summary_match.group(1).strip()

            # Resolution
            resolution_match = re.search(
                r'\*\*Resolution:\*\*\s*\n(.*?)(?=\Z)',
                response_text,
                re.DOTALL
            )
            if resolution_match:
                synthesis["resolution"] = resolution_match.group(1).strip()

            # Log if any field is missing
            missing_fields = [k for k, v in synthesis.items() if not v]
            if missing_fields:
                self.logger.warning(
                    f"Failed to parse some fields from LLM response: {missing_fields}"
                )

        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            self.logger.debug(f"Raw response: {response_text[:500]}...")

        return synthesis

    @utils.retry_on_failure()
    async def synthesize_ticket(self, ticket_data: Dict) -> Dict:
        """
        Synthesize a single ticket using Gemini LLM.

        Phase 4: Added OpenTelemetry parent span (Tier 2 - Business Logic)
        This creates a parent span that groups all LLM calls and HTTP operations
        for this ticket into a single trace.

        Args:
            ticket_data: Dictionary containing complete ticket information

        Returns:
            Dictionary with synthesis results

        Raises:
            GeminiAPIError: If API call fails
        """
        ticket_id = ticket_data.get('ticket_id', 'unknown')

        # Phase 4: Create parent span for entire synthesis operation
        with self.tracer.start_as_current_span(
            "ticket.synthesis",
            attributes={
                "ticket.id": str(ticket_id),
                "operation.type": "synthesis",
                "model.provider": self.model_provider,
            }
        ) as span:
            async with self.semaphore:
                self.logger.debug(f"Synthesizing ticket {ticket_id}")

                try:
                    # Format the prompt
                    prompt = self.format_prompt(ticket_data)

                    # Call LLM API (via provider abstraction, synchronous but wrapped in async)
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.llm_client.generate_content(prompt)
                    )

                    # Extract response text
                    if not response or not response.text:
                        raise utils.GeminiAPIError(f"Empty response from LLM for ticket {ticket_id}")

                    response_text = response.text
                    self.logger.debug(f"Received response for ticket {ticket_id}")

                    # Parse the response
                    synthesis = self.parse_response(response_text)

                    # Add span attributes for observability
                    span.set_attribute("synthesis.success", True)
                    span.set_attribute("response.length", len(response_text))

                    # Add to ticket data
                    result = ticket_data.copy()
                    result["synthesis"] = synthesis

                    self.logger.info(f"Successfully synthesized ticket {ticket_id}")

                    # Add delay to respect free tier rate limits
                    if config.GEMINI_REQUEST_DELAY > 0:
                        await asyncio.sleep(config.GEMINI_REQUEST_DELAY)

                    return result

                except Exception as e:
                    error_msg = f"Failed to synthesize ticket {ticket_id}: {e}"
                    self.logger.error(error_msg)

                    # Mark span as error
                    span.set_attribute("synthesis.success", False)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)

                    raise utils.GeminiAPIError(error_msg)

    async def synthesize_multiple(
        self,
        tickets: List[Dict],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """
        Synthesize multiple tickets in parallel with rate limiting.

        Args:
            tickets: List of ticket dictionaries (successfully fetched)
            progress_callback: Optional callback function for progress updates

        Returns:
            List of ticket dictionaries with synthesis results
        """
        self.logger.info(f"Starting to synthesize {len(tickets)} tickets")
        results = []

        # Filter out failed tickets (only synthesize successful fetches)
        tickets_to_synthesize = [
            t for t in tickets
            if t.get('processing_status') == 'success'
        ]

        self.logger.info(
            f"Synthesizing {len(tickets_to_synthesize)} successfully fetched tickets"
        )

        # Create tasks for parallel execution
        tasks = []
        for ticket in tickets_to_synthesize:
            task = self._synthesize_with_progress(ticket, progress_callback)
            tasks.append(task)

        # Execute all tasks and gather results
        synthesized_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(synthesized_results):
            if isinstance(result, Exception):
                # Synthesis failed
                ticket = tickets_to_synthesize[i]
                ticket_id = ticket.get('ticket_id', 'unknown')
                self.logger.error(f"Synthesis failed for ticket {ticket_id}: {result}")

                # Mark as failed
                ticket_copy = ticket.copy()
                ticket_copy["processing_status"] = "synthesis_failed"
                ticket_copy["synthesis_error"] = str(result)
                results.append(ticket_copy)
            else:
                # Synthesis succeeded
                results.append(result)

        # Add back tickets that were skipped (failed fetches)
        failed_fetches = [
            t for t in tickets
            if t.get('processing_status') != 'success'
        ]
        results.extend(failed_fetches)

        self.logger.info(f"Completed synthesis of {len(results)} tickets")
        return results

    async def _synthesize_with_progress(
        self,
        ticket_data: Dict,
        progress_callback: Optional[Callable]
    ) -> Dict:
        """
        Synthesize a ticket and call progress callback.

        Args:
            ticket_data: Dictionary containing ticket information
            progress_callback: Callback function for progress updates

        Returns:
            Ticket dictionary with synthesis
        """
        ticket_id = ticket_data.get('ticket_id', 'unknown')

        try:
            result = await self.synthesize_ticket(ticket_data)

            # Call progress callback if provided
            if progress_callback:
                progress_callback(ticket_id, result, success=True)

            return result

        except Exception as e:
            # Call progress callback with failure
            if progress_callback:
                progress_callback(ticket_id, ticket_data, success=False)

            raise e
