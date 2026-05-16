# Pending Improvements

This document tracks future enhancements and features to be implemented once the core Shopping Agent application is fully stable.

## 1. Advanced Product Filtering [COMPLETED]
The system now intelligently filters out sponsored products from the search results to ensure only authentic, organic listings are evaluated. 

## 2. Smart Product Selection [COMPLETED]
The scraper now looks at the top 10 organic products and dynamically selects the top 3 with the maximum number of reviews to ensure the AI has the most reliable data.

## 3. WhatsApp Integration
Implement a bridge (e.g., via Twilio or a WhatsApp Business API webhook) to allow users to invoke the Shopping Agent directly by sending a WhatsApp message with their search query.

## 4. Standalone Mobile-Friendly Results Page
Since the results are already being rendered as a full, standalone HTML page (`results.html`), we can host the backend as a public-facing web service (e.g., via Vercel or a dedicated server). This way, when a user submits a query via WhatsApp, the Agent can reply with a direct link to the hosted results matrix, allowing the user to view the beautifully formatted comparisons right on their phone browser.
