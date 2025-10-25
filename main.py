#!/usr/bin/env python3
"""
Zendesk Ticket Summarizer - Main Entry Point

A terminal-based application that fetches Zendesk tickets and uses
Google Gemini 2.5 Pro to generate comprehensive summaries.

Usage:
    python main.py <input_csv_path>
"""

import sys
import csv
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table

import config
import utils
from fetcher import ZendeskFetcher
from synthesizer import GeminiSynthesizer
from categorizer import TicketCategorizer


class TicketSummarizer:
    """
    Main orchestrator for ticket summarization workflow.
    """

    def __init__(self):
        """
        Initialize the summarizer with logger and components.

        Sets up:
        - Logger for tracking all operations
        - Console for rich terminal output
        - Fetcher for Zendesk API calls (Phase 1)
        - Synthesizer for LLM summarization (Phase 2)
        - Categorizer for POD assignment (Phase 3) - NEW in Phase 2
        - Statistics tracking for all three phases
        """
        self.logger = utils.setup_logger("ticket_summarizer")
        self.console = Console()
        self.fetcher = ZendeskFetcher()
        self.synthesizer = GeminiSynthesizer()
        self.categorizer = TicketCategorizer()  # Phase 2: POD categorization

        # Statistics tracking for all phases
        self.stats = {
            "total_tickets": 0,
            "fetch_success": 0,
            "fetch_failed": 0,
            "synthesis_success": 0,
            "synthesis_failed": 0,
            "categorization_success": 0,  # Phase 2: New stat
            "categorization_failed": 0,  # Phase 2: New stat
            "confident_count": 0,  # Phase 2: Confidence breakdown
            "not_confident_count": 0,  # Phase 2: Confidence breakdown
            "pod_distribution": {},  # Phase 2: POD counts
            "start_time": None,
            "end_time": None
        }

    def load_csv(self, csv_path: str) -> List[Tuple[int, str]]:
        """
        Load ticket IDs from CSV file with auto-detection of format.

        Supports two CSV formats:
        1. Format 1: "Serial No, Ticket ID" (Phase 1 format)
        2. Format 2: "Zendesk Tickets ID" (Phase 2 format - auto-generates serial numbers)

        Args:
            csv_path: Path to input CSV file

        Returns:
            List of tuples (serial_no, ticket_id)

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV format is invalid or unrecognized
        """
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        ticket_ids = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Auto-detect CSV format based on headers
            headers = reader.fieldnames

            # Format 1: "Serial No, Ticket ID"
            if 'Serial No' in headers and 'Ticket ID' in headers:
                self.logger.info("Detected CSV Format 1: Serial No, Ticket ID")
                for row in reader:
                    serial_no = int(row['Serial No'])
                    ticket_id = str(row['Ticket ID']).strip()
                    ticket_ids.append((serial_no, ticket_id))

            # Format 2: "Zendesk Tickets ID" (auto-generate serial numbers)
            elif 'Zendesk Tickets ID' in headers:
                self.logger.info("Detected CSV Format 2: Zendesk Tickets ID (auto-generating serial numbers)")
                serial_no = 1
                for row in reader:
                    ticket_id = str(row['Zendesk Tickets ID']).strip()
                    ticket_ids.append((serial_no, ticket_id))
                    serial_no += 1

            # Unsupported format
            else:
                raise ValueError(
                    f"Unrecognized CSV format. Expected columns:\n"
                    f"  Format 1: 'Serial No, Ticket ID'\n"
                    f"  Format 2: 'Zendesk Tickets ID'\n"
                    f"Found: {headers}"
                )

        self.logger.info(f"Loaded {len(ticket_ids)} ticket IDs from {csv_path}")
        return ticket_ids

    async def fetch_phase(self, ticket_ids: List[Tuple[int, str]]) -> List[dict]:
        """
        Phase 1: Fetch all tickets from Zendesk.

        Args:
            ticket_ids: List of tuples (serial_no, ticket_id)

        Returns:
            List of fetched ticket dictionaries
        """
        self.console.print("\n[bold cyan][PHASE 1] Fetching Ticket Data from Zendesk[/bold cyan]")

        fetched_tickets = []
        fetch_errors = []

        # Progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(
                "[cyan]Fetching tickets...",
                total=len(ticket_ids)
            )

            def progress_callback(ticket_id: str, result: dict):
                """Callback for progress updates."""
                if result.get('processing_status') == 'success':
                    self.stats['fetch_success'] += 1
                else:
                    self.stats['fetch_failed'] += 1
                    fetch_errors.append(result)

                progress.update(task, advance=1)

            # Fetch all tickets
            fetched_tickets = await self.fetcher.fetch_multiple_tickets(
                ticket_ids,
                progress_callback
            )

        # Display results
        self.console.print(
            f"[green]✓[/green] Successfully fetched: {self.stats['fetch_success']} tickets"
        )
        if self.stats['fetch_failed'] > 0:
            failed_ids = [e['ticket_id'] for e in fetch_errors]
            self.console.print(
                f"[red]✗[/red] Failed: {self.stats['fetch_failed']} tickets "
                f"(IDs: {', '.join(failed_ids)})"
            )

        return fetched_tickets

    async def synthesis_phase(self, tickets: List[dict]) -> List[dict]:
        """
        Phase 2: Synthesize tickets using Gemini LLM.

        Args:
            tickets: List of fetched ticket dictionaries

        Returns:
            List of synthesized ticket dictionaries
        """
        self.console.print("\n[bold cyan][PHASE 2] Synthesizing with Gemini 2.5 Pro[/bold cyan]")

        # Filter tickets that were successfully fetched
        tickets_to_synthesize = [
            t for t in tickets
            if t.get('processing_status') == 'success'
        ]

        if not tickets_to_synthesize:
            self.console.print("[yellow]⚠[/yellow] No tickets to synthesize (all fetches failed)")
            return tickets

        synthesized_tickets = []

        # Progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(
                "[cyan]Synthesizing tickets...",
                total=len(tickets_to_synthesize)
            )

            def progress_callback(ticket_id: str, result: dict, success: bool):
                """Callback for progress updates."""
                if success:
                    self.stats['synthesis_success'] += 1
                else:
                    self.stats['synthesis_failed'] += 1

                progress.update(task, advance=1)

            # Synthesize all tickets
            synthesized_tickets = await self.synthesizer.synthesize_multiple(
                tickets,
                progress_callback
            )

        # Display results
        self.console.print(
            f"[green]✓[/green] Successfully synthesized: {self.stats['synthesis_success']} tickets"
        )
        if self.stats['synthesis_failed'] > 0:
            self.console.print(
                f"[red]✗[/red] Failed: {self.stats['synthesis_failed']} tickets"
            )

        return synthesized_tickets

    async def categorization_phase(self, tickets: List[dict]) -> List[dict]:
        """
        Phase 3: Categorize synthesized tickets into PODs.

        This is the new phase added in Phase 2 of the project.
        Takes synthesized tickets and assigns them to PODs using LLM-based
        categorization with confidence scoring.

        Args:
            tickets: List of synthesized ticket dictionaries

        Returns:
            List of categorized ticket dictionaries
        """
        self.console.print("\n[bold cyan][PHASE 3] Categorizing into PODs[/bold cyan]")

        # Filter tickets that were successfully synthesized
        # Only categorize tickets with synthesis data
        tickets_to_categorize = [
            t for t in tickets
            if t.get('processing_status') == 'success' and 'synthesis' in t
        ]

        if not tickets_to_categorize:
            self.console.print("[yellow]⚠[/yellow] No tickets to categorize (all synthesis failed)")
            return tickets

        categorized_tickets = []

        # Progress tracking with real-time updates
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(
                "[cyan]Categorizing tickets...",
                total=len(tickets_to_categorize)
            )

            def progress_callback(ticket_id: str, result: dict, success: bool):
                """
                Callback for progress updates during categorization.

                Tracks:
                - Success/failure counts
                - Confidence breakdown (confident vs not confident)
                - POD distribution
                """
                if success:
                    self.stats['categorization_success'] += 1

                    # Track confidence breakdown
                    categorization = result.get('categorization', {})
                    confidence = categorization.get('confidence', '')

                    if confidence == 'confident':
                        self.stats['confident_count'] += 1
                    elif confidence == 'not confident':
                        self.stats['not_confident_count'] += 1

                    # Track POD distribution
                    primary_pod = categorization.get('primary_pod', 'Unknown')
                    if primary_pod:
                        self.stats['pod_distribution'][primary_pod] = \
                            self.stats['pod_distribution'].get(primary_pod, 0) + 1
                else:
                    self.stats['categorization_failed'] += 1

                progress.update(task, advance=1)

            # Categorize all tickets in parallel with rate limiting
            categorized_tickets = await self.categorizer.categorize_multiple(
                tickets,
                progress_callback
            )

        # Display categorization results
        self.console.print(
            f"[green]✓[/green] Successfully categorized: {self.stats['categorization_success']} tickets"
        )
        if self.stats['confident_count'] > 0 or self.stats['not_confident_count'] > 0:
            self.console.print(
                f"   • Confident: {self.stats['confident_count']} tickets"
            )
            self.console.print(
                f"   • Not Confident: {self.stats['not_confident_count']} tickets"
            )
        if self.stats['categorization_failed'] > 0:
            self.console.print(
                f"[red]✗[/red] Failed: {self.stats['categorization_failed']} tickets"
            )

        return categorized_tickets

    def generate_output(self, tickets: List[dict]) -> dict:
        """
        Generate final output JSON structure with Phase 2 enhancements.

        Includes:
        - Phase 1 & 2 stats (fetch, synthesis)
        - Phase 2 stats (categorization, confidence, POD distribution) - NEW
        - All ticket data with synthesis and categorization
        - Error tracking

        Args:
            tickets: List of processed ticket dictionaries

        Returns:
            Complete output dictionary with enhanced metadata
        """
        self.console.print("\n[cyan]Generating output JSON...[/cyan]")

        # Calculate processing time
        processing_time = self.stats['end_time'] - self.stats['start_time']

        # Build enhanced output structure with Phase 2 metadata
        output = {
            "metadata": {
                "total_tickets": self.stats['total_tickets'],
                "successfully_processed": self.stats['categorization_success'],  # Phase 2: Updated
                "synthesis_failed": self.stats['synthesis_failed'],  # Phase 2: New
                "categorization_failed": self.stats['categorization_failed'],  # Phase 2: New
                "failed": (
                    self.stats['fetch_failed'] +
                    self.stats['synthesis_failed'] +
                    self.stats['categorization_failed']
                ),
                # Phase 2: Confidence breakdown
                "confidence_breakdown": {
                    "confident": self.stats['confident_count'],
                    "not_confident": self.stats['not_confident_count']
                },
                # Phase 2: POD distribution
                "pod_distribution": self.stats['pod_distribution'],
                "processed_at": utils.get_current_ist_timestamp(),
                "processing_time_seconds": round(processing_time, 2)
            },
            "tickets": [],
            "errors": []
        }

        # Process tickets
        for ticket in tickets:
            if ticket.get('processing_status') == 'success' and 'synthesis' in ticket:
                # Successfully processed ticket
                output["tickets"].append(ticket)
            else:
                # Failed ticket
                output["tickets"].append(ticket)
                output["errors"].append({
                    "ticket_id": ticket.get('ticket_id'),
                    "serial_no": ticket.get('serial_no'),
                    "error_type": ticket.get('error_type', 'UnknownError'),
                    "message": ticket.get('error', 'Unknown error occurred')
                })

        return output

    def save_output(self, output: dict) -> str:
        """
        Save output to JSON file.

        Args:
            output: Output dictionary to save

        Returns:
            Output filename
        """
        filename = utils.generate_output_filename()

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Output saved to {filename}")
        return filename

    def display_summary(self, output_filename: str):
        """
        Display final summary to console with Phase 2 enhancements.

        Shows:
        - Overall processing stats
        - Confidence breakdown (Phase 2)
        - POD distribution (Phase 2)
        - Processing time
        - Log file location

        Args:
            output_filename: Name of the output file
        """
        processing_time = self.stats['end_time'] - self.stats['start_time']
        minutes = int(processing_time // 60)
        seconds = int(processing_time % 60)

        # Create summary table with Phase 2 stats
        table = Table(title="Summary", show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Tickets:", str(self.stats['total_tickets']))
        table.add_row(
            "Successfully Processed:",
            f"[green]{self.stats['categorization_success']}[/green]"
        )
        table.add_row(
            "Failed:",
            f"[red]{self.stats['fetch_failed'] + self.stats['synthesis_failed'] + self.stats['categorization_failed']}[/red]"
        )

        # Phase 2: Confidence breakdown
        if self.stats['confident_count'] > 0 or self.stats['not_confident_count'] > 0:
            table.add_row("Confidence Breakdown:", "")
            table.add_row(
                "  • Confident:",
                f"[green]{self.stats['confident_count']}[/green]"
            )
            table.add_row(
                "  • Not Confident:",
                f"[yellow]{self.stats['not_confident_count']}[/yellow]"
            )

        # Phase 2: POD distribution
        if self.stats['pod_distribution']:
            table.add_row("POD Distribution:", "")
            for pod, count in sorted(self.stats['pod_distribution'].items()):
                table.add_row(f"  • {pod}:", str(count))

        table.add_row("Total Time:", f"{minutes}m {seconds}s")
        table.add_row("Log File:", f"logs/app_{datetime.now().strftime('%Y%m%d')}.log")

        # Display in panel
        self.console.print("\n")
        self.console.print(Panel(table, border_style="green"))
        self.console.print(f"\n[green]✓[/green] Output saved: [bold]{output_filename}[/bold]\n")

    async def run(self, csv_path: str):
        """
        Main workflow execution.

        Args:
            csv_path: Path to input CSV file
        """
        try:
            # Display header
            self.console.print(
                Panel.fit(
                    "[bold cyan]Zendesk Ticket Summarizer[/bold cyan]\n"
                    "Powered by Gemini 2.5 Pro",
                    border_style="cyan"
                )
            )

            # Start timer
            self.stats['start_time'] = time.time()

            # Load CSV
            self.console.print(f"\n[cyan]Loading CSV:[/cyan] {csv_path}")
            ticket_ids = self.load_csv(csv_path)
            self.stats['total_tickets'] = len(ticket_ids)
            self.console.print(f"[green]✓[/green] Found {len(ticket_ids)} tickets to process")

            # Phase 1: Fetch tickets from Zendesk
            fetched_tickets = await self.fetch_phase(ticket_ids)

            # Phase 2: Synthesize tickets using Gemini LLM
            synthesized_tickets = await self.synthesis_phase(fetched_tickets)

            # Phase 3: Categorize tickets into PODs (NEW in Phase 2)
            categorized_tickets = await self.categorization_phase(synthesized_tickets)

            # End timer
            self.stats['end_time'] = time.time()

            # Generate output with Phase 2 enhancements
            output = self.generate_output(categorized_tickets)

            # Save output
            output_filename = self.save_output(output)

            # Display summary
            self.display_summary(output_filename)

        except FileNotFoundError as e:
            self.console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except ValueError as e:
            self.console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠[/yellow] Process interrupted by user")
            sys.exit(1)
        except Exception as e:
            self.logger.exception("Unexpected error occurred")
            self.console.print(f"[red]Unexpected error:[/red] {e}")
            sys.exit(1)


def main():
    """
    Main entry point for the CLI application.
    """
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python main.py <input_csv_path>")
        print("\nExample:")
        print("  python main.py input_tickets.csv")
        sys.exit(1)

    csv_path = sys.argv[1]

    # Create and run summarizer
    summarizer = TicketSummarizer()
    asyncio.run(summarizer.run(csv_path))


if __name__ == "__main__":
    main()
