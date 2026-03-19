# Compliance Agent — Features

## 1. Chat Q&A Agent (pages/1_agent.py)
- Chat interface with st.chat_message + st.chat_input
- 4 example question buttons in 2 columns shown when chat is empty
- Chat history preserved in st.session_state.chat_history
- Sidebar: cascading jurisdiction selector (state → city dropdowns from DB)
- Sidebar: Clear chat button
- Email alert nudge shown when answer mentions "new law" or "update"
- Sources shown in collapsible st.expander per message, deduplicated by URL

## 2. Lease Compliance Checker (integrated in pages/1_agent.py)
- File uploader for PDF and DOCX inside st.expander
- Triggered when file uploaded + user asks compliance question
- Returns clause-by-clause analysis with: what's wrong, regulation that applies, fix needed, suggested revision
- Overall compliance score + action items list
- Works for any US jurisdiction (no hardcoded cities)
- Rule-based fallback when no LLM API key configured
- Legal disclaimer always shown with result

## 3. Regulation Explorer (pages/2_explorer.py)
- Search box using vector search (semantic)
- Filter by category dropdown
- Filter by state/city dropdown
- Results table: source name, type, category, URL, last checked date
- Clickable URLs to source documents

## 4. Update Log (pages/3_update_log.py)
- "Check for Updates Now" button
- Filter updates by jurisdiction
- Shows: source name, detected date, what changed, affected jurisdictions
- Deduplication: same source+URL shown once (most recent)
- Email notification sent to subscribers on update

## 5. Email Alerts (pages/4_email_alerts.py)
- Subscribe: email + jurisdiction selection
- Unsubscribe: email + jurisdiction
- View subscriptions: enter email to see active subscriptions
- Welcome email on subscribe
- Daily digest emails for subscribed jurisdictions
- Immediate alert on regulation update

## 6. Settings (pages/5_settings.py)
- Load regulations from CSV
- Initialize/rebuild vector index
- Show indexing status per jurisdiction
- API key status display (which keys are configured)
- Manual trigger for scraper

## 7. Rule-Based Fallback Engine (core/compliance/rules.py)
Works without any API key. Detects:
- ESA/service animal fee violations (Fair Housing Act)
- Missing ESA exemption language in pet clauses
- Security deposit return timeline violations (state-specific)
- Unreasonable late fees
- Missing required disclosures
- Rent increase cap violations (checks against jurisdiction rules in DB)

## 8. New Domains (beyond original TX-only)
- Pet laws: ESA rules (federal), breed restrictions (city-level), deposit caps (state-level)
- Rental insurance: landlord-can-require flag, min coverage, proof requirements
- All 50 US states via jurisdiction hierarchy in DB