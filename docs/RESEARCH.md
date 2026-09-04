# Research notes and scope decisions

## Problem framing

SIH26032 describes farmers facing long waits, insufficient procurement-schedule information, and uncertainty about procurement status. The MVP therefore concentrates on three measurable outcomes:

1. A farmer can determine whether a procurement window is suitable before travelling.
2. A centre cannot accept more active tokens than its configured capacity.
3. Farmers can see queue progress and receive a notification whenever their status changes.

## Official workflow references

The official e-NAM farmer guidance says registration can happen through the portal, mobile app, or mandi; it lists identity and bank information among registration details and says digital arrival records receive unique lot IDs that can be tracked. This supports the MVP's farmer profile, eligibility declarations, unique tokens, and status history.

- e-NAM farmers: https://enam.gov.in/web/stakeholders-Involved/farmers
- e-NAM registration: https://enam.gov.in/web/Enam_ctrl/enam_registration
- e-NAM integration scope and process flow: https://enam.gov.in/web/assest/download/sul/Application%20Notice-RFQ-Empanelment_of_Service_Providers_for_integration_with_National_Agriculture_Market_eNAM.pdf

The wider e-NAM flow includes gate entry, quality assaying, trading, weighment, invoicing, payment and gate exit. Those stages are intentionally outside this focused MVP. ProcureFlow stops at schedule discovery, preliminary eligibility, token allocation, queue handling and visit completion.

## Gmail SMTP research

Google's current guidance documents `smtp.gmail.com`, port 587 for TLS, and authenticated delivery using the complete email address and an App Password. App Passwords require 2-Step Verification and are not available for every managed or Advanced Protection account.

- Google Workspace SMTP configuration: https://support.google.com/a/answer/176600
- Google Account App Passwords: https://support.google.com/accounts/answer/185833

The application therefore uses STARTTLS on port 587 and reads the account and App Password only from `.env`. When SMTP is disabled or unavailable, notifications remain visible in the in-app message centre so testing is deterministic.

## Production cautions

- Eligibility rules vary by scheme, commodity, state and procurement agency; declarations here are demonstrative until the sponsor supplies authoritative rules.
- Real deployments should verify identity and bank data through approved integrations and consent flows rather than self-declarations.
- Email is useful for confirmations but should not be the sole urgent-notification channel; an approved SMS provider can be added later.
- The local MVP deliberately contains no payments, auctioning, Aadhaar storage or document uploads.

