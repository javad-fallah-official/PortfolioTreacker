# Portfolio Tracker Documentation

Welcome to the comprehensive documentation for the Portfolio Tracker project - a sophisticated cryptocurrency portfolio tracking system built around the Wallex exchange API.

## 📚 Documentation Structure

This documentation is organized into five main categories for easy navigation:

### 🚀 [01 - Getting Started](./01-getting-started/)
Essential documentation for new users and developers getting started with the project.

- **[Project Overview](./01-getting-started/project-overview.md)** - Complete project architecture and feature overview
- **[Examples and Usage](./01-getting-started/examples-and-usage.md)** - Practical examples and usage patterns

### 📖 [02 - API Reference](./02-api-reference/)
Comprehensive API documentation for all components and modules.

- **[API Documentation](./02-api-reference/api.md)** - General API documentation
- **[Wallex Package](./02-api-reference/wallex-package.md)** - Core Wallex library documentation
- **[REST Client](./02-api-reference/wallex-rest-client.md)** - REST API client reference
- **[WebSocket Client](./02-api-reference/wallex-websocket-client.md)** - WebSocket client reference
- **[Types & Utils](./02-api-reference/wallex-types-utils.md)** - Type definitions and utility functions

### 🛠️ [03 - Development](./03-development/)
Documentation for contributors and developers working on the project.

- **[Contributing Guide](./03-development/contributing.md)** - Main contribution guidelines
- **[Contributing Guide (Extended)](./03-development/contributing-guide.md)** - Additional contribution information

### 🔧 [04 - Technical Details](./04-technical-details/)
In-depth technical documentation for system architecture and implementation.

- **[Database Layer](./04-technical-details/database-layer.md)** - Database schema and operations
- **[Web UI Layer](./04-technical-details/web-ui-layer.md)** - Web interface implementation
- **[Frontend Template Dashboard](./04-technical-details/frontend-template-dashboard.md)** - Frontend template structure

### 📋 [05 - Project Information](./05-project-info/)
Project metadata, history, and administrative information.

- **[Changelog](./05-project-info/changelog.md)** - Version history and changes
- **[Project Summary](./05-project-info/project-summary.md)** - High-level project summary
- **[Project Completion](./05-project-info/project-completion.md)** - Project completion status
- **[Modular Library Summary](./05-project-info/modular-library-summary.md)** - Library structure overview

## 🏗️ Project Architecture

The Portfolio Tracker is built with a modular architecture consisting of:

- **Wallex Python Library** - Core API client with REST and WebSocket support
- **Database Layer** - SQLite-based portfolio snapshot storage
- **Web Dashboard** - FastAPI-based web interface
- **Frontend** - Responsive HTML dashboard with Chart.js integration

## 🚀 Quick Start

1. **New Users**: Start with [Project Overview](./01-getting-started/project-overview.md)
2. **Developers**: Check [Examples and Usage](./01-getting-started/examples-and-usage.md)
3. **Contributors**: Read [Contributing Guide](./03-development/contributing.md)
4. **API Users**: Browse [API Reference](./02-api-reference/)

## 🔍 Key Features

- **Modular Design** - Use only the components you need
- **Real-time Data** - WebSocket support for live market data
- **Historical Tracking** - SQLite database for portfolio history
- **Web Dashboard** - Beautiful, responsive web interface
- **Comprehensive Testing** - Extensive test coverage
- **Type Safety** - Strong typing throughout with TypedDict

## 📞 Support

For questions, issues, or contributions, please refer to the appropriate documentation section or check the [Contributing Guide](./03-development/contributing.md).

---

*Last updated: January 2025*