"""
CSV export functionality for ticket analysis results.
Generates CSV files for easy analysis in Google Sheets.
"""

import csv
import logging
from typing import List, Dict


class CSVExporter:
    """Exports ticket analysis results to CSV format."""

    def __init__(self):
        """Initialize CSV exporter."""
        self.logger = logging.getLogger("ticket_summarizer.csv_exporter")

    def export_pod_categorization(self, tickets: List[Dict], output_path: str) -> None:
        """
        Export POD categorization results to CSV.

        Args:
            tickets: List of ticket dictionaries with categorization results
            output_path: Path to output CSV file
        """
        self.logger.info(f"Exporting POD categorization to CSV: {output_path}")

        # Define CSV columns (excluding 'updated_at' as per Phase 5 requirements)
        fieldnames = [
            "ticket_id",
            "serial_no",
            "url",
            "subject",
            "status",
            "created_at",
            "comments_count",
            "is_escalated",
            "jira_ticket_id",
            "jira_ticket_url",
            "issue_reported",
            "root_cause",
            "summary",
            "resolution",
            "primary_pod",
            "categorization_reasoning",
            "confidence",
            "alternative_pods",
            "alternative_reasoning",
            "processing_status",
            "error"
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for ticket in tickets:
                # Extract escalation data
                escalation = ticket.get("custom_fields", {}).get("escalation", {})

                # Extract synthesis data
                synthesis = ticket.get("synthesis", {})

                # Extract categorization data
                categorization = ticket.get("categorization", {})

                # Build row
                row = {
                    "ticket_id": ticket.get("ticket_id", ""),
                    "serial_no": ticket.get("serial_no", ""),
                    "url": ticket.get("url", ""),
                    "subject": ticket.get("subject", ""),
                    "status": ticket.get("status", ""),
                    "created_at": ticket.get("created_at", ""),
                    "comments_count": ticket.get("comments_count", 0),
                    "is_escalated": escalation.get("is_escalated", False),
                    "jira_ticket_id": escalation.get("jira_ticket_id", ""),
                    "jira_ticket_url": escalation.get("jira_ticket_url", ""),
                    "issue_reported": synthesis.get("issue_reported", ""),
                    "root_cause": synthesis.get("root_cause", ""),
                    "summary": synthesis.get("summary", ""),
                    "resolution": synthesis.get("resolution", ""),
                    "primary_pod": categorization.get("primary_pod", ""),
                    "categorization_reasoning": categorization.get("reasoning", ""),
                    "confidence": categorization.get("confidence", ""),
                    "alternative_pods": categorization.get("alternative_pods", ""),
                    "alternative_reasoning": categorization.get("alternative_reasoning", ""),
                    "processing_status": ticket.get("processing_status", ""),
                    "error": ticket.get("error", "")
                }

                writer.writerow(row)

        self.logger.info(f"CSV export complete: {len(tickets)} tickets exported")

    def export_diagnostics_analysis(self, tickets: List[Dict], output_path: str) -> None:
        """
        Export diagnostics analysis results to CSV.

        Args:
            tickets: List of ticket dictionaries with diagnostics analysis results
            output_path: Path to output CSV file
        """
        self.logger.info(f"Exporting diagnostics analysis to CSV: {output_path}")

        # Define CSV columns (excluding 'updated_at' as per Phase 5 requirements)
        # Phase 6: Added triage/fix/overall split assessments
        fieldnames = [
            "ticket_id",
            "serial_no",
            "url",
            "subject",
            "status",
            "created_at",
            "comments_count",
            "is_escalated",
            "jira_ticket_id",
            "jira_ticket_url",
            "issue_reported",
            "root_cause",
            "support_root_cause",
            "summary",
            "resolution",
            "was_diagnostics_used_custom_field",
            "was_diagnostics_used_llm_assessment",
            "was_diagnostics_used_confidence",
            "was_diagnostics_used_reasoning",
            "triage_assessment",
            "triage_reasoning",
            "fix_assessment",
            "fix_reasoning",
            "overall_assessment",
            "overall_reasoning",
            "diagnostics_confidence",
            "diagnostics_capabilities_matched",
            "limitation_notes",
            "ticket_type",
            "processing_status",
            "error"
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for ticket in tickets:
                # Extract escalation data
                escalation = ticket.get("custom_fields", {}).get("escalation", {})

                # Extract custom fields (Phase 6: includes support_root_cause)
                custom_fields = ticket.get("custom_fields", {})

                # Extract synthesis data
                synthesis = ticket.get("synthesis", {})

                # Extract diagnostics analysis data
                diagnostics = ticket.get("diagnostics_analysis", {})
                was_used = diagnostics.get("was_diagnostics_used", {})
                could_help = diagnostics.get("could_diagnostics_help", {})
                metadata = diagnostics.get("metadata", {})

                # Format diagnostics capabilities as comma-separated string
                capabilities = could_help.get("diagnostics_capability_matched", [])
                capabilities_str = ", ".join(capabilities) if capabilities else ""

                # Build row (Phase 6: triage/fix/overall split)
                row = {
                    "ticket_id": ticket.get("ticket_id", ""),
                    "serial_no": ticket.get("serial_no", ""),
                    "url": ticket.get("url", ""),
                    "subject": ticket.get("subject", ""),
                    "status": ticket.get("status", ""),
                    "created_at": ticket.get("created_at", ""),
                    "comments_count": ticket.get("comments_count", 0),
                    "is_escalated": escalation.get("is_escalated", False),
                    "jira_ticket_id": escalation.get("jira_ticket_id", ""),
                    "jira_ticket_url": escalation.get("jira_ticket_url", ""),
                    "issue_reported": synthesis.get("issue_reported", ""),
                    "root_cause": synthesis.get("root_cause", ""),
                    "support_root_cause": custom_fields.get("support_root_cause", ""),
                    "summary": synthesis.get("summary", ""),
                    "resolution": synthesis.get("resolution", ""),
                    "was_diagnostics_used_custom_field": custom_fields.get("was_diagnostics_used", ""),
                    "was_diagnostics_used_llm_assessment": was_used.get("llm_assessment", ""),
                    "was_diagnostics_used_confidence": was_used.get("confidence", ""),
                    "was_diagnostics_used_reasoning": was_used.get("reasoning", ""),
                    "triage_assessment": could_help.get("triage_assessment", ""),
                    "triage_reasoning": could_help.get("triage_reasoning", ""),
                    "fix_assessment": could_help.get("fix_assessment", ""),
                    "fix_reasoning": could_help.get("fix_reasoning", ""),
                    "overall_assessment": could_help.get("overall_assessment", ""),
                    "overall_reasoning": could_help.get("overall_reasoning", ""),
                    "diagnostics_confidence": could_help.get("confidence", ""),
                    "diagnostics_capabilities_matched": capabilities_str,
                    "limitation_notes": could_help.get("limitation_notes", ""),
                    "ticket_type": metadata.get("ticket_type", ""),
                    "processing_status": ticket.get("processing_status", ""),
                    "error": ticket.get("error", "")
                }

                writer.writerow(row)

        self.logger.info(f"CSV export complete: {len(tickets)} tickets exported")
