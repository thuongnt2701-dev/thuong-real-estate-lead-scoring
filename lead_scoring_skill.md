# Skill: Lead Scoring for Real Estate Industry

## 1. Overview
This skill is designed to automatically evaluate and score potential customers (leads) in the real estate sector based on their described needs. The goal is to prioritize high-value leads and filter out low-quality or "junk" data.

## 2. Input Data Structure
The input data typically comes from a Google Sheet with the following columns:
- `id`: Unique identifier for the lead.
- `ten_khach`: Customer's full name.
- `sdt`: Phone number.
- `nhu_cau_mo_ta`: Detailed description of the customer's requirements, situation, or status. **(Primary column for analysis)**.

## 3. Scoring Rules

### A. VIP / High Potential (+50 Points)
Identify these leads based on the following keywords and context in `nhu_cau_mo_ta`:
- **High Budget**: Specific amounts from 20 billion VND upwards, or phrases like "strong finance", "budget is not an issue".
- **Luxury Property Types**: "Single villas" (Biệt thự đơn lập), "Penthouse", "Large shophouses on main roads", "Industrial land funds", "Large office floors".
- **Prime Locations**: High-demand areas such as "District 1", "Riverside", "Vinhomes Ocean Park", "Phú Mỹ Hưng".
- **Professional Profiles**: "Business owner", "Professional investor", "Wholesale buyer", "Bulk purchase".
- **Urgency & Transparency**: Requests for "100% legal clarity", "Individual pink book (Sổ hồng riêng)", "Wants to meet the developer directly for negotiation".

### B. Junk / Low Potential (-50 Points)
Identify these leads based on negative indicators in `nhu_cau_mo_ta`:
- **Unrealistic Requests**: Buying property at prices significantly below market value (e.g., District 1 house for 1-2 billion VND, central house with garden/pool for a few hundred million).
- **No Real Demand**: "Wrong number", "No demand", "Old data", "Wrong industry".
- **Uncooperative/Lack of Interest**: "Asking for fun", "No intention to buy yet", "Uncooperative attitude".
- **Spam/Advertising**: Content offering other services like "Insurance", "Bank loans (unrelated to property purchase)", "Service invitations".
- **Communication Issues**: "Subscriber unavailable", "Called many times no answer", "No Zalo response".

### C. Normal / Potential (Base Score: 0 or +10 Points)
Leads that do not fall into the above categories but show genuine interest:
- Seeking apartments or townhouses in the mid-range (3-10 billion VND).
- Requesting bank loans or considering payment policies.
- Has real needs but requires more consultation on legalities or location.

## 4. Processing Instructions
1. **Analyze Content**: Read the `nhu_cau_mo_ta` field carefully.
2. **Identify Keywords**: Look for keywords matching the criteria in Section 3.
3. **Calculate Score**:
    - Start with a base score of 0.
    - Add 50 if it meets VIP criteria.
    - Subtract 50 if it meets Junk criteria.
    - Stay at 0 or add a small bonus (e.g., +10) if it's a standard valid lead.
4. **Classification**:
    - **Score >= 50**: HOT (Priority)
    - **Score 0 to 40**: WARM (Consultation needed)
    - **Score < 0**: COLD/JUNK (Discard)

## 5. Output Format
For each lead, provide:
- `id`: From input.
- `score`: Total calculated score.
- `classification`: HOT, WARM, or JUNK.
- `reason`: A brief explanation of why this score was given (e.g., "High budget, luxury segment" or "Wrong number").
