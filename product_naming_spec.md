# Product Naming Specification (v1.0)

## Core Format Rule

All product strings must follow this structure:

[COLLECTION] [PRODUCT TYPE] [OPTIONAL STYLE/DETAILS]  
- SIZE INFO (always after "-")  
- VARIANT (always after "/")  

---

## Purpose

This format is required to ensure:
- consistent parsing in automated systems
- reliable category detection
- accurate size/variant extraction
- elimination of ambiguity in product names
- reduction of manual correction workload

---

## REQUIRED STRUCTURE BREAKDOWN

### 1. Product Header (before "-")

Contains:
- collection name
- product type
- optional descriptive modifiers

### 2. Size Block (after "-")

Must always follow:

- SIZE (AGE)MEASUREMENT"

Example:
- 6 (18m)5.5"

### 3. Variant Block (after "/")

Represents **customer-selected option only**:

Example:
- Sable dark brown

---

# CATEGORY EXAMPLES (CURRENT → PROPOSED)

---

## 1. LOAFERS

### Current
Latte, Saddle, Sable Leather LOAFERS Shoes Baby and Toddler - 6 (18m)5.5" / Sable dark brown

### Proposed
Sable Leather Loafers - 6 (18m)5.5" / Sable dark brown

---

## 2. RAINEY JANES

### Current
Caramel RAINEY JANES Shoes Baby and Toddler - 5 (15m)5.25"

### Proposed
Caramel Rainey Janes - 5 (15m)5.25"

---

## 3. BELLA JANES

### Current
Dusty Rose & Oyster BELLA JANES Shoes Baby and Toddler - 7 (24m)5.75" / Dusty Rose

### Proposed
Dusty Rose Bella Janes - 7 (24m)5.75" / Dusty Rose

---

## 4. SEQ / SUN (SEQUOIA + SUNRISE)

### SEQUOIA

#### Current
Sable & Sepia SEQUOIA Shoes Baby and Toddler - 8 (2yr)6" / Sepia

#### Proposed
Sepia Sequoia - 8 (2yr)6" / Sepia

---

### SUNRISE

#### Current
Rust & Wood SUNRISE Shoes Baby and Toddler - 7 (24m)5.75" / Wood

#### Proposed
Rust Sunrise - 7 (24m)5.75" / Wood

---

## 5. DAISY

### Current
Sepia, Caramel DAISY SANDALS Shoes Baby and Toddler - 5 (15m)5.25" / Caramel

### Proposed
Caramel Daisy Sandals - 5 (15m)5.25" / Caramel

---

## 6. MOCCS

### Current
Big Sky Blue Leather Moccs Shoes Baby and Toddler - 4 (12m)5"

### Proposed
Big Sky Moccs - 4 (12m)5"

---

## 7. TWO TONE

### Current
Chestnut/Tumbleweed Two Tone Loafer Baby and Toddler Shoes - 7 (24m)5.75"

### Proposed
Chestnut Tumbleweed Two Tone Loafers - 7 (24m)5.75"

---

## 8. DESIGN & CRITTERS

### Current
Russet Bear // Cute Critters Leather Shoes Baby and Toddler - 0 (NB-3m)4"

### Proposed
Russet Bear Critters - 0 (NB-3m)4"

---

## 9. SCOUT

### Current
Sepia, Chai, Caramel SCOUT BOOTIES Baby and Toddler - 6 (18m)5.5" / Sepia

### Proposed
Sepia Scout Booties - 6 (18m)5.5" / Sepia

---

## 10. T-STRAP

### Current
Honey T-Strap Shoes Baby and Toddler - 5 (15m)5.25"

### Proposed
Honey T-Strap - 5 (15m)5.25"

---

## 11. LOTUS

### Current
Platinum LOTUS T-Strap Shoes Baby and Toddler - 8 (2yr)6"

### Proposed
Platinum Lotus T-Strap - 8 (2yr)6"

---

# RULES SUMMARY

## DO
- keep size format identical
- keep variant after "/"
- keep product identity in first segment
- remove marketing language ("Baby and Toddler", "Shoes", etc.)

## DO NOT
- embed multiple color lists as primary truth
- mix catalog options with customer selection
- change size formatting across products
- place variant before "-"

---

# SYSTEM IMPACT

Adopting this format enables:
- deterministic parsing (no heuristics needed)
- elimination of most color detection logic
- reliable HTML reporting
- future database migration readiness