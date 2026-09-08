# Sample output

Generated 2026-09-08T13:22:31.155076+00:00 from `knowledge.db`.
Regenerate with `python scripts/export_sample.py`.

| Metric | Value |
|---|---|
| Documents | 6 |
| Facts | 423 (326 grounded) |
| Relations: CONTRADICTS | 4 |
| Relations: CORROBORATES | 17 |
| Relations: RECONCILABLE_CONTEXT | 132 |
| Extraction issues | 98 |

## Relations by type

### CORROBORATES (17)

- **A** (02-delhivery-annual-report-fy24-excerpt.pdf p.51): Delhivery Limited was incorporated on June 22, 2011.
  - evidence: "June 22, 2011"
- **B** (01-delhivery-prospectus-2022-excerpt.pdf p.30): Delhivery was originally incorporated as SSN Logistics Private Limited on June 22, 2011.
  - evidence: "Our Company was incorporated as "SSN Logistics Private Limited", a private limited company, under the Companies Act, 1956, pursuant to a certificate of incorporation issued by the RoC on June 22, 2011."
  - **CORROBORATES** (confidence 1.0): Both facts refer to the same event—the incorporation of Delhivery Limited on June 22, 2011. Fact B provides the additional detail that the company was originally named 'SSN Logistics Private Limited' before being renamed to Delhivery. The incorporation date is identical in both facts.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.8): Delhivery had 111 gateways as of Q4 FY24.
  - evidence: "Q4 FY24
Gateways 111"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Delhivery operates 111 gateways across India as of March 31, 2024.
  - evidence: "111 gateways across the India"
  - **CORROBORATES** (confidence 1.0): Both facts report that Delhivery operates 111 gateways at the same time period: Fact A says 'Q4 FY24' and Fact B says 'as of March 31, 2024,' which is the end date of Q4 FY24 in the Indian fiscal calendar. Same entity, metric, value, and time period.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.8): Delhivery had 29 automated sort centers as of Q4 FY24.
  - evidence: "Q4 FY24
Automated sort centers 29"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Delhivery operates 29 fully and semi-automated sortation centres as of March 31, 2024.
  - evidence: "operated 29 fully and semi automated sortation centres"
  - **CORROBORATES** (confidence 0.95): Both facts report 29 automated sort centers at the same time period: Fact A says 'Q4 FY24' and Fact B says 'as of March 31, 2024' (Q4 FY24 ends March 31, 2024). Fact B clarifies these include 'fully and semi-automated' centers, but the count (29) is identical.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.6): Delhivery's revenue from services in FY24 was ₹8,142 Cr
  - evidence: "₹8,142 Cr"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Consolidated revenue from operations for FY24 was ₹81,415.38 million.
  - evidence: "Revenue from Operations ... 81,415.38"
  - **CORROBORATES** (confidence 0.98): Fact A reports ₹8,142 Cr which equals ₹81,420 million, while Fact B reports ₹81,415.38 million—both for FY24. The difference of 4.62 million is only 0.006% and is attributable to rounding.

- **A** (02-delhivery-annual-report-fy24-excerpt.pdf p.51): Delhivery Limited's registered office address is N24-N34, S24-S34, Air Cargo Logistics Centre-II, Opposite Gate 6, Cargo Terminal, IGI Airport, New Delhi 110037.
  - evidence: "N24-N34, S24-S34, Air Cargo Logistics Centre-II, Opposite Gate 6 Cargo Terminal, IGI Airport, New Delhi 110037"
- **B** (01-delhivery-prospectus-2022-excerpt.pdf p.30): Delhivery Limited's registered office is located at N24-N34, S24-S34, Air Cargo Logistics Centre-II, Opposite Gate 6 Cargo Terminal, Indira Gandhi International Airport, New Delhi 110037, Delhi, India.
  - evidence: "N24-N34, S24-S34
