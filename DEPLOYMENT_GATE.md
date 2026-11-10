# Revenue Recovery 0.4.9.1 Deployment Gate

## Experimental validity
- [ ] Blind ranking occurs before model reveal.
- [ ] Scenario order is randomized.
- [ ] Human ranking is locked before reveal.
- [ ] Full human and model rankings are stored.
- [ ] Blind and post-model comments are stored separately.

## Model integrity
- [ ] Eligibility filter verified.
- [ ] Objective-specific cash/profit/growth value logic reviewed.
- [ ] Weighted contribution explanation verified.
- [ ] Near-tie confidence verified.
- [ ] Opportunity priority remains separate from action feasibility.
- [ ] Seasonality remains bounded.

## Data/security
- [ ] Dedicated validation table created.
- [ ] RLS enabled.
- [ ] Reviewer roles have INSERT only.
- [ ] SELECT/UPDATE/DELETE denied in tests.
- [ ] Supabase keys stored in Streamlit Secrets, not GitHub.
- [ ] Service-role key is not used in reviewer app.
- [ ] .streamlit/secrets.toml is ignored.

## Research interpretation
- [ ] Early convenience sample treated as qualitative validation only.
- [ ] Agreement is not described as proof of correctness.
- [ ] No causal revenue claim.
- [ ] IRB determination obtained before any academic/generalizable human-subject research if applicable.

Deploy only after every box is checked.


## Final implementation corrections
- [x] Supabase insert requests `returning="minimal"` so INSERT-only RLS does not require SELECT.
- [x] Economic-value scaling uses fixed documented synthetic reference anchors rather than current-queue min/max or percentiles.
- [x] Reference anchors are explicitly labeled experimental and scheduled for empirical replacement later.
