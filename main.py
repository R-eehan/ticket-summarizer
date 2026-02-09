#!/usr/bin/env python3
"""
Zendesk Ticket Summarizer - Main Entry Point

A terminal-based application that fetches Zendesk tickets and uses
Google Gemini 2.5 Pro to generate comprehensive summaries.

Usage:
    python main.py --input <csv_path> --analysis-type <pod|diagnostics|both>
"""

import sys
import csv
import json
import asyncio
import time
import argparse
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
from diagnostics_analyzer import DiagnosticsAnalyzer
from csv_exporter import CSVExporter


class TicketSummarizer:
    """
    Main orchestrator for ticket summarization workflow.
    """

    def __init__(self, analysis_type: str = "pod", model_provider: str = "gemini"):
        """
        Initialize the summarizer with logger and components.

        Sets up:
        - Logger for tracking all operations
        - Console for rich terminal output
        - Fetcher for Zendesk API calls (Phase 1)
        - Synthesizer for LLM summarization (Phase 2)
        - Categorizer for POD assignment (Phase 3a) - Phase 2
        - Diagnostics Analyzer for Diagnostics analysis (Phase 3b) - Phase 3b
        - Statistics tracking for all phases

        Args:
            analysis_type: Type of analysis to perform ("pod", "diagnostics", or "both")
            model_provider: LLM provider to use ("gemini" or "azure")
        """
        self.logger = utils.setup_logger("ticket_summarizer")
        self.console = Console()
        self.analysis_type = analysis_type
        self.model_provider = model_provider
        self.fetcher = ZendeskFetcher()
        self.synthesizer = GeminiSynthesizer(model_provider=model_provider)  # Phase 3c: Multi-model
        self.categorizer = TicketCategorizer()  # Phase 3a: POD categorization
        self.diagnostics_analyzer = DiagnosticsAnalyzer(model_provider=model_provider)  # Phase 3b + 3c

        # Statistics tracking for all phases
        self.stats = {
            "total_tickets": 0,
            "fetch_success": 0,
            "fetch_failed": 0,
            "synthesis_success": 0,
            "synthesis_failed": 0,
            # POD categorization stats (Phase 3a)
            "categorization_success": 0,
            "categorization_failed": 0,
            "confident_count": 0,
            "not_confident_count": 0,
            "pod_distribution": {},
            # Diagnostics analysis stats (Phase 3b)
            "diagnostics_analysis_success": 0,
            "diagnostics_analysis_failed": 0,
            "diagnostics_was_used": {"yes": 0, "no": 0, "unknown": 0},
            "diagnostics_could_help": {"yes": 0, "no": 0, "maybe": 0},
            "diagnostics_confidence": {"confident": 0, "not_confident": 0},
            # Engineering escalation stats (Phase 5)
            "escalated_count": 0,
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

                    # Track escalation (Phase 5)
                    escalation = result.get('custom_fields', {}).get('escalation', {})
                    if escalation.get('is_escalated', False):
                        self.stats['escalated_count'] += 1
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

    async def diagnostics_phase(self, tickets: List[dict]) -> List[dict]:
        """
        Phase 3b: Analyze tickets for Diagnostics feature applicability.

        This is the new phase added in Phase 3b of the project.
        Takes synthesized tickets and analyzes whether Diagnostics was used
        and could have helped resolve the issue.

        Args:
            tickets: List of synthesized ticket dictionaries

        Returns:
            List of tickets with diagnostics analysis
        """
        self.console.print("\n[bold cyan][PHASE 3b] Analyzing Diagnostics Applicability[/bold cyan]")

        # Filter tickets that were successfully synthesized
        # Only analyze tickets with synthesis data
        tickets_to_analyze = [
            t for t in tickets
            if t.get('processing_status') == 'success' and 'synthesis' in t
        ]

        if not tickets_to_analyze:
            self.console.print("[yellow]⚠[/yellow] No tickets to analyze (all synthesis failed)")
            return tickets

        analyzed_tickets = []

        # Progress tracking with real-time updates
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(
                "[cyan]Analyzing Diagnostics applicability...",
                total=len(tickets_to_analyze)
            )

            def progress_callback(ticket_id: str, result: dict):
                """
                Callback for progress updates during diagnostics analysis.

                Tracks:
                - Success/failure counts
                - "Was Diagnostics used?" breakdown
                - "Could Diagnostics help?" breakdown
                - Confidence breakdown
                """
                if result.get('diagnostics_analysis_status') == 'success':
                    self.stats['diagnostics_analysis_success'] += 1

                    # Get diagnostics analysis data
                    diag_analysis = result.get('diagnostics_analysis', {})

                    # Track "was_diagnostics_used" breakdown
                    was_used = diag_analysis.get('was_diagnostics_used', {})
                    llm_assessment = was_used.get('llm_assessment', '').lower()
                    if llm_assessment in ['yes', 'no', 'unknown']:
                        self.stats['diagnostics_was_used'][llm_assessment] += 1

                    # Track "could_diagnostics_help" breakdown
                    could_help = diag_analysis.get('could_diagnostics_help', {})
                    assessment = could_help.get('assessment', '').lower()
                    if assessment in ['yes', 'no', 'maybe']:
                        self.stats['diagnostics_could_help'][assessment] += 1

                    # Track confidence (using could_diagnostics_help confidence)
                    confidence = could_help.get('confidence', '').lower()
                    if confidence == 'confident':
                        self.stats['diagnostics_confidence']['confident'] += 1
                    elif confidence == 'not confident':
                        self.stats['diagnostics_confidence']['not_confident'] += 1

                    # Track escalation (Phase 5)
                    escalation = result.get('custom_fields', {}).get('escalation', {})
                    if escalation.get('is_escalated', False):
                        self.stats['escalated_count'] += 1

                else:
                    self.stats['diagnostics_analysis_failed'] += 1

                progress.update(task, advance=1)

            # Analyze all tickets with rate limiting
            analyzed_tickets = await self.diagnostics_analyzer.analyze_multiple(
                tickets,
                progress_callback
            )

        # Display diagnostics analysis results
        self.console.print(
            f"[green]✓[/green] Successfully analyzed: {self.stats['diagnostics_analysis_success']} tickets"
        )
        if self.stats['diagnostics_confidence']['confident'] > 0 or self.stats['diagnostics_confidence']['not_confident'] > 0:
            self.console.print(
                f"   • Confident: {self.stats['diagnostics_confidence']['confident']} tickets"
            )
            self.console.print(
                f"   • Not Confident: {self.stats['diagnostics_confidence']['not_confident']} tickets"
            )
        if self.stats['diagnostics_analysis_failed'] > 0:
            self.console.print(
                f"[red]✗[/red] Failed: {self.stats['diagnostics_analysis_failed']} tickets"
            )

        return analyzed_tickets

    def generate_output(self, tickets: List[dict]) -> dict:
        """
        Generate final output JSON structure based on analysis type.

        Includes:
        - Phase 1 & 2 stats (fetch, synthesis)
        - Phase 3a stats (POD categorization) OR
        - Phase 3b stats (Diagnostics analysis) OR
        - Both (when analysis_type is "both")
        - All ticket data with appropriate analysis results
        - Error tracking

        Args:
            tickets: List of processed ticket dictionaries

        Returns:
            Complete output dictionary with appropriate metadata
        """
        self.console.print("\n[cyan]Generating output JSON...[/cyan]")

        # Calculate processing time
        processing_time = self.stats['end_time'] - self.stats['start_time']

        # Calculate escalation statistics (Phase 5)
        escalated_count = sum(
            1 for ticket in tickets
            if ticket.get("processing_status") == "success"
            and ticket.get("custom_fields", {}).get("escalation", {}).get("is_escalated", False)
        )
        successful_count = sum(
            1 for ticket in tickets
            if ticket.get("processing_status") == "success"
        )
        escalation_rate = (escalated_count / successful_count * 100) if successful_count > 0 else 0

        # Build metadata based on analysis type
        if self.analysis_type == "pod":
            # POD categorization metadata
            metadata = {
                "analysis_type": "pod",
                "total_tickets": self.stats['total_tickets'],
                "successfully_processed": self.stats['categorization_success'],
                "synthesis_failed": self.stats['synthesis_failed'],
                "categorization_failed": self.stats['categorization_failed'],
                "failed": (
                    self.stats['fetch_failed'] +
                    self.stats['synthesis_failed'] +
                    self.stats['categorization_failed']
                ),
                "confidence_breakdown": {
                    "confident": self.stats['confident_count'],
                    "not_confident": self.stats['not_confident_count']
                },
                "pod_distribution": self.stats['pod_distribution'],
                "escalation_breakdown": {
                    "total_escalated": escalated_count,
                    "total_not_escalated": successful_count - escalated_count,
                    "escalation_rate": f"{escalation_rate:.2f}%"
                },
                "processed_at": utils.get_current_ist_timestamp(),
                "processing_time_seconds": round(processing_time, 2)
            }
        elif self.analysis_type == "diagnostics":
            # Diagnostics analysis metadata
            metadata = {
                "analysis_type": "diagnostics",
                "total_tickets": self.stats['total_tickets'],
                "successfully_processed": self.stats['diagnostics_analysis_success'],
                "synthesis_failed": self.stats['synthesis_failed'],
                "diagnostics_analysis_failed": self.stats['diagnostics_analysis_failed'],
                "failed": (
                    self.stats['fetch_failed'] +
                    self.stats['synthesis_failed'] +
                    self.stats['diagnostics_analysis_failed']
                ),
                "diagnostics_breakdown": {
                    "was_used": self.stats['diagnostics_was_used'],
                    "could_help": self.stats['diagnostics_could_help'],
                    "confidence": self.stats['diagnostics_confidence']
                },
                "escalation_breakdown": {
                    "total_escalated": escalated_count,
                    "total_not_escalated": successful_count - escalated_count,
                    "escalation_rate": f"{escalation_rate:.2f}%"
                },
                "processed_at": utils.get_current_ist_timestamp(),
                "processing_time_seconds": round(processing_time, 2)
            }
        else:  # both
            # Combined metadata
            metadata = {
                "analysis_type": "both",
                "total_tickets": self.stats['total_tickets'],
                "successfully_processed": min(
                    self.stats['categorization_success'],
                    self.stats['diagnostics_analysis_success']
                ),
                "synthesis_failed": self.stats['synthesis_failed'],
                "categorization_failed": self.stats['categorization_failed'],
                "diagnostics_analysis_failed": self.stats['diagnostics_analysis_failed'],
                "failed": (
                    self.stats['fetch_failed'] +
                    self.stats['synthesis_failed'] +
                    max(self.stats['categorization_failed'], self.stats['diagnostics_analysis_failed'])
                ),
                "pod_analysis": {
                    "confidence_breakdown": {
                        "confident": self.stats['confident_count'],
                        "not_confident": self.stats['not_confident_count']
                    },
                    "pod_distribution": self.stats['pod_distribution']
                },
                "diagnostics_analysis": {
                    "was_used": self.stats['diagnostics_was_used'],
                    "could_help": self.stats['diagnostics_could_help'],
                    "confidence": self.stats['diagnostics_confidence']
                },
                "escalation_breakdown": {
                    "total_escalated": escalated_count,
                    "total_not_escalated": successful_count - escalated_count,
                    "escalation_rate": f"{escalation_rate:.2f}%"
                },
                "processed_at": utils.get_current_ist_timestamp(),
                "processing_time_seconds": round(processing_time, 2)
            }

        output = {
            "metadata": metadata,
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

    def save_output(self, output: dict, analysis_type: str = None) -> str:
        """
        Save output to JSON file with analysis-type-specific naming.

        Args:
            output: Output dictionary to save
            analysis_type: Type of analysis ("pod", "diagnostics", "both")

        Returns:
            Output filename
        """
        # Generate timestamped filename based on analysis type
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_suffix = analysis_type or self.analysis_type

        if analysis_suffix == "both":
            # For "both", generate two separate files
            pod_filename = f"output_pod_{timestamp}.json"
            diagnostics_filename = f"output_diagnostics_{timestamp}.json"

            # Create POD-specific output
            pod_output = output.copy()
            pod_output["metadata"]["analysis_type"] = "pod"

            # Create Diagnostics-specific output
            diag_output = output.copy()
            diag_output["metadata"]["analysis_type"] = "diagnostics"

            # Save both JSON files
            with open(pod_filename, 'w', encoding='utf-8') as f:
                json.dump(pod_output, f, indent=2, ensure_ascii=False)
            with open(diagnostics_filename, 'w', encoding='utf-8') as f:
                json.dump(diag_output, f, indent=2, ensure_ascii=False)

            self.logger.info(f"POD output saved to {pod_filename}")
            self.logger.info(f"Diagnostics output saved to {diagnostics_filename}")

            # Generate CSV files (Phase 5)
            csv_exporter = CSVExporter()
            pod_csv_filename = pod_filename.replace(".json", ".csv")
            diagnostics_csv_filename = diagnostics_filename.replace(".json", ".csv")

            csv_exporter.export_pod_categorization(output["tickets"], pod_csv_filename)
            csv_exporter.export_diagnostics_analysis(output["tickets"], diagnostics_csv_filename)

            self.logger.info(f"POD CSV saved to {pod_csv_filename}")
            self.logger.info(f"Diagnostics CSV saved to {diagnostics_csv_filename}")

            return f"{pod_filename}, {diagnostics_filename}"
        else:
            # Single file for pod or diagnostics
            filename = f"output_{analysis_suffix}_{timestamp}.json"

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Output saved to {filename}")

            # Generate CSV file (Phase 5)
            csv_exporter = CSVExporter()
            csv_filename = filename.replace(".json", ".csv")

            if analysis_suffix == "pod":
                csv_exporter.export_pod_categorization(output["tickets"], csv_filename)
            elif analysis_suffix == "diagnostics":
                csv_exporter.export_diagnostics_analysis(output["tickets"], csv_filename)

            self.logger.info(f"CSV saved to {csv_filename}")

            return filename

    def display_summary(self, output_filename: str):
        """
        Display final summary to console based on analysis type.

        Shows:
        - Overall processing stats
        - Analysis-type-specific breakdowns
        - Processing time
        - Log file location

        Args:
            output_filename: Name of the output file(s)
        """
        processing_time = self.stats['end_time'] - self.stats['start_time']
        minutes = int(processing_time // 60)
        seconds = int(processing_time % 60)

        # Create summary table
        table = Table(title="Summary", show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Analysis Type:", self.analysis_type.upper())
        table.add_row("Total Tickets:", str(self.stats['total_tickets']))

        if self.analysis_type == "pod":
            # POD categorization summary
            table.add_row(
                "Successfully Processed:",
                f"[green]{self.stats['categorization_success']}[/green]"
            )
            table.add_row(
                "Failed:",
                f"[red]{self.stats['fetch_failed'] + self.stats['synthesis_failed'] + self.stats['categorization_failed']}[/red]"
            )

            # Confidence breakdown
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

            # POD distribution
            if self.stats['pod_distribution']:
                table.add_row("POD Distribution:", "")
                for pod, count in sorted(self.stats['pod_distribution'].items()):
                    table.add_row(f"  • {pod}:", str(count))

            # Escalation summary (Phase 5)
            escalated = self.stats.get('escalated_count', 0)
            not_escalated = self.stats['categorization_success'] - escalated
            escalation_rate = (escalated / self.stats['categorization_success'] * 100) if self.stats['categorization_success'] > 0 else 0
            table.add_row("Escalation Summary:", "")
            table.add_row(
                "  • Escalated to Engineering:",
                f"[yellow]{escalated}[/yellow] ({escalation_rate:.2f}%)"
            )
            table.add_row(
                "  • Not Escalated:",
                f"[green]{not_escalated}[/green]"
            )

        elif self.analysis_type == "diagnostics":
            # Diagnostics analysis summary
            table.add_row(
                "Successfully Processed:",
                f"[green]{self.stats['diagnostics_analysis_success']}[/green]"
            )
            table.add_row(
                "Failed:",
                f"[red]{self.stats['fetch_failed'] + self.stats['synthesis_failed'] + self.stats['diagnostics_analysis_failed']}[/red]"
            )

            # Was Diagnostics Used breakdown
            if any(self.stats['diagnostics_was_used'].values()):
                table.add_row("Was Diagnostics Used?", "")
                table.add_row(
                    "  • Yes:",
                    f"[green]{self.stats['diagnostics_was_used']['yes']}[/green]"
                )
                table.add_row(
                    "  • No:",
                    f"[red]{self.stats['diagnostics_was_used']['no']}[/red]"
                )
                table.add_row(
                    "  • Unknown:",
                    f"[yellow]{self.stats['diagnostics_was_used']['unknown']}[/yellow]"
                )

            # Could Diagnostics Help breakdown
            if any(self.stats['diagnostics_could_help'].values()):
                table.add_row("Could Diagnostics Help?", "")
                table.add_row(
                    "  • Yes:",
                    f"[green]{self.stats['diagnostics_could_help']['yes']}[/green]"
                )
                table.add_row(
                    "  • No:",
                    f"[red]{self.stats['diagnostics_could_help']['no']}[/red]"
                )
                table.add_row(
                    "  • Maybe:",
                    f"[yellow]{self.stats['diagnostics_could_help']['maybe']}[/yellow]"
                )

            # Confidence breakdown
            if any(self.stats['diagnostics_confidence'].values()):
                table.add_row("Confidence:", "")
                table.add_row(
                    "  • Confident:",
                    f"[green]{self.stats['diagnostics_confidence']['confident']}[/green]"
                )
                table.add_row(
                    "  • Not Confident:",
                    f"[yellow]{self.stats['diagnostics_confidence']['not_confident']}[/yellow]"
                )

            # Escalation summary (Phase 5)
            escalated = self.stats.get('escalated_count', 0)
            not_escalated = self.stats['diagnostics_analysis_success'] - escalated
            escalation_rate = (escalated / self.stats['diagnostics_analysis_success'] * 100) if self.stats['diagnostics_analysis_success'] > 0 else 0
            table.add_row("Escalation Summary:", "")
            table.add_row(
                "  • Escalated to Engineering:",
                f"[yellow]{escalated}[/yellow] ({escalation_rate:.2f}%)"
            )
            table.add_row(
                "  • Not Escalated:",
                f"[green]{not_escalated}[/green]"
            )

        else:  # both
            # Combined summary
            table.add_row(
                "Successfully Processed:",
                f"[green]{min(self.stats['categorization_success'], self.stats['diagnostics_analysis_success'])}[/green]"
            )
            table.add_row(
                "Failed:",
                f"[red]{self.stats['fetch_failed'] + self.stats['synthesis_failed'] + max(self.stats['categorization_failed'], self.stats['diagnostics_analysis_failed'])}[/red]"
            )

            # POD stats
            table.add_row("POD Analysis:", "")
            if self.stats['pod_distribution']:
                for pod, count in sorted(self.stats['pod_distribution'].items()):
                    table.add_row(f"  • {pod}:", str(count))

            # Diagnostics stats
            table.add_row("Diagnostics Analysis:", "")
            table.add_row(
                "  • Could Help (Yes):",
                f"[green]{self.stats['diagnostics_could_help']['yes']}[/green]"
            )
            table.add_row(
                "  • Could Help (No):",
                f"[red]{self.stats['diagnostics_could_help']['no']}[/red]"
            )

        table.add_row("Total Time:", f"{minutes}m {seconds}s")
        table.add_row("Log File:", f"logs/app_{datetime.now().strftime('%Y%m%d')}.log")

        # Display in panel
        self.console.print("\n")
        self.console.print(Panel(table, border_style="green"))
        self.console.print(f"\n[green]✓[/green] Output saved: [bold]{output_filename}[/bold]\n")

    async def run(self, csv_path: str):
        """
        Main workflow execution with branching based on analysis type.

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

            # Display analysis type and model provider
            self.console.print(f"\n[bold cyan]Analysis Type:[/bold cyan] {self.analysis_type.upper()}")
            self.console.print(f"[bold cyan]Model Provider:[/bold cyan] {self.model_provider.upper()}")

            # Start timer
            self.stats['start_time'] = time.time()

            # Load CSV
            self.console.print(f"[cyan]Loading CSV:[/cyan] {csv_path}")
            ticket_ids = self.load_csv(csv_path)
            self.stats['total_tickets'] = len(ticket_ids)
            self.console.print(f"[green]✓[/green] Found {len(ticket_ids)} tickets to process")

            # Phase 1: Fetch tickets from Zendesk (with custom fields)
            fetched_tickets = await self.fetch_phase(ticket_ids)

            # Phase 2: Synthesize tickets using Gemini LLM
            synthesized_tickets = await self.synthesis_phase(fetched_tickets)

            # Phase 3: Branch based on analysis type
            processed_tickets = synthesized_tickets

            if self.analysis_type == "pod":
                # Phase 3a: POD categorization only
                processed_tickets = await self.categorization_phase(synthesized_tickets)

            elif self.analysis_type == "diagnostics":
                # Phase 3b: Diagnostics analysis only
                processed_tickets = await self.diagnostics_phase(synthesized_tickets)

            elif self.analysis_type == "both":
                # Phase 3a + 3b: Run both analyses in parallel
                self.console.print(
                    "\n[bold cyan][PHASE 3] Running POD Categorization + Diagnostics Analysis in Parallel[/bold cyan]"
                )

                # Create tasks for parallel execution
                pod_task = asyncio.create_task(
                    self.categorization_phase(synthesized_tickets)
                )
                diag_task = asyncio.create_task(
                    self.diagnostics_phase(synthesized_tickets)
                )

                # Wait for both to complete
                categorized_tickets, diagnostics_tickets = await asyncio.gather(
                    pod_task, diag_task
                )

                # Merge results (both should have same tickets, just different analysis fields)
                # We'll use the categorized_tickets as base and merge diagnostics analysis
                for i, ticket in enumerate(categorized_tickets):
                    if i < len(diagnostics_tickets):
                        diag_ticket = diagnostics_tickets[i]
                        if 'diagnostics_analysis' in diag_ticket:
                            ticket['diagnostics_analysis'] = diag_ticket['diagnostics_analysis']
                        if 'diagnostics_analysis_status' in diag_ticket:
                            ticket['diagnostics_analysis_status'] = diag_ticket['diagnostics_analysis_status']

                processed_tickets = categorized_tickets

            # End timer
            self.stats['end_time'] = time.time()

            # Generate output based on analysis type
            output = self.generate_output(processed_tickets)

            # Save output (may create multiple files for "both" mode)
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
    Main entry point for the CLI application with argparse support.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Zendesk Ticket Summarizer - Powered by Gemini 2.5 Pro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # POD categorization with Gemini (default)
  python main.py --input tickets.csv --analysis-type pod

  # POD categorization with Azure OpenAI
  python main.py --input tickets.csv --analysis-type pod --model-provider azure

  # Diagnostics analysis with Gemini
  python main.py --input tickets.csv --analysis-type diagnostics

  # Diagnostics analysis with Azure OpenAI
  python main.py --input tickets.csv --analysis-type diagnostics --model-provider azure

  # Both analyses in parallel with Azure OpenAI
  python main.py --input tickets.csv --analysis-type both --model-provider azure
        """
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to input CSV file containing ticket IDs"
    )

    parser.add_argument(
        "--analysis-type",
        choices=["pod", "diagnostics", "both"],
        required=True,
        help="Type of analysis to perform: 'pod' (POD categorization), "
             "'diagnostics' (Diagnostics applicability), or 'both' (run both in parallel)"
    )

    parser.add_argument(
        "--model-provider",
        choices=["gemini", "azure"],
        default="gemini",
        help="LLM provider to use: 'gemini' (Google Gemini free tier) or "
             "'azure' (Azure OpenAI GPT-4o). Defaults to 'gemini'"
    )

    # Parse arguments
    args = parser.parse_args()

    # Create and run summarizer with specified analysis type and model provider
    summarizer = TicketSummarizer(
        analysis_type=args.analysis_type,
        model_provider=args.model_provider
    )
    asyncio.run(summarizer.run(args.input))


if __name__ == "__main__":
    main()
