# 📄 DOCUMENTATION.md

## CreditSeer — Documentation

---

## Overview

CreditSeer is a step-driven application that ingests **credit agreement PDFs** and extracts structured legal and financial terms using a **two-stage, schema-driven LLM architecture**.

The system is designed to:

* minimize hallucination,
* reduce cross-term contamination,
* surface uncertainty through confidence signals,
* and allow users to inspect outputs at every stage before proceeding.

This application prioritizes **analyst trust, debuggability, and transparency** over automation.

---

## High-Level System Flow

The application progresses through **explicit, user-controlled stages**.

1. Upload PDF
2. Process PDF → extracted text
3. Chunk document into legal articles
4. Classify chunks and map schemas
5. Stage 1 extraction (block discovery)
6. Stage 2 extraction (value extraction + confidence)

Each stage:

* is triggered by a user action,
* produces visible output,
* must complete before the next stage can run.

---

## Frontend Interaction Model (Required)

The frontend must expose **one button per stage**, and display results before enabling the next step.

---

### 1. Upload PDF

**UI**

* Button: **Upload PDF**

**Behavior**

* User uploads a credit agreement PDF.
* File is stored server-side.

**Output shown**

* File name
* File size
* Upload status

---

### 2. Process PDF

**UI**

* Button: **Process PDF**

**Behavior**

* Convert PDF into structured text.

**PDF processing includes**

* Main text extraction
* Word-level fallback for headers, footers, and page numbers
* Table detection and normalization

**Output shown**

* Extracted text (scrollable)
* Metadata:
  * page count
  * character count
  * number of detected tables

---

### 3. Chunk Document

**UI**

* Button: **Chunk Text**

**Behavior**

* Split extracted text into article-level chunks.

**Output shown**

* List of chunks
* For each chunk:

  * title
  * character length
  * expandable text view

---

## Text Chunking Utilities for Credit Agreements

### Purpose

Credit agreements follow a consistent but non-uniform article structure.
The chunking system must identify legal sections **semantically**, not by section number.

---

### Expected Articles (Typical)

Most agreements include some or all of the following:

1. Definitions
2. Credits (or *The Credits*)
3. Representations and Warranties
4. Conditions (or *Conditions to Credit Extensions*)
5. Affirmative Covenants
6. Negative Covenants
7. Guarantee
8. Events of Default
9. Administrative Agent (or *The Administrative Agent*)
10. Miscellaneous

* sometimes combined with Administrative Agent

Not all articles are guaranteed to exist.

---

### Article Detection Rules

Chunk boundaries are detected using:

First look for "Table of Contents" or "TABLE OF CONTENTS" or "Table\s+of\s+Contents"

#### 1. Section headers

Format 1: "ARTICLE I Definitions 1" - title and page on same line
Format 2: "ARTICLE I" on one line, "DEFINITIONS" on next line(s)

Examples (non-exhaustive):

* `ARTICLE I — DEFINITIONS`
* `ARTICLE VI – NEGATIVE COVENANTS`
* `REPRESENTATIONS AND WARRANTIES`
* `EVENTS OF DEFAULT`

Roman numerals, punctuation, and formatting may vary.

#### 2. Keyword density (secondary signal)

| Article               | Common Signals                       |
| --------------------- | ------------------------------------ |
| Definitions           | `shall mean`, `means`                |
| Credits               | `Loans`, `Commitments`, `Borrowings` |
| Representations       | `represents and warrants`            |
| Conditions            | `conditions precedent`               |
| Affirmative Covenants | `shall`, `shall cause`               |
| Negative Covenants    | `shall not`, `may not`               |
| Guarantee             | `guarantees`, `guarantor`            |
| Events of Default     | `Event of Default`                   |
| Administrative Agent  | `Administrative Agent`               |
| Miscellaneous         | `governing law`, `counterparts`      |

---

### Chunk Normalization

Each detected article becomes a normalized chunk:

```json
{
  "chunkId": "uuid",
  "chunkType": "negative_covenants",
  "title": "ARTICLE VI — NEGATIVE COVENANTS",
  "text": "...",
  "metadata": {
    "charCount": 42133,
    "startPage": 57,
    "endPage": 71
  }
}
```

Missing articles are skipped.
Merged articles are assigned the most appropriate `chunkType`.

---

## Chunk Classification & Schema Mapping

### Supported `chunkType` Values

| chunkType            | Description                       |
| -------------------- | --------------------------------- |
| `cover`              | Title page and agreement preamble |
| `definitions`        | Capitalized term definitions      |
| `representations`    | Representations & Warranties      |
| `negative_covenants` | Negative / financial covenants    |
| `credits`            | Credit facilities and loan terms  |
| `events_of_default` | Events of default and remedies    |
| `other`              | Unused sections                   |

---

### Schema Mapping Rules

Schemas are applied **only** based on `chunkType`.

#### Stage 1 Mapping

| chunkType            | Stage-1 Schema                           |
| -------------------- | ---------------------------------------- |
| `cover`              | `schema/cover.stage1.json`              |
| `definitions`        | `schema/definitions.stage1.json`         |
| `representations`    | `schema/representations.stage1.json`     |
| `negative_covenants` | `schema/negativeCovenants.stage1.json`  |
| `credits`            | `schema/credits.stage1.json`             |
| `events_of_default`  | `schema/eventsOfDefault.stage1.json`     |
| `other`              | none                                     |