Air Cargo Logistics Centre-II
Opposite Gate 6 Cargo Terminal
Indira Gandhi International Airport
New Delhi 110037 Delhi, India"
  - **CORROBORATES** (confidence 0.98): Both facts report the same registered office address: 'N24-N34, S24-S34, Air Cargo Logistics Centre-II, Opposite Gate 6 Cargo Terminal, New Delhi 110037'. Fact A uses 'IGI Airport' while Fact B uses 'Indira Gandhi International Airport', which are the same entity (IGI is the abbreviation). The core address components are identical.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.6): Delhivery's revenue from services grew 12.7% year-over-year from FY23 to FY24
  - evidence: "YoY: 12.7%"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Consolidated revenue from operations grew by 12.68% from FY23 to FY24.
  - evidence: "registering a growth of 12.68%"
  - **CORROBORATES** (confidence 0.95): Both facts report revenue growth from FY23 to FY24: Fact A states 12.7% YoY growth in revenue from services, and Fact B states 12.68% growth in consolidated revenue from operations. The values match within rounding precision (12.7% vs 12.68%).

- **A** (01-delhivery-prospectus-2022-excerpt.pdf p.30): Sahil Barua is Managing Director and Chief Executive Officer of Delhivery Limited.
  - evidence: "Sahil Barua 05131571 House No. 367/4, B5 Plot No., Villa No. 9, Managing Director and Chief Executive Officer"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.24): Sahil Barua is Managing Director and Chief Executive Officer as of March 31, 2024
  - evidence: "Mr. Sahil Barua Managing Director and Chief Executive Officer"
  - **CORROBORATES** (confidence 0.98): Both facts assert that Sahil Barua holds the position of Managing Director and Chief Executive Officer at Delhivery Limited. The titles are identical and refer to the same person in the same role, despite being from documents dated at different times.

- **A** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Delhivery operates a pan-India network providing services in 18,793 postal index codes as of March 31, 2024.
  - evidence: "provides services in 18,793 postal index number ("PIN") codes, as of March 31, 2024"
- **B** (03-delhivery-q4-fy24-earnings-presentation.pdf p.8): Delhivery's pin-code reach was 18,793 as of Q4 FY24.
  - evidence: "Q4 FY24
Pin-code reach(1) 18,793"
  - **CORROBORATES** (confidence 0.99): Both facts report 18,793 PIN codes covered. March 31, 2024 is the end date of Q4 FY24, so these refer to exactly the same time period and value. The metrics 'PIN codes covered' and 'pin-code reach' are equivalent.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.8): Delhivery had 33,278 active customers as of Q4 FY24.
  - evidence: "Q4 FY24
No. of Active Customers(3) 33,278"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Delhivery provided logistics and supply chain solutions to a diverse base of over 33,000 active customers as of March 31, 2024.
  - evidence: "to a diverse base of over 33,000 active customers such as e-commerce marketplaces"
  - **CORROBORATES** (confidence 0.95): Fact A reports exactly 33,278 active customers as of Q4 FY24 (ending March 31, 2024), while Fact B states 'over 33,000' active customers as of March 31, 2024. Same time period, same metric; the second fact is simply a rounded presentation of the precise figure in the first.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.8): Delhivery had 33,278 active customers as of Q4 FY24.
  - evidence: "Q4 FY24
No. of Active Customers(3) 33,278"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.51): Delhivery Limited serves over 33,250 active customers.
  - evidence: "over 33,250 active customers"
  - **CORROBORATES** (confidence 0.95): Both facts report active customers at the end of FY24 (Q4 FY24 ends March 31, 2024). Fact A states exactly 33,278 customers while Fact B states 'over 33,250' customers—the latter is simply a rounded/conservative presentation of the same 33,278 figure.

- **A** (02-delhivery-annual-report-fy24-excerpt.pdf p.24): Deepak Kapoor is Chairperson and Non-Executive Independent Director as of March 31, 2024
  - evidence: "Mr. Deepak Kapoor Chairperson and Non-Executive Independent Director"
- **B** (01-delhivery-prospectus-2022-excerpt.pdf p.30): Deepak Kapoor is Chairman and Non-Executive Independent Director of Delhivery Limited.
  - evidence: "Deepak Kapoor 00162957 K-42, NDSE-2, Andrewsganj S.O., South Delhi, Chairman and Non-Executive Independent Director"
  - **CORROBORATES** (confidence 0.95): Both facts describe Deepak Kapoor holding the same leadership position at Delhivery. Fact A uses 'Chairperson' (March 31, 2024) and Fact B uses 'Chairman' (Prospectus date), but both designate him as Non-Executive Independent Director in the chair role—terminology variance for the same position.

- **A** (01-india-economic-survey-2024-25-excerpt.pdf p.4): India's real GDP is estimated to grow by 6.4 per cent in FY25
  - evidence: "India's real GDP is estimated to grow by 6.4 per cent in FY25."
