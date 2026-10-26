# qa-pilot's own knowledge domains (2026-10-19)

The independent book review (§4, §7) named the main gaps of the book catalog: security, test-code quality, HTTP API correctness, authentication, test strategy (risk-based, contract testing, testing in production, exploratory) and AI-feature testing. qa-pilot's own rules now cover them.

## How each rule set was built

1. **Author agent.** One per domain. It worked from current open sources, with web research and caps on rule count. Every rule:
   - is paraphrased;
   - has `source.origin` (source, version, section or ID, URL) and `authority`;
   - avoids existing book rules, and refers to an QAC id when it refines or corrects one.
2. **Independent verifier agent.** It opened each cited source and confirmed the section exists and supports the rule. It also checked severity and authority discipline, paraphrase and auditability, and fixed or dropped rules in place.
3. **Main session.** It resolved the overlaps the verifiers reported between domains, validated the files with `render_rules.py`, and promoted them from `drafts/` to `rules/` after the 0.5 TDK eval, so the eval measured phase 1 alone.

| Domain (file) | Drafted | After verification | Fixed | Dropped | Main sources |
|---|---|---|---|---|---|
| web-patterns + web-invariants | 24 | 24 | 14 | 0 | RFC 9110, OWASP, TanStack Query v5 docs, GOV.UK, Nielsen, WCAG, CWE-209 |
| security | 40 | 38 | 24 | 2 | OWASP ASVS 5.0.0, API Top 10 2023, Top 10 2025, WSTG |
| test-code | 31 | 29 | 16 | 2 | Playwright docs, eslint-plugin-playwright/jest/testing-library, Testing Library, xUnit Patterns, tsDetect, SWE at Google, Fowler |
| api-http | 24 | 23 | 9 | 1 | RFC 9110/9457/8259/5789/7396, Zalando RESTful API Guidelines (CC BY 4.0), Spectral |
| test-strategy | 24 | 21 | 7 | 3 | ISTQB CTFL v4.0.1 (section numbers checked against the PDF), SBTM/HTSM, Fowler, Pact, Google SRE |
| auth | 15 | 14 | 6 | 1 | NIST SP 800-63B-4, OWASP ASVS 5.0 V6/V7/V10, OWASP cheat sheets, RFC 9700 |
| ai-systems | 15 | 15 | 6 | 0 | OWASP LLM Top 10 2025, NIST AI 600-1, ISTQB CT-GenAI, vendor eval docs |

**Cross-domain merges:**
- QAP-SEC-038 merged into QAP-API-002;
- QAP-API-007 merged into QAP-WEB-006/011;
- QAP-SEC-003 merged into QAP-WEB-008/SEC-002;
- QAP-AUTHN-009 merged into QAP-WEB-009.

The verification reports are in the session scratchpad (`domains/*-verify.md`). They are not committed, because they quote the sources at length.

## Effect on packs

On the TDK profile (requirements + test-plan targets), the packs grow from about 296 KB to about 350 KB:
- `core` +15 KB;
- `api-data` +36 KB.

Web patterns and invariants are not packed; agents read them from `references/web-patterns.md`. Most test-code rules target `test-code` and only enter packs for test-code audits.

## Known limits

- Some sources could not be opened automatically: satisfice.com, iso.org, EUR-Lex. Those citations rely on the agents' knowledge.
- Book citations (Khorikov, Hendrickson, Crispin & Gregory) are from memory of the books' structure.
- The rules are paraphrases, not substitutes for the standards.
