# Conditions and Extraction

## Rules
1. **Extract Complex Conditions:** Never write inline compound expressions with multiple logical operators. Extract to a named boolean variable.
2. **Positive Framing:** Always frame boolean variables positively (e.g. `is_valid` instead of `is_not_invalid`).
3. **Guard Clauses:** Prefer early returns with guard clauses over deep `if/else` nesting.