- **B** (02-rbi-annual-report-2024-25-excerpt.pdf p.24): GDP real growth in India was 6.5 per cent in 2024-25
  - evidence: "6.5"
  - **CORROBORATES** (confidence 0.85): Both facts report India's real GDP growth for the same period - FY25 and 2024-25 refer to the same fiscal year. The values are nearly identical: 6.4% versus 6.5%, a 0.1 percentage point difference likely attributable to rounding, preliminary versus revised estimates, or different data releases.

_(5 more in `relations.json`)_

### CONTRADICTS (4)

- **A** (01-delhivery-prospectus-2022-excerpt.pdf p.30): Delhivery Limited's corporate office is located at Plot 5, Sector 44, Gurugram 122002, Haryana, India.
  - evidence: "Plot 5, Sector 44
Gurugram 122002
Haryana, India"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.51): Delhivery Limited's corporate address is Plot No. 5, Sector 44, Gurugram, Haryana 122001.
  - evidence: "Plot No. 5, Sector 44, Gurugram, Haryana 122001"
  - **CONTRADICTS** (confidence 0.85): Both facts describe the corporate office/address at Plot 5, Sector 44, Gurugram, Haryana, but Fact A gives the PIN code as 122002 while Fact B gives it as 122001. The location details are otherwise identical, making the differing postal codes a material contradiction.

- **A** (02-delhivery-annual-report-fy24-excerpt.pdf p.51): Delhivery Limited's registered office address is N24-N34, S24-S34, Air Cargo Logistics Centre-II, Opposite Gate 6, Cargo Terminal, IGI Airport, New Delhi 110037.
  - evidence: "N24-N34, S24-S34, Air Cargo Logistics Centre-II, Opposite Gate 6 Cargo Terminal, IGI Airport, New Delhi 110037"
- **B** (01-delhivery-prospectus-2022-excerpt.pdf p.1): Delhivery Limited's registered office is at N24-N34, S24-S34, Plot 5, Sector 44, Gurugram 122002, Haryana, India.
  - evidence: "N24-N34, S24-S34, Plot 5, Sector 44, Gurugram 122002 Haryan a, India"
  - **CONTRADICTS** (confidence 0.95): Fact A states the registered office is at 'Air Cargo Logistics Centre-II, Opposite Gate 6 Cargo Terminal, IGI Airport, New Delhi 110037', while Fact B states it is at 'Plot 5, Sector 44, Gurugram 122002, Haryana'. These are materially different locations (New Delhi airport vs. Gurugram) with no temporal or contextual information to reconcile the discrepancy.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.8): Delhivery had 30 automated sort centers as of Q3 FY24.
  - evidence: "Q3 FY24
Automated sort centers 30"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Delhivery operates 29 fully and semi-automated sortation centres as of March 31, 2024.
  - evidence: "operated 29 fully and semi automated sortation centres"
  - **CONTRADICTS** (confidence 0.8): Fact A reports 30 automated sort centers in Q3 FY24, while Fact B reports 29 automated sortation centres as of March 31, 2024 (which would be Q4 FY24, after Q3). The unexplained decrease from 30 to 29 between these sequential periods, with no context provided, represents a material contradiction.

- **A** (03-imf-india-2025-article-iv-excerpt.pdf p.10): India's real GDP grew by 7.8 percent in 2025Q2
  - evidence: "real GDP growth of 7.8 percent in 2025Q2"
- **B** (01-india-economic-survey-2024-25-excerpt.pdf p.20): India's GDP at constant 2011-12 prices grew by 5.4 per cent in Q2 FY25
  - evidence: "India's GDP at constant (2011-12) prices grew by 6.7 per cent and 5.4 per cent in Q1 and Q2 FY25, respectively."
  - **CONTRADICTS** (confidence 0.8): Both facts measure India's real GDP growth at constant prices for Q2 FY25 (2025Q2 = Q2 FY25), but report materially different values: 7.8% (Fact A) vs. 5.4% (Fact B). The 2.4 percentage point gap for the same metric in the same quarter is substantial and unexplained.

### RECONCILABLE_CONTEXT (132)

