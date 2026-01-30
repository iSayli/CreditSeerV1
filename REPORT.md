## KirklandandElis1.pdf Pipeline Report

Timestamp (UTC): 2026-01-16T00:45:00.484662Z
Server: http://localhost:5002

### 1) Reset
- Status: success
- Cleanup: Cleaned up 0 file(s)

### 2) Upload
- Status: success
- Filename: KirklandandElis1.pdf
- Size: 2,133,718 bytes

### 3) Process PDF
- Status: success
- Page count: 179
- Table count: 4
- Text length: 537,695 chars

### 4) Chunking
- Status: success
- Chunk count: 11

| chunkId | chunkType | title | charCount |
| --- | --- | --- | --- |
| 14690c65-90b3-4975-9629-5b26b2fc4b29 | cover | Cover Page | 8705 |
| 55c134d5-ae9d-4218-b3cc-e245883fb245 | definitions | DEFINITIONS | 143937 |
| d603bbf1-04ab-4554-8374-77568ba3cff2 | credits | THE CREDITS | 95714 |
| a00e9e84-4b52-4a27-9f10-f28018afc607 | representations | REPRESENTATIONS AND WARRANTIES | 29629 |
| 58ad4bb3-7cc3-49e8-a7fb-5817957bb7e9 | other | CONDITIONS TO CREDIT EXTENSIONS | 8273 |
| 977ed15f-edbe-411e-93fa-554eae683fbc | other | AFFIRMATIVE COVENANTS | 28294 |
| 1ca8dad6-3642-4a82-b98a-834e5c33d566 | negative_covenants | NEGATIVE COVENANTS | 60661 |
| d2e19ca4-77fa-4584-816d-e727d3fae4bc | other | GUARANTEE | 12564 |
| 8c85d8d4-fe0b-440c-a902-c5f7fd2d1ce9 | events_of_default | EVENTS OF DEFAULT | 15473 |
| b2489996-f58c-4b87-83a4-e27987afc36a | other | THE ADMINISTRATIVE AGENT | 15179 |
| 10de9ef7-cdf5-4bce-82de-0de3adc1f86b | other | MISCELLANEOUS | 119254 |

### 5) Stage 1 (Block Discovery)
- Status: success

Sample blocks by chunk:
- Cover (14690c65-90b3-4975-9629-5b26b2fc4b29), blockCount=7
  - agreementTitle (named_entity): "REVOLVING CREDIT AGREEMENT"
  - effectiveDate (date): "August 7, 2013"
  - borrowers (named_entity): "BANKRATE, INC."
- Definitions (55c134d5-ae9d-4218-b3cc-e245883fb245), blockCount=9
  - maturityDate (date): Not Found
  - revolvingMaturityDate (date): "Revolving Maturity Date" shall mean (i) ... May 17, 2018 ...
  - revolvingCreditCommitment (commitment): "Revolving Commitment" shall mean ...
- Credits (d603bbf1-04ab-4554-8374-77568ba3cff2), blockCount=9
  - feesGeneral (valueType empty): Section 2.05 Fees. ...
  - commitmentFee (fee): (a) Commitment Fee. Borrower agrees to pay ...
  - administrativeAgentFees (fee): (b) Administrative Agent Fees. ...
- Negative Covenants (1ca8dad6-3642-4a82-b98a-834e5c33d566), blockCount=5
  - totalLeverageRatio (covenant): Not Found
  - interestCoverageRatio (covenant): Not Found
  - fixedChargeCoverageRatio (covenant): Incur any Indebtedness ... (truncated)
- Events of Default (8c85d8d4-fe0b-440c-a902-c5f7fd2d1ce9), blockCount=11
  - paymentDefaultPrincipal (eventOfDefault): (a) default shall be made in the payment of any principal ...
  - paymentDefaultInterest (eventOfDefault): (b) default shall be made in the payment of any interest ...
  - misrepresentationDefault (eventOfDefault): (c) any representation or warranty made ...
- Representations (a00e9e84-4b52-4a27-9f10-f28018afc607), blockCount=1
  - useOfProceeds (representation): Section 3.11 Use of Proceeds. Borrower will use the proceeds ...

### 6) Stage 2 (Value Extraction)
- Status: success

Sample extractions by chunk:
- Cover (agreementTitle, effectiveDate, borrowers)
  - agreementTitle: "REVOLVING CREDIT AGREEMENT"
  - effectiveDate: "August 7, 2013"
  - borrowers: "BANKRATE, INC."
- Definitions
  - revolvingMaturityDate: ["May 17, 2018", "final maturity date as specified ..."]
  - revolvingCreditCommitment:
    - commitmentAmount: "$70.0 million"
    - referenceSections: ["Appendix A", "Section 2.07", "Section 10.04"]
- Credits
  - commitmentFee:
    - feeRate: "Applicable Fee"
    - feeBase: "average daily unused amount"
    - accrualPeriod: "commencing on the first such date ..."
    - paymentTiming: ["payable in arrears", "on the last Business Day of March, June, September and December of each year", "on the date on which such Revolving Commitment terminates"]
  - administrativeAgentFees: mostly Not Found / empty values
- Events of Default
  - paymentDefaultPrincipal:
    - affectedObligation: "default in the payment of any principal of any Loan or any Reimbursement Obligation"
    - gracePeriod: []
  - paymentDefaultInterest:
    - affectedObligation: "payment of any interest on any Loan or any Fee or any other amount due ..."
    - gracePeriod: ["five Business Days"]
- Negative Covenants
  - fixedChargeCoverageRatio:
    - thresholdValues: ["2.00 to 1.00"]
    - operator/applicabilityCondition extracted (non-empty)

### 7) Highlight Verification (Stage 1 block text vs chunk text)
Automated check: stage1 block text (normalized) found within the associated chunk text.
- Blocks checked: 25
- Found in chunk: 19
- Not found: 6 (all correspond to Stage 1 "Not Found" blocks like `totalLeverageRatio`, `interestCoverageRatio`, `maturityDate`)

Sample checks:
- agreementTitle (cover): found=true, blockLength=27, chunkLength=8705
- revolvingMaturityDate (definitions): found=true, blockLength=~200, chunkLength=143937
- fixedChargeCoverageRatio (negative_covenants): found=true, blockLength=739, chunkLength=60661

### 8) UI Highlight Behavior
Manual UI clicks were not performed in this run (API-only verification). If you want, I can open the UI and click a set of values to confirm visual highlight alignment.
