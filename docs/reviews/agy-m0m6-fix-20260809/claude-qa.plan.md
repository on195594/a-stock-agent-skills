# Claude QA result (isolated plan mode)

Claude exited 0 in the temporary shadow. Because the invocation used
`--permission-mode plan`, the final report was written to the isolated plan
file rather than stdout.

Normalized result: `COMPLIANT`.

Deterministic findings: checks 1-6 and 8-9 PASS; check 7 is SKIP because the
fixture declares a cached dividend path; checks 10-11 are SKIP for A framework.
There are no FAIL findings.

