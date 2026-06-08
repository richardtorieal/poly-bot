# Poly-Bot Development Mandates

## Branching & Safety
- **FEATURE BRANCHING IS MANDATORY:** Never make code changes directly to the `main` branch. 
- **Workflow:** 
  1. Create a fresh feature branch from `main` (e.g., `feature/optimization-YYYYMMDD`).
  2. Implement and test changes on the feature branch.
  3. Validate performance using `validate_loop.py` (ensure Out-of-Sample Sharpe improves).
  4. Merge into `main` ONLY after successful validation.
- **Goal:** Protect the production environment and the `poly-bot-paper` process from unstable or unverified code.

## Autonomous Optimization
- The recurring optimization job MUST create a new branch for every experiment.
- If an experiment fails validation, the branch must be deleted and `main` must remain untouched.
