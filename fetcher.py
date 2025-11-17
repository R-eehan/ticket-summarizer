"""
Zendesk API client for fetching ticket data and comments.
Implements rate limiting, retry logic, and comprehensive error handling.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
import aiohttp
from aiohttp import BasicAuth

import config
import utils


class ZendeskFetcher:
    """
    Async Zendesk API client with rate limiting and retry logic.
    """

    def __init__(self):
        """Initialize Zendesk fetcher with configuration."""
        self.logger = logging.getLogger("ticket_summarizer.fetcher")
        self.base_url = config.ZENDESK_BASE_URL
        self.auth = BasicAuth(
            login=f"{config.ZENDESK_EMAIL}/token",
            password=config.ZENDESK_API_KEY
        )
        self.timeout = aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT_SECONDS)
        self.semaphore = asyncio.Semaphore(config.ZENDESK_MAX_CONCURRENT)

    @utils.retry_on_failure()
    async def fetch_ticket(self, session: aiohttp.ClientSession, ticket_id: str) -> Dict:
        """
        Fetch a single ticket's metadata from Zendesk, including custom fields.

        Args:
            session: aiohttp client session
            ticket_id: Zendesk ticket ID

        Returns:
            Dictionary containing ticket data with custom fields

        Raises:
            TicketNotFoundError: If ticket doesn't exist
            ZendeskAPIError: If API call fails
        """
        async with self.semaphore:
            # Include custom fields in the API request
            url = f"{config.ZENDESK_TICKET_URL.format(ticket_id=ticket_id)}"
            self.logger.debug(f"Fetching ticket {ticket_id} with custom fields from {url}")

            try:
                async with session.get(url, auth=self.auth, timeout=self.timeout) as response:
                    if response.status == 404:
                        raise utils.TicketNotFoundError(f"Ticket {ticket_id} not found")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise utils.ZendeskAPIError(
                            f"Failed to fetch ticket {ticket_id}: "
                            f"HTTP {response.status} - {error_text}"
                        )

                    data = await response.json()
                    self.logger.debug(f"Successfully fetched ticket {ticket_id}")
                    return data.get('ticket', {})

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                raise utils.ZendeskAPIError(f"Network error fetching ticket {ticket_id}: {e}")

    @utils.retry_on_failure()
    async def fetch_comments(self, session: aiohttp.ClientSession, ticket_id: str) -> List[Dict]:
        """
        Fetch all comments for a ticket from Zendesk.
        Handles pagination to retrieve all comments.

        Args:
            session: aiohttp client session
            ticket_id: Zendesk ticket ID

        Returns:
            List of comment dictionaries

        Raises:
            ZendeskAPIError: If API call fails
        """
        async with self.semaphore:
            url = config.ZENDESK_COMMENTS_URL.format(ticket_id=ticket_id)
            self.logger.debug(f"Fetching comments for ticket {ticket_id}")

            all_comments = []

            try:
                while url:
                    async with session.get(url, auth=self.auth, timeout=self.timeout) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise utils.ZendeskAPIError(
                                f"Failed to fetch comments for ticket {ticket_id}: "
                                f"HTTP {response.status} - {error_text}"
                            )

                        data = await response.json()
                        comments = data.get('comments', [])
                        all_comments.extend(comments)

                        # Check for pagination
                        url = data.get('next_page')

                self.logger.debug(
                    f"Successfully fetched {len(all_comments)} comments for ticket {ticket_id}"
                )
                return all_comments

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                raise utils.ZendeskAPIError(
                    f"Network error fetching comments for ticket {ticket_id}: {e}"
                )

    async def fetch_ticket_complete(
        self,
        session: aiohttp.ClientSession,
        ticket_id: str,
        serial_no: Optional[int] = None
    ) -> Dict:
        """
        Fetch complete ticket data including metadata and all comments.

        Args:
            session: aiohttp client session
            ticket_id: Zendesk ticket ID
            serial_no: Optional serial number from CSV

        Returns:
            Dictionary containing complete ticket data with comments
        """
        try:
            # Fetch ticket and comments in parallel
            ticket_data, comments_data = await asyncio.gather(
                self.fetch_ticket(session, ticket_id),
                self.fetch_comments(session, ticket_id),
                return_exceptions=True
            )

            # Handle exceptions from parallel fetch
            if isinstance(ticket_data, Exception):
                raise ticket_data
            if isinstance(comments_data, Exception):
                raise comments_data

            # Parse custom fields
            custom_fields_data = self._parse_custom_fields(ticket_data)

            # Process and format the data
            processed_ticket = {
                "ticket_id": ticket_id,
                "serial_no": serial_no,
                "subject": ticket_data.get('subject', ''),
                "description": ticket_data.get('description', ''),
                "url": f"https://{config.ZENDESK_SUBDOMAIN}.zendesk.com/agent/tickets/{ticket_id}",
                "status": ticket_data.get('status', 'unknown'),
                "created_at": utils.convert_to_ist(ticket_data.get('created_at', '')),
                "updated_at": utils.convert_to_ist(ticket_data.get('updated_at', '')),
                "comments_count": len(comments_data),
                "custom_fields": custom_fields_data,
                "comments": [],
                "processing_status": "success"
            }

            # Process comments
            for comment in comments_data:
                processed_comment = {
                    "id": str(comment.get('id', '')),
                    "author_id": str(comment.get('author_id', '')),
                    "author_name": self._get_author_name(comment),
                    "created_at": utils.convert_to_ist(comment.get('created_at', '')),
                    "body": comment.get('body', ''),
                    "public": comment.get('public', True)
                }
                processed_ticket["comments"].append(processed_comment)

            self.logger.info(f"Successfully fetched complete data for ticket {ticket_id}")
            return processed_ticket

        except utils.TicketNotFoundError as e:
            self.logger.error(f"Ticket {ticket_id} not found: {e}")
            return {
                "ticket_id": ticket_id,
                "serial_no": serial_no,
                "processing_status": "failed",
                "error": str(e),
                "error_type": "TicketNotFoundError"
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch ticket {ticket_id}: {e}")
            return {
                "ticket_id": ticket_id,
                "serial_no": serial_no,
                "processing_status": "failed",
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _get_author_name(self, comment: Dict) -> str:
        """
        Extract author name from comment data.

        Args:
            comment: Comment dictionary

        Returns:
            Author name string
        """
        # Try via field if available, otherwise use author_id
        via = comment.get('via', {})
        if via:
            source = via.get('source', {})
            from_data = source.get('from', {})
            name = from_data.get('name', '')
            if name:
                return name

        # Fallback to author_id
        return f"User {comment.get('author_id', 'Unknown')}"

    def _parse_custom_fields(self, ticket_data: Dict) -> Dict:
        """
        Parse and extract custom fields from ticket data.

        Args:
            ticket_data: Raw ticket data from Zendesk API

        Returns:
            Dictionary with parsed custom field values including escalation data
        """
        custom_fields_data = {}
        custom_fields = ticket_data.get('custom_fields', [])

        # Initialize variables for escalation fields (Phase 5)
        cross_team_value = None
        jira_ticket_url = None

        # Extract all relevant custom fields
        for field in custom_fields:
            field_id = field.get('id')
            field_value = field.get('value', '')

            # "Was Diagnostic Panel used?" field (existing)
            if field_id == config.DIAGNOSTICS_CUSTOM_FIELD_ID:
                normalized_value = utils.normalize_diagnostics_field(field_value)
                custom_fields_data['was_diagnostics_used'] = normalized_value
                self.logger.debug(
                    f"Parsed diagnostics custom field: raw='{field_value}', "
                    f"normalized='{normalized_value}'"
                )

            # Cross Team field (Phase 5)
            elif field_id == config.CROSS_TEAM_FIELD_ID:
                cross_team_value = field_value
                self.logger.debug(f"Parsed Cross Team field: raw='{field_value}'")

            # JIRA Ticket field (Phase 5)
            elif field_id == config.JIRA_TICKET_FIELD_ID:
                jira_ticket_url = field_value
                self.logger.debug(f"Parsed JIRA Ticket field: url='{field_value}'")

        # Default diagnostics field if not found
        if 'was_diagnostics_used' not in custom_fields_data:
            custom_fields_data['was_diagnostics_used'] = 'unknown'
            self.logger.debug("Diagnostics custom field not found, defaulting to 'unknown'")

        # Determine escalation status (Phase 5)
        escalation_data = utils.determine_escalation_status(cross_team_value, jira_ticket_url)
        custom_fields_data['escalation'] = escalation_data

        self.logger.debug(
            f"Escalation status: is_escalated={escalation_data['is_escalated']}, "
            f"cross_team={escalation_data['cross_team_status']}, "
            f"jira_id={escalation_data['jira_ticket_id']}"
        )

        return custom_fields_data

    async def fetch_multiple_tickets(
        self,
        ticket_ids: List[tuple],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """
        Fetch multiple tickets in parallel with rate limiting.

        Args:
            ticket_ids: List of tuples (serial_no, ticket_id)
            progress_callback: Optional callback function for progress updates

        Returns:
            List of ticket dictionaries (both successful and failed)
        """
        self.logger.info(f"Starting to fetch {len(ticket_ids)} tickets")
        results = []

        async with aiohttp.ClientSession() as session:
            tasks = []

            for serial_no, ticket_id in ticket_ids:
                task = self._fetch_with_progress(
                    session,
                    ticket_id,
                    serial_no,
                    progress_callback
                )
                tasks.append(task)

            # Execute all tasks and gather results
            results = await asyncio.gather(*tasks, return_exceptions=False)

        self.logger.info(f"Completed fetching {len(results)} tickets")
        return results

    async def _fetch_with_progress(
        self,
        session: aiohttp.ClientSession,
        ticket_id: str,
        serial_no: int,
        progress_callback: Optional[Callable]
    ) -> Dict:
        """
        Fetch a ticket and call progress callback.

        Args:
            session: aiohttp client session
            ticket_id: Zendesk ticket ID
            serial_no: Serial number from CSV
            progress_callback: Callback function for progress updates

        Returns:
            Ticket dictionary
        """
        result = await self.fetch_ticket_complete(session, ticket_id, serial_no)

        # Call progress callback if provided
        if progress_callback:
            progress_callback(ticket_id, result)

        return result