- **A** (01-delhivery-prospectus-2022-excerpt.pdf p.30): Kapil Bharati is Executive Director and Chief Technology Officer of Delhivery Limited.
  - evidence: "Kapil Bharati 02227607 295 DDA Flats, Gulmohar Enclave, Andrewsganj Executive Director and Chief Technology Officer"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.24): Kapil Bharati is Whole Time Director and Chief Technology Officer as of March 31, 2024
  - evidence: "Mr. Kapil Bharati Whole Time Director and Chief Technology Officer"
  - **RECONCILABLE_CONTEXT** (confidence 0.85): Fact A states Kapil Bharati is 'Executive Director and Chief Technology Officer' (as of prospectus date, circa 2022), while Fact B states he is 'Whole Time Director and Chief Technology Officer' (as of March 31, 2024). Both terms refer to an employee-director role in Indian corporate terminology, and both maintain the CTO designation; the terminology difference is explainable by different document conventions or a minor formal designation change over the ~2-year period.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.8): Delhivery's pin-code reach was 18,074 as of Q4 FY22.
  - evidence: "Q4 FY22
Pin-code reach(1) 18,074"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Delhivery operates a pan-India network providing services in 18,793 postal index codes as of March 31, 2024.
  - evidence: "provides services in 18,793 postal index number ("PIN") codes, as of March 31, 2024"
  - **RECONCILABLE_CONTEXT** (confidence 0.95): Both facts measure Delhivery's pin-code/PIN code reach, but at different times: Fact A reports 18,074 as of Q4 FY22, while Fact B reports 18,793 as of March 31, 2024. The increase of 719 PIN codes over approximately two years reflects network expansion.

- **A** (01-delhivery-prospectus-2022-excerpt.pdf p.30): Donald Francis Colleran is Non-Executive Nominee Director of Delhivery Limited.
  - evidence: "Donald Francis Colleran(1) 09431299 1895 Hazelton Dr, Germantown, TN 38138-2658 Non-Executive Nominee Director"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.24): Donald Francis Colleran, Non-Executive Director, ceased to be a Director at the conclusion of the 12th AGM on September 27, 2023, as he was liable to retire by rotation and not proposed for re-election due to unwillingness
  - evidence: "Mr. Donald Francis Colleran, Non-Executive Director (DIN: 09431299), was liable to retire by rotation at the 12th AGM, and not proposed for re-election due to his unwillingness. Therefore, Mr. Donald Francis Colleran ceased to be a Director at the conclusion of the 12th AGM i.e., September 27, 2023."
  - **RECONCILABLE_CONTEXT** (confidence 0.98): Fact A states Donald Francis Colleran was a Non-Executive Nominee Director as of the Prospectus date, while Fact B reports he ceased to be a Director on September 27, 2023. This reflects a legitimate change in status over time.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.8): Delhivery had 123 gateways as of Q4 FY22.
  - evidence: "Q4 FY22
Gateways 123"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Delhivery operates 111 gateways across India as of March 31, 2024.
  - evidence: "111 gateways across the India"
  - **RECONCILABLE_CONTEXT** (confidence 0.85): Both facts measure the number of gateways, but at different times: Fact A reports 123 as of Q4 FY22, while Fact B reports 111 as of March 31, 2024. The decrease of 12 gateways over approximately two years likely reflects network consolidation or optimization.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.8): Delhivery's pin-code reach was 18,540 as of Q4 FY23.
  - evidence: "Q4 FY23
Pin-code reach(1) 18,540"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Delhivery operates a pan-India network providing services in 18,793 postal index codes as of March 31, 2024.
  - evidence: "provides services in 18,793 postal index number ("PIN") codes, as of March 31, 2024"
  - **RECONCILABLE_CONTEXT** (confidence 0.95): Both facts measure pin-code reach, but at different times: Fact A reports 18,540 as of Q4 FY23, while Fact B reports 18,793 as of March 31, 2024. The increase of 253 PIN codes over approximately one year reflects continued network expansion.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.6): Delhivery's revenue from services in FY24 was ₹8,142 Cr
  - evidence: "₹8,142 Cr"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Standalone revenue from operations for FY24 was ₹74,540.82 million.
  - evidence: "Revenue from Operations 74,540.82"
  - **RECONCILABLE_CONTEXT** (confidence 0.85): Fact A reports ₹8,142 Cr (₹81,420 million) in FY24, while Fact B reports ₹74,540.82 million for FY24. The difference (~6,879 million) is explainable by scope: Fact B is explicitly 'standalone' while Fact A may be consolidated, or they may represent different revenue categories (services vs. operations).

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.6): Delhivery's revenue from services in FY24 was ₹8,142 Cr
  - evidence: "₹8,142 Cr"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Consolidated revenue from operations for FY23 was ₹72,253.01 million.
  - evidence: "72,253.01"
  - **RECONCILABLE_CONTEXT** (confidence 0.95): Fact A reports ₹8,142 Cr (₹81,420 million) for FY24, while Fact B reports ₹72,253.01 million for FY23. The values differ because they are from different fiscal years (FY24 vs. FY23).

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.6): Delhivery's revenue from services in FY24 was ₹8,142 Cr
  - evidence: "₹8,142 Cr"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Standalone revenue from operations for FY23 was ₹66,586.61 million.
  - evidence: "66,586.61"
  - **RECONCILABLE_CONTEXT** (confidence 0.95): Fact A reports ₹8,142 Cr (₹81,420 million) for FY24, while Fact B reports ₹66,586.61 million for FY23. The values differ due to different time periods (FY24 vs. FY23) and potentially different scope (standalone vs. possibly consolidated).

