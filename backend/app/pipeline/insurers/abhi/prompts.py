"""
ABHI (Aditya Birla Health Insurance) — LLM prompts for PDF extraction.

All prompts used for LLM-based document extraction are centralised here.
This makes it easy to iterate on prompts without touching step logic.
"""

from __future__ import annotations


# ═══════════════════════════════════════════════════════════
#  PDF Endorsement Schedule Extraction Prompt
# ═══════════════════════════════════════════════════════════

ENDORSEMENT_PDF_PROMPT = """
**Task:** You are a specialized OCR and data extraction assistant. Your goal is to extract specific information from the provided "Endorsement Schedule cum Tax Invoice" document.

**Instructions:**
1. Extract the data exactly as it appears in the text.
2. For the "Address," combine any multi-line address into a single string with proper spacing.
3. For "Period of Insurance," capture both the "From" and "To" dates.
4. If a field is not found, return `null`.
5. **Output Format:** Return only a valid JSON object. No conversational text.

**Schema and Field Mapping:**
- `endorsement_number`: "Endorsement Number"
- `date_of_issue`: "Date of Issue"
- `effective_date_time`: "Endorsement Effective Date & Time"
- `request_date`: "Endorsement Request date"
- `policy_number`: "Policy No"
- `policy_holder_name`: "Name of Policy Holder"
- `address`: "Address"
- `policy_holder_gstin`: "Policy Holder GSTIN"
- `period_from`: "Period of Insurance - From"
- `period_to`: "Period of Insurance - To"

**Example Output Structure:**
```json
{
  "endorsement_number": "Example-123",
  "date_of_issue": "DD/MM/YYYY",
  "effective_date_time": "YYYY-MM-DD HH:MM:SS",
  "request_date": "DD/MM/YYYY",
  "policy_number": "000-000",
  "policy_holder_name": "NAME HERE",
  "address": "Full Address String",
  "policy_holder_gstin": "GSTIN123",
  "period_from": "DD/MM/YYYY",
  "period_to": "DD/MM/YYYY"
}
```
""".strip()


# ═══════════════════════════════════════════════════════════
#  System Prompt
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT = """
You are a structured data extraction assistant for ABHI (Aditya Birla Health Insurance) 
endorsement documents. You always respond with valid JSON. 
You never add explanations, markdown formatting, or code blocks — just pure JSON.
""".strip()
