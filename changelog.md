## 1.1.5
- Guard: validate_batch short-circuits on empty list before API call
- Fix: agent_id type checked before URL interpolation — prevents mock objects reaching production endpoints
- Hardening: test suite env guard raises if AZTP_API_URL points to production