#### Stage 2 Mapping

| chunkType            | Stage-2 Schema                           | Required |
| -------------------- | ---------------------------------------- | -------- |
| `definitions`        | `schema/definitions.stage2.json`         | Yes      |
| `negative_covenants` | `schema/negativeCovenants.stage2.json`  | Yes      |
| `credits`            | `schema/credits.stage2.json`             | Yes      |
| `events_of_default`  | `schema/eventsOfDefault.stage2.json`     | Yes      |
| `cover`              | none                                     | No       |
| `representations`    | none (for now)                           | No       |
| `other`              | none                                     | No       |

---

## Two-Stage Extraction Architecture

### Stage 1 — Block Discovery

**Purpose**
Identify and isolate legally meaningful blocks.

**Input**

* One chunk
* Corresponding Stage-1 schema

**Behavior**

* Locate each block using anchor patterns and semantic equivalents.
* Extract the **entire verbatim block text**.
* Assign a `valueType` (e.g., `date`, `commitment`, `covenant`).
* Do **not** extract values.

**Output**

```json
{
  "blockId": "revolvingCreditCommitment",
  "valueType": "commitment",
  "text": "Full definition text…"
}
```

---

### Stage 2 — Value Extraction

**Purpose**
Extract structured values from isolated blocks only.

**Input**

* Stage-1 blocks
* Stage-2 schema for the chunk

**Behavior**

* Route extraction by `valueType`.
* Extract values only from the block's text.
* Return `"Not Found"` for missing values.
* **Optimization**: Blocks marked `"Not Found"` in Stage 1 are automatically skipped (no LLM call made).

---

## Value Types

### Definitions

* `date`
* `commitment`
* `rate`
* `margin`

### Negative Covenants

* `covenant`

### Credits

* `fee`
* `interest`
* `interestMechanics`

### Events of Default

* `eventOfDefault`
* `defaultRemedy`

### Representations

* `representation`

---

## Field Types

The system supports the following field types for value extraction and validation:

* `text` - Free-form text (no format validation)
* `quantitative_metric` - Currency, percentages, ratios, basis points, numbers
* `date` - Numeric dates (01/15/2024) and month-style dates (January 15, 2024)
* `location` - Section references (Section 2.01, Schedule 1.2, Exhibit A)
* `duration` - Time periods (5 Business Days, thirty days, one month)
* `boolean` - Yes/No, True/False, Automatic/Discretionary

---

## Confidence Signals

Each extracted value includes deterministic confidence metadata with detailed factor breakdowns.

### Confidence Factors (7-Factor Model)

1. **Value Presence** (0-3 points): Value found or not
2. **Format Validity** (0-2 points): Type-aware regex validation
3. **Evidence Support** (0-2 points): Exact match for numbers; token coverage for text
4. **Completeness** (0-1 point): List count sanity / table rows found
5. **Anchor Proximity** (0-1 point): Distance to schema pattern anchor
6. **Ambiguity Penalty** (-0.5 to 0): Multiple candidates in block
7. **Faithfulness** (0-1 point): For summarized outputs, check against source

### Confidence Levels

* **High** (≥75%): Strong confidence across all factors
* **Medium** (50-74%): Moderate confidence with some uncertainty
* **Low** (<50%): Low confidence, requires review
* **Not Present** (0%): Value not found in block (includes `isMissing: true` flag)

### Display Percentage

* Internal percentage: Uncapped (0-100%)
* Display percentage: Capped at 95% to avoid false certainty
* Ambiguity flags: `ambiguousCandidates`, `multipleMatches`, `anchorNotFound`

---

## Environment Configuration

A `.env` file is required at the project root.

### Example `.env`

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
MAX_CHUNK_CHAR_LIMIT=150000
```

Secrets must never be hardcoded.

---

## Project Structure

```
CreditSeer/
├── app.py
├── routes/
├── pdf_processing/
├── chunking/
├── extraction/
├── schemas/
│   ├── stage1/
│   └── stage2/
└── frontend/
```

---

## LLM Call Optimization

### Call Structure

**Stage 1**: One LLM call per chunk type that has a schema (typically 6 calls)
* `cover`, `definitions`, `representations`, `negative_covenants`, `credits`, `events_of_default`

**Stage 2**: One LLM call per block that was **found** in Stage 1
* Blocks marked `"Not Found"` in Stage 1 are automatically skipped (no LLM call)
* Maximum: ~34 calls if all blocks are found
* Typical: ~17-23 calls (depends on how many blocks are found)

**Total**: ~23-40 LLM calls per document (optimized from 40+ with block skipping)

### Cost Savings

If 50% of blocks are "Not Found":
* Stage 1: 6 calls (unchanged)
* Stage 2: ~17 calls (instead of 34)
* **Savings: ~17 LLM calls per document (~42% reduction)**

---

## Design Principles

* Show every intermediate output
* Never hallucinate
* Isolate text before extracting values
* Surface uncertainty explicitly
* Optimize for analyst trust
* Minimize unnecessary LLM calls (skip missing blocks)


