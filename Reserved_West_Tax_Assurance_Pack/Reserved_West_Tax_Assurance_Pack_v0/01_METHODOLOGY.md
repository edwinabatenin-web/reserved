# Methodology v0.2

Reserved West uses Progressive Assurance.

The purpose is to maximise understanding of engine behaviour, not maximise test count.

Scenario groups:
- Representative
- Boundary
- Interaction
- Tolerance

Testing process:
1. Verify canonical engine.
2. Build independent reference calculator.
3. Design informative scenarios.
4. Execute progressively.
5. Analyse root causes.
6. Fix.
7. Add permanent regression scenarios.
8. Repeat.

Scenario generation continues only while new scenarios exercise materially different calculation pathways or interactions.

Systemic Critical defects pause later stages. Isolated defects are investigated without unnecessarily stopping the programme.
