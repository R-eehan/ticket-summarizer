"""
POD Categorization module for Zendesk Ticket Summarizer (Phase 2).
Categorizes synthesized tickets into PODs using Gemini LLM with confidence scoring.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Callable
import google.generativeai as genai

import config
import utils


class TicketCategorizer:
    """
    Async ticket categorizer using Gemini LLM for POD assignment.

    This is Phase 3 of the ticket processing workflow. It takes the synthesis
    output from Phase 2 and determines which POD (Product Organizational Domain)
    the ticket belongs to, along with reasoning and confidence scoring.

    Key Features:
    - LLM-based categorization using synthesis context
    - Binary confidence scoring (confident/not confident)
    - Alternative POD suggestions for ambiguous cases
    - Rate limiting and retry logic
    - Comprehensive validation and error handling
    """

    def __init__(self):
        """
        Initialize the categorizer with Gemini model and rate limiting.

        Sets up:
        - Logger for tracking categorization operations
        - Gemini API configuration
        - Rate limiting semaphore (5 concurrent max)
        - Model initialization
        """
        self.logger = logging.getLogger("ticket_summarizer.categorizer")

        # Configure Gemini API with the provided API key
        genai.configure(api_key=config.GEMINI_API_KEY)

        # Initialize Gemini model for categorization
        # Uses same model as synthesis for consistency
        self.model = genai.GenerativeModel(config.GEMINI_MODEL)

        # Rate limiting: Max 5 concurrent Gemini API calls
        # Prevents hitting API rate limits while maintaining good throughput
        self.semaphore = asyncio.Semaphore(config.GEMINI_MAX_CONCURRENT)

        self.logger.info(f"Initialized Categorizer with model: {config.GEMINI_MODEL}")

    def format_categorization_prompt(self, ticket_data: Dict) -> str:
        """
        Format ticket synthesis data into categorization prompt for LLM.

        Extracts synthesis fields (issue, root cause, summary, resolution) and
        embeds them into the categorization prompt template defined in config.

        Args:
            ticket_data: Dictionary containing ticket with synthesis

        Returns:
            Formatted prompt string ready for LLM

        Example:
            >>> ticket = {
            ...     "subject": "Smart Tip not displaying",
            ...     "synthesis": {
            ...         "issue_reported": "Smart tip not showing in preview",
            ...         "root_cause": "CSS selector missing",
            ...         "summary": "Customer reported...",
            ...         "resolution": "Added CSS selector"
            ...     }
            ... }
            >>> prompt = categorizer.format_categorization_prompt(ticket)
        """
        # Extract subject and synthesis fields
        subject = ticket_data.get('subject', 'No subject')
        synthesis = ticket_data.get('synthesis', {})

        issue_reported = synthesis.get('issue_reported', 'Not available')
        root_cause = synthesis.get('root_cause', 'Not available')
        summary = synthesis.get('summary', 'Not available')
        resolution = synthesis.get('resolution', 'Not available')

        # Fill in the categorization prompt template with synthesis data
        # Template contains POD definitions and categorization instructions
        prompt = config.CATEGORIZATION_PROMPT_TEMPLATE.format(
            subject=subject,
            issue_reported=issue_reported,
            root_cause=root_cause,
            summary=summary,
            resolution=resolution
        )

        return prompt

    def parse_categorization_response(self, response_text: str) -> Dict:
        """
        Parse LLM response into structured categorization data.

        Extracts fields using regex patterns matching the expected output format.
        Validates POD and confidence values against predefined lists.
        Handles missing or malformed fields gracefully with fallbacks.

        Args:
            response_text: Raw text response from Gemini LLM

        Returns:
            Dictionary with categorization fields:
            {
                "primary_pod": str,
                "reasoning": str,
                "confidence": str,
                "confidence_reason": str,
                "alternative_pods": list,
                "alternative_reasoning": str or null,
                "metadata": {
                    "keywords_matched": list,
                    "decision_factors": list
                }
            }
        """
        # Initialize categorization structure with default values
        categorization = {
            "primary_pod": "",
            "reasoning": "",
            "confidence": "not confident",  # Default to not confident for safety
            "confidence_reason": "",
            "alternative_pods": [],
            "alternative_reasoning": None,
            "metadata": {
                "keywords_matched": [],
                "decision_factors": []
            }
        }

        try:
            # Extract Primary POD
            # Pattern: **Primary POD:**\n[POD name]
            pod_match = re.search(
                r'\*\*Primary POD:\*\*\s*\n(.*?)(?=\n\*\*|\Z)',
                response_text,
                re.DOTALL
            )
            if pod_match:
                primary_pod = pod_match.group(1).strip()
                # Validate against known PODs
                if utils.validate_pod(primary_pod):
                    categorization["primary_pod"] = primary_pod
                else:
                    self.logger.warning(
                        f"Invalid POD '{primary_pod}' - not in VALID_PODS list. "
                        f"Marking as empty."
                    )

            # Extract Reasoning
            # Pattern: **Reasoning:**\n[2-3 sentences]
            reasoning_match = re.search(
                r'\*\*Reasoning:\*\*\s*\n(.*?)(?=\n\*\*|\Z)',
                response_text,
                re.DOTALL
            )
            if reasoning_match:
                categorization["reasoning"] = reasoning_match.group(1).strip()

            # Extract Confidence
            # Pattern: **Confidence:**\n[confident or not confident]
            confidence_match = re.search(
                r'\*\*Confidence:\*\*\s*\n(.*?)(?=\n\*\*|\Z)',
                response_text,
                re.DOTALL
            )
            if confidence_match:
                confidence = confidence_match.group(1).strip()
                # Validate against known confidence levels
                if utils.validate_confidence(confidence):
                    categorization["confidence"] = confidence
                else:
                    self.logger.warning(
                        f"Invalid confidence '{confidence}' - not in CONFIDENCE_LEVELS. "
                        f"Defaulting to 'not confident'."
                    )

            # Extract Confidence Reason
            # Pattern: **Confidence Reason:**\n[explanation]
            confidence_reason_match = re.search(
                r'\*\*Confidence Reason:\*\*\s*\n(.*?)(?=\n\*\*|\Z)',
                response_text,
                re.DOTALL
            )
            if confidence_reason_match:
                categorization["confidence_reason"] = confidence_reason_match.group(1).strip()

            # Extract Alternative PODs
            # Pattern: **Alternative PODs:**\n[POD1, POD2 or None]
            alt_pods_match = re.search(
                r'\*\*Alternative PODs:\*\*\s*\n(.*?)(?=\n\*\*|\Z)',
                response_text,
                re.DOTALL
            )
            if alt_pods_match:
                alt_pods_text = alt_pods_match.group(1).strip()
                if alt_pods_text.lower() != "none":
                    # Split by comma and validate each POD
                    alt_pods = [p.strip() for p in alt_pods_text.split(',')]
                    validated_alt_pods = [p for p in alt_pods if utils.validate_pod(p)]
                    categorization["alternative_pods"] = validated_alt_pods
                # else: keep as empty list []

            # Extract Alternative Reasoning
            # Pattern: **Alternative Reasoning:**\n[explanation or N/A]
            alt_reasoning_match = re.search(
                r'\*\*Alternative Reasoning:\*\*\s*\n(.*?)(?=\Z)',
                response_text,
                re.DOTALL
            )
            if alt_reasoning_match:
                alt_reasoning = alt_reasoning_match.group(1).strip()
                if alt_reasoning.upper() != "N/A":
                    categorization["alternative_reasoning"] = alt_reasoning
                # else: keep as null

            # Log parsing warnings if critical fields are missing
            if not categorization["primary_pod"]:
                self.logger.warning("Failed to parse Primary POD from LLM response")
            if not categorization["reasoning"]:
                self.logger.warning("Failed to parse Reasoning from LLM response")
            if not categorization["confidence_reason"]:
                self.logger.warning("Failed to parse Confidence Reason from LLM response")

        except Exception as e:
            self.logger.error(f"Error parsing categorization response: {e}")
            self.logger.debug(f"Raw response: {response_text[:500]}...")

        return categorization

    @utils.retry_on_failure()
    async def categorize_ticket(self, ticket_data: Dict) -> Dict:
        """
        Categorize a single synthesized ticket into a primary POD.

        This is the core categorization method. It:
        1. Extracts synthesis from ticket data
        2. Formats categorization prompt with POD definitions
        3. Calls Gemini LLM for categorization decision
        4. Parses and validates the response
        5. Returns ticket data with categorization added

        Rate limiting and retry logic are applied via decorators and semaphores.

        Args:
            ticket_data: Dictionary containing ticket with completed synthesis

        Returns:
            Ticket dictionary with categorization field added

        Raises:
            GeminiAPIError: If LLM categorization fails after retries

        Example:
            >>> ticket = {
            ...     "ticket_id": "87239",
            ...     "synthesis": {...}
            ... }
            >>> result = await categorizer.categorize_ticket(ticket)
            >>> result["categorization"]["primary_pod"]
            'Guidance'
        """
        ticket_id = ticket_data.get('ticket_id', 'unknown')

        # Rate limiting: Ensure we don't exceed Gemini API limits
        # Only 5 categorizations can run concurrently
        async with self.semaphore:
            self.logger.debug(f"Categorizing ticket {ticket_id}")

            try:
                # Step 1: Extract synthesis data for categorization
                synthesis = ticket_data.get('synthesis', {})

                # Skip categorization if synthesis is missing or incomplete
                if not synthesis or not synthesis.get('summary'):
                    raise utils.GeminiAPIError(
                        f"Ticket {ticket_id} missing synthesis data - cannot categorize"
                    )

                # Step 2: Format categorization prompt with synthesis context
                # Prompt includes all POD definitions and categorization logic
                prompt = self.format_categorization_prompt(ticket_data)

                # Step 3: Call Gemini LLM for categorization
                # Run synchronous API call in executor to avoid blocking
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(prompt)
                )

                # Validate response
                if not response or not response.text:
                    raise utils.GeminiAPIError(
                        f"Empty response from Gemini for ticket {ticket_id}"
                    )

                response_text = response.text
                self.logger.debug(f"Received categorization response for ticket {ticket_id}")

                # Step 4: Parse LLM response into structured categorization data
                categorization = self.parse_categorization_response(response_text)

                # Step 5: Add categorization to ticket data
                result = ticket_data.copy()
                result["categorization"] = categorization

                self.logger.info(
                    f"Successfully categorized ticket {ticket_id} as "
                    f"{categorization['primary_pod']} "
                    f"(confidence: {categorization['confidence']})"
                )

                # Add delay to respect free tier rate limits
                if config.GEMINI_REQUEST_DELAY > 0:
                    await asyncio.sleep(config.GEMINI_REQUEST_DELAY)

                return result

            except Exception as e:
                error_msg = f"Failed to categorize ticket {ticket_id}: {e}"
                self.logger.error(error_msg)
                raise utils.GeminiAPIError(error_msg)

    async def categorize_multiple(
        self,
        tickets: List[Dict],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """
        Categorize multiple tickets in parallel with rate limiting and progress tracking.

        Processes tickets in batches respecting the concurrency limit (5 concurrent).
        Only categorizes tickets that have successful synthesis - skips failed ones.
        Handles individual failures gracefully without stopping the entire batch.

        Args:
            tickets: List of ticket dictionaries with synthesis
            progress_callback: Optional callback function(ticket_id, result, success)
                              Called after each ticket is categorized

        Returns:
            List of ticket dictionaries with categorization added

        Example:
            >>> tickets = [{"ticket_id": "1", "synthesis": {...}}, ...]
            >>> def callback(tid, result, success):
            ...     print(f"Categorized {tid}: {success}")
            >>> results = await categorizer.categorize_multiple(tickets, callback)
        """
        self.logger.info(f"Starting categorization of {len(tickets)} tickets")

        # Filter: Only categorize tickets with successful synthesis
        # Tickets that failed fetch or synthesis are skipped
        tickets_to_categorize = [
            t for t in tickets
            if t.get('processing_status') == 'success' and 'synthesis' in t
        ]

        self.logger.info(
            f"Categorizing {len(tickets_to_categorize)} tickets "
            f"(skipped {len(tickets) - len(tickets_to_categorize)} without synthesis)"
        )

        # Create async tasks for parallel categorization
        # Each task will be rate-limited by the semaphore
        tasks = []
        for ticket in tickets_to_categorize:
            task = self._categorize_with_progress(ticket, progress_callback)
            tasks.append(task)

        # Execute all categorization tasks in parallel
        # return_exceptions=True ensures one failure doesn't stop others
        categorized_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        results = []
        for i, result in enumerate(categorized_results):
            if isinstance(result, Exception):
                # Categorization failed for this ticket
                ticket = tickets_to_categorize[i]
                ticket_id = ticket.get('ticket_id', 'unknown')
                self.logger.error(f"Categorization failed for ticket {ticket_id}: {result}")

                # Mark as categorization failed, preserve synthesis
                ticket_copy = ticket.copy()
                ticket_copy["categorization_status"] = "failed"
                ticket_copy["categorization_error"] = str(result)
                results.append(ticket_copy)
            else:
                # Categorization succeeded
                results.append(result)

        # Add back tickets that were skipped (no synthesis)
        skipped_tickets = [
            t for t in tickets
            if t.get('processing_status') != 'success' or 'synthesis' not in t
        ]
        results.extend(skipped_tickets)

        # Log summary statistics
        successful = sum(1 for r in results if "categorization" in r)
        failed = sum(1 for r in results if "categorization_status" == "failed")
        self.logger.info(
            f"Categorization complete: {successful} succeeded, "
            f"{failed} failed, {len(skipped_tickets)} skipped"
        )

        return results

    async def _categorize_with_progress(
        self,
        ticket_data: Dict,
        progress_callback: Optional[Callable]
    ) -> Dict:
        """
        Categorize a ticket and call progress callback.

        Helper method that wraps categorize_ticket() with progress callback support.
        This allows the main workflow to track progress in real-time.

        Args:
            ticket_data: Ticket dictionary with synthesis
            progress_callback: Callback function to report progress

        Returns:
            Categorized ticket dictionary

        Raises:
            Propagates exceptions from categorize_ticket()
        """
        ticket_id = ticket_data.get('ticket_id', 'unknown')

        try:
            # Attempt categorization
            result = await self.categorize_ticket(ticket_data)

            # Call progress callback with success=True
            if progress_callback:
                progress_callback(ticket_id, result, success=True)

            return result

        except Exception as e:
            # Call progress callback with success=False
            if progress_callback:
                progress_callback(ticket_id, ticket_data, success=False)

            # Re-raise exception to be handled by categorize_multiple
            raise e
