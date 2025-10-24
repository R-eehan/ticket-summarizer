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


class TicketSummarizer:
    """
    Main orchestrator for ticket summarization workflow.
    """

    def __init__(self):
        """Initialize the summarizer with logger and components."""
        self.logger = utils.setup_logger("ticket_summarizer")
        self.console = Console()
        self.fetcher = ZendeskFetcher()
        self.synthesizer = GeminiSynthesizer()

        # Statistics
        self.stats = {
            "total_tickets": 0,
            "fetch_success": 0,
            "fetch_failed": 0,
            "synthesis_success": 0,
            "synthesis_failed": 0,
            "start_time": None,
            "end_time": None
        }

    def load_csv(self, csv_path: str) -> List[Tuple[int, str]]:
        """
        Load ticket IDs from CSV file.

        Args:
            csv_path: Path to input CSV file

        Returns:
            List of tuples (serial_no, ticket_id)

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV format is invalid
        """
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        ticket_ids = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Validate headers
            if 'Serial No' not in reader.fieldnames or 'Ticket ID' not in reader.fieldnames:
                raise ValueError(
                    "CSV must contain 'Serial No' and 'Ticket ID' columns. "
                    f"Found: {reader.fieldnames}"
                )

            # Read ticket IDs
            for row in reader:
                serial_no = int(row['Serial No'])
                ticket_id = str(row['Ticket ID']).strip()
                ticket_ids.append((serial_no, ticket_id))

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

    def generate_output(self, tickets: List[dict]) -> dict:
        """
        Generate final output JSON structure.

        Args:
            tickets: List of processed ticket dictionaries

        Returns:
            Complete output dictionary
        """
        self.console.print("\n[cyan]Generating output JSON...[/cyan]")

        # Calculate processing time
        processing_time = self.stats['end_time'] - self.stats['start_time']

        # Build output structure
        output = {
            "metadata": {
                "total_tickets": self.stats['total_tickets'],
                "successfully_processed": self.stats['synthesis_success'],
                "failed": self.stats['fetch_failed'] + self.stats['synthesis_failed'],
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
        Display final summary to console.

        Args:
            output_filename: Name of the output file
        """
        processing_time = self.stats['end_time'] - self.stats['start_time']
        minutes = int(processing_time // 60)
        seconds = int(processing_time % 60)

        # Create summary table
        table = Table(title="Summary", show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Tickets:", str(self.stats['total_tickets']))
        table.add_row(
            "Successfully Processed:",
            f"[green]{self.stats['synthesis_success']}[/green]"
        )
        table.add_row(
            "Failed:",
            f"[red]{self.stats['fetch_failed'] + self.stats['synthesis_failed']}[/red]"
        )
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

            # Phase 1: Fetch tickets
            fetched_tickets = await self.fetch_phase(ticket_ids)

            # Phase 2: Synthesize tickets
            synthesized_tickets = await self.synthesis_phase(fetched_tickets)

            # End timer
            self.stats['end_time'] = time.time()

            # Generate output
            output = self.generate_output(synthesized_tickets)

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
