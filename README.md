# Revenue Recovery 0.4.9.1 — Validation-Ready Candidate

Main changes from 0.4.9:
- blind randomized human ranking before model reveal;
- full ranking capture rather than only move-up/move-down;
- objective-specific economic value (cash, profit, growth) rather than one generic dollar score;
- explanations based on weighted contributions;
- near-tie confidence;
- optional persistent Supabase submission path;
- insert-only RLS schema for reviewers;
- minimal reviewer metadata.

This remains a synthetic-data validation prototype, not a production decision system.


## Final audit corrections
- Database writes use minimal-return inserts to preserve insert-only reviewer permissions.
- Economic-value scaling uses stable synthetic anchors ($5k cash, $5k gross profit, $15k potential revenue) so scores do not change merely because an unrelated extreme opportunity enters the queue. These anchors are experimental, not industry claims.
