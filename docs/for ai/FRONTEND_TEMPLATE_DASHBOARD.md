# Frontend Template - Dashboard HTML Reference for AI

This document describes the structure and intent of templates/dashboard.html.

## templates/dashboard.html

- Purpose: Provide a responsive dashboard UI for wallet/portfolio visualization.

### Head Section
- Includes meta tags for responsiveness and theme color.
- Title: Wallex Wallet Dashboard
- External libraries:
  - Chart.js via CDN for data visualization
- Styles:
  - Embedded CSS defining layout, color palette (dark theme), card components, grids, and responsiveness.

### Body Structure
- Header:
  - App title and navigation links (Dashboard, Portfolio, Settings)
- Main:
  - Grid layout with cards for key metrics (Total Value, 24h Change, Invested, P/L)
  - Sections for charts:
    - Portfolio Value Over Time (line chart)
    - Asset Allocation (doughnut chart)
    - 24h Movers (bar chart)
  - Each chart section includes controls (e.g., timeframe selectors) and a legend area

### Scripts
- Initializes Chart.js instances for each chart placeholder
- Fetch logic (to be implemented) to pull data from `/api/balances` and other endpoints
- Utility functions for formatting numbers and dates

### Extension Ideas
- Add loading spinners and error placeholders
- Implement dark/light theme toggle
- Add tooltips and drill-down interactions
- Wire charts to live data via WebSocket for real-time updates

Notes for AI
- Keep class names and IDs consistent if you extend JS logic to avoid breaking CSS/JS selectors.
- Prefer updating existing components over adding new ones unless necessary for new features.