- **A** (02-delhivery-annual-report-fy24-excerpt.pdf p.51): Delhivery Limited's registered office address is N24-N34, S24-S34, Air Cargo Logistics Centre-II, Opposite Gate 6, Cargo Terminal, IGI Airport, New Delhi 110037.
  - evidence: "N24-N34, S24-S34, Air Cargo Logistics Centre-II, Opposite Gate 6 Cargo Terminal, IGI Airport, New Delhi 110037"
- **B** (01-delhivery-prospectus-2022-excerpt.pdf p.1): Delhivery Limited's corporate contact office is at Air Cargo Logistics Centre-II, Opposite Gate 6 Cargo Terminal, Indira Gandhi International Airport, New Delhi 110037.
  - evidence: "Air Cargo Logistics Centre-II, Opposite Gate 6 Cargo Terminal, Indira Gandhi International Airport, New Delhi 110037"
  - **RECONCILABLE_CONTEXT** (confidence 0.85): Fact A refers to the 'registered office address' while Fact B refers to the 'corporate contact office address'. Both are at the same facility (Air Cargo Logistics Centre-II at IGI Airport), but they describe different types of offices serving different legal/operational purposes, which explains the slight difference in the address details provided.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.8): Delhivery had 24 automated sort centers as of Q4 FY23.
  - evidence: "Q4 FY23
Automated sort centers 24"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Delhivery operates 29 fully and semi-automated sortation centres as of March 31, 2024.
  - evidence: "operated 29 fully and semi automated sortation centres"
  - **RECONCILABLE_CONTEXT** (confidence 0.95): Fact A reports 24 automated sort centers as of Q4 FY23, while Fact B reports 29 fully and semi-automated sortation centres as of March 31, 2024. The increase from 24 to 29 is explained by the later time period (approximately one year later), reflecting network expansion.

- **A** (03-delhivery-q4-fy24-earnings-presentation.pdf p.6): Delhivery's revenue from services grew 12.7% year-over-year from FY23 to FY24
  - evidence: "YoY: 12.7%"
- **B** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Standalone revenue from operations grew by 11.95% from FY23 to FY24.
  - evidence: "registering a growth of 11.95%"
  - **RECONCILABLE_CONTEXT** (confidence 0.9): Both report revenue growth from FY23 to FY24, but with different values: 12.7% (Fact A, implied consolidated) vs 11.95% (Fact B, explicitly standalone). The difference is explained by scope—consolidated operations grew faster than standalone operations alone.

- **A** (02-delhivery-annual-report-fy24-excerpt.pdf p.22): Delhivery operates 29 fully and semi-automated sortation centres as of March 31, 2024.
  - evidence: "operated 29 fully and semi automated sortation centres"
- **B** (03-delhivery-q4-fy24-earnings-presentation.pdf p.8): Delhivery had 21 automated sort centers as of Q4 FY22.
  - evidence: "Q4 FY22
Automated sort centers 21"
  - **RECONCILABLE_CONTEXT** (confidence 0.92): Fact A reports 29 automated sortation centres as of March 31, 2024 (end of FY24), while Fact B reports 21 as of Q4 FY22 (approximately 2 years earlier). The increase from 21 to 29 over this period reflects infrastructure expansion over time.

_(120 more in `relations.json`)_
