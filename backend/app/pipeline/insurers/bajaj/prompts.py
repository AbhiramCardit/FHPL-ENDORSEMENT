"""
Bajaj — LLM prompts for PDF extraction.

All prompts used for LLM-based document extraction are centralised here.
This makes it easy to iterate on prompts without touching step logic.
"""

from __future__ import annotations


# ═══════════════════════════════════════════════════════════
#  PDF Endorsement Extraction Prompt
# ═══════════════════════════════════════════════════════════

ENDORSEMENT_PDF_PROMPT = """
You are a data extraction AI. Please analyze the **attached PDF document**.

Your goal is to extract specific insurance policy details and premium calculations.

### Extraction Rules:
1. **Address:** Combine all lines of the "Proposer Address" into a single line string.
2. **Premium Table:** For the rows "Net Premium", "Integrated GST (18%)", and "Gross premium", extract the values for all three columns ("Premium on Policy", "Endorsement Premium", "Total Premium after Endorsement").
3. **Endorsement Premium Text:** For the specific key "Endorsement Premium" at the bottom of the JSON, extract the text written in words (e.g., "Rupees Seventy Five...").
4. **Format:** Return the output as a valid, raw JSON object. Do not include markdown formatting (like ```json) or conversational text.

### Output Structure:
Fill in this exact JSON skeleton with the data from the PDF:

{
  "Proposer Name": null,
  "Policy Number": null,
  "Proposer Address": null,
  "Policy Issued on": null,
  "Period of Insurance": null,
  "Endorsement": null,
  "Customer ID": null,
  "GSTIN / UIN": null,
  "Policy Status": null,
  "Invoice No": null,
  "Endorsement Type": null,
  "Effective date": null,
  "Endorsement Issued Date": null,
  "Endorsement Title": null,
  "Premium": {
    "Net Premium": {
      "Premium on Policy": null,
      "Endorsement Premium": null,
      "Total Premium after Endorsement": null
    },
    "Integrated GST (18%)": {
      "Premium on Policy": null,
      "Endorsement Premium": null,
      "Total Premium after Endorsement": null
    },
    "Gross premium": {
      "Premium on Policy": null,
      "Endorsement Premium": null,
      "Total Premium after Endorsement": null
    },
    "Endorsement Premium": null
  }
}
""".strip()


# ═══════════════════════════════════════════════════════════
#  System Prompt
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT = """
You are a structured data extraction assistant for Bajaj Allianz General Insurance
endorsement documents. You always respond with valid JSON.
You never add explanations, markdown formatting, or code blocks — just pure JSON.
""".strip()
