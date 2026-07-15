# Graph Report - .  (2026-07-15)

## Corpus Check
- Large corpus: 102 files · ~892,025 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 784 nodes · 1371 edges · 58 communities (46 shown, 12 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 254 edges (avg confidence: 0.83)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Account API Services|Account API Services]]
- [[_COMMUNITY_Profile Data Model|Profile Data Model]]
- [[_COMMUNITY_Database Migration Setup|Database Migration Setup]]
- [[_COMMUNITY_Horizon UI Components|Horizon UI Components]]
- [[_COMMUNITY_Project Governance Docs|Project Governance Docs]]
- [[_COMMUNITY_Meridian Review Components|Meridian Review Components]]
- [[_COMMUNITY_Money Date Utilities|Money Date Utilities]]
- [[_COMMUNITY_Frontend Mock Data|Frontend Mock Data]]
- [[_COMMUNITY_FastAPI Application Lifecycle|FastAPI Application Lifecycle]]
- [[_COMMUNITY_Frontend Routing Theme|Frontend Routing Theme]]
- [[_COMMUNITY_TypeScript Configuration|TypeScript Configuration]]
- [[_COMMUNITY_Frontend Dependencies|Frontend Dependencies]]
- [[_COMMUNITY_Meridian Dark Transactions|Meridian Dark Transactions]]
- [[_COMMUNITY_Ledger UI Components|Ledger UI Components]]
- [[_COMMUNITY_Aurora Light Transactions|Aurora Light Transactions]]
- [[_COMMUNITY_Horizon Light Dashboard|Horizon Light Dashboard]]
- [[_COMMUNITY_Ledger Dark Dashboard|Ledger Dark Dashboard]]
- [[_COMMUNITY_Ledger Light Dashboard|Ledger Light Dashboard]]
- [[_COMMUNITY_Ledger Dark Transactions|Ledger Dark Transactions]]
- [[_COMMUNITY_Meridian Dark Dashboard|Meridian Dark Dashboard]]
- [[_COMMUNITY_Meridian Light Dashboard|Meridian Light Dashboard]]
- [[_COMMUNITY_Horizon Dark Dashboard|Horizon Dark Dashboard]]
- [[_COMMUNITY_Horizon Light Transactions|Horizon Light Transactions]]
- [[_COMMUNITY_Light UI Comparison|Light UI Comparison]]
- [[_COMMUNITY_Ledger Light Review|Ledger Light Review]]
- [[_COMMUNITY_Meridian Dark Review|Meridian Dark Review]]
- [[_COMMUNITY_Meridian Light Review|Meridian Light Review]]
- [[_COMMUNITY_Aurora UI Components|Aurora UI Components]]
- [[_COMMUNITY_Aurora Light Dashboard|Aurora Light Dashboard]]
- [[_COMMUNITY_Aurora Dark Review|Aurora Dark Review]]
- [[_COMMUNITY_Aurora Light Review|Aurora Light Review]]
- [[_COMMUNITY_Horizon Dark Review|Horizon Dark Review]]
- [[_COMMUNITY_Horizon Light Review|Horizon Light Review]]
- [[_COMMUNITY_Dark UI Comparison|Dark UI Comparison]]
- [[_COMMUNITY_Ledger Dark Review|Ledger Dark Review]]
- [[_COMMUNITY_Financial Derived Data|Financial Derived Data]]
- [[_COMMUNITY_Aurora Dark Dashboard|Aurora Dark Dashboard]]
- [[_COMMUNITY_Ledger Light Transactions|Ledger Light Transactions]]
- [[_COMMUNITY_Meridian Light Transactions|Meridian Light Transactions]]
- [[_COMMUNITY_Aurora Dark Transactions|Aurora Dark Transactions]]
- [[_COMMUNITY_Horizon Dark Transactions|Horizon Dark Transactions]]
- [[_COMMUNITY_Migration Baseline|Migration Baseline]]
- [[_COMMUNITY_Profile Account Migration|Profile Account Migration]]
- [[_COMMUNITY_Unix Local Launcher|Unix Local Launcher]]
- [[_COMMUNITY_Database Package|Database Package]]
- [[_COMMUNITY_Domain Package|Domain Package]]
- [[_COMMUNITY_API Package|API Package]]
- [[_COMMUNITY_Models Package|Models Package]]
- [[_COMMUNITY_Routers Package|Routers Package]]
- [[_COMMUNITY_Schemas Package|Schemas Package]]
- [[_COMMUNITY_Services Package|Services Package]]
- [[_COMMUNITY_Local Development Stack|Local Development Stack]]
- [[_COMMUNITY_Frontend Design Policy|Frontend Design Policy]]
- [[_COMMUNITY_Category Derivation|Category Derivation]]
- [[_COMMUNITY_API Project Metadata|API Project Metadata]]

## God Nodes (most connected - your core abstractions)
1. `compilerOptions` - 19 edges
2. `ProfileCreate` - 17 edges
3. `create_account()` - 16 edges
4. `create_profile()` - 16 edges
5. `Profile` - 15 edges
6. `update_account()` - 15 edges
7. `Dashboard()` - 15 edges
8. `Dashboard()` - 15 edges
9. `totalSpendingCents()` - 15 edges
10. `formatShortDate()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Profile-Scoped Data Model` --semantically_similar_to--> `Profile Isolation`  [INFERRED] [semantically similar]
  docs/architecture/overview.md → SPENDING_TRACKER_PRODUCT_PLAN.md
- `Exact Money and Spending Semantics` --conceptually_related_to--> `Integer-Cent Money Representation`  [INFERRED]
  SPENDING_TRACKER_PRODUCT_PLAN.md → docs/decisions/0003-money-and-accounting.md
- `Mandatory Workboard Protocol` --references--> `Implementation Workboard`  [EXTRACTED]
  AGENTS.md → docs/implementation-workboard.md
- `Spending Tracker` --references--> `Implementation Workboard`  [EXTRACTED]
  README.md → docs/implementation-workboard.md
- `Profiles and Accounts Vertical Slice` --implements--> `Profile Isolation`  [INFERRED]
  docs/implementation-workboard.md → SPENDING_TRACKER_PRODUCT_PLAN.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Local-First Private Runtime** — readme_local_first_development, docs_architecture_overview_local_first_architecture, scripts_readme_local_stack_launchers [INFERRED 0.95]
- **Profiles and Accounts Delivery Slice** — spending_tracker_product_plan_profile_isolation, spending_tracker_product_plan_archive_first_lifecycle, docs_implementation_workboard_profiles_accounts_vertical_slice [INFERRED 0.95]
- **Statement Parser Trust Framework** — spending_tracker_product_plan_statement_import_pipeline, docs_parser_notes_readme_text_based_pdf_scope, fixtures_statements_readme_statement_fixture_privacy, tests_e2e_readme_end_to_end_scenarios [INFERRED 0.85]
- **Aurora Dashboard Financial Overview** — docs_screenshots_aurora_dashboard_dark_monthly_financial_summary, docs_screenshots_aurora_dashboard_dark_spending_trend_visualization, docs_screenshots_aurora_dashboard_dark_category_breakdown_visualization, docs_screenshots_aurora_dashboard_dark_transaction_activity_panels [EXTRACTED 1.00]
- **Aurora Dashboard Financial Overview** — docs_screenshots_aurora_dashboard_light_financial_kpis, docs_screenshots_aurora_dashboard_light_spending_trend, docs_screenshots_aurora_dashboard_light_category_breakdown, docs_screenshots_aurora_dashboard_light_recent_transactions, docs_screenshots_aurora_dashboard_light_upcoming_recurring, docs_screenshots_aurora_dashboard_light_largest_purchases [EXTRACTED 1.00]
- **Aurora Transaction Categorization Review Workflow** — docs_screenshots_aurora_review_dark_review_progress, docs_screenshots_aurora_review_dark_transaction_under_review, docs_screenshots_aurora_review_dark_category_suggestion, docs_screenshots_aurora_review_dark_category_selection_grid, docs_screenshots_aurora_review_dark_merchant_memory_rule, docs_screenshots_aurora_review_dark_review_actions [EXTRACTED 1.00]
- **Aurora Category Review Workflow** — docs_screenshots_aurora_review_light_transaction_review_card, docs_screenshots_aurora_review_light_merchant_match_evidence, docs_screenshots_aurora_review_light_category_choices, docs_screenshots_aurora_review_light_remember_merchant_rule, docs_screenshots_aurora_review_light_review_actions, docs_screenshots_aurora_review_light_review_progress [EXTRACTED 1.00]
- **Aurora Transaction Exploration Flow** — docs_screenshots_aurora_transactions_dark_transaction_filter_toolbar, docs_screenshots_aurora_transactions_dark_account_period_context, docs_screenshots_aurora_transactions_dark_dense_transaction_ledger, docs_screenshots_aurora_transactions_dark_category_status_badges [INFERRED 0.95]
- **Aurora Transaction Exploration and Classification** — docs_screenshots_aurora_transactions_light_search_filter_toolbar, docs_screenshots_aurora_transactions_light_transaction_table, docs_screenshots_aurora_transactions_light_merchant_descriptions, docs_screenshots_aurora_transactions_light_account_attribution, docs_screenshots_aurora_transactions_light_category_badges, docs_screenshots_aurora_transactions_light_signed_amounts, docs_screenshots_aurora_transactions_light_excluded_activity [EXTRACTED 1.00]
- **Horizon Monthly Financial Overview** — docs_screenshots_horizon_dashboard_dark_gradient_financial_summary, docs_screenshots_horizon_dashboard_dark_spending_trend_visualization, docs_screenshots_horizon_dashboard_dark_category_breakdown_visualization, docs_screenshots_horizon_dashboard_dark_transaction_and_recurring_activity, docs_screenshots_horizon_dashboard_dark_largest_purchases, docs_screenshots_horizon_dashboard_dark_excluded_activity_rule [EXTRACTED 1.00]
- **Horizon Financial Overview** — docs_screenshots_horizon_dashboard_light_gradient_financial_summary, docs_screenshots_horizon_dashboard_light_spending_trend_chart, docs_screenshots_horizon_dashboard_light_category_breakdown_chart, docs_screenshots_horizon_dashboard_light_recent_transactions, docs_screenshots_horizon_dashboard_light_upcoming_recurring_charges, docs_screenshots_horizon_dashboard_light_largest_purchases, docs_screenshots_horizon_dashboard_light_excluded_activity_transparency [INFERRED 0.95]
- **Savings Capacity Context** — docs_screenshots_horizon_dashboard_light_gradient_financial_summary, docs_screenshots_horizon_dashboard_light_savings_equation, docs_screenshots_horizon_dashboard_light_upcoming_recurring_charges, docs_screenshots_horizon_dashboard_light_excluded_activity_transparency [INFERRED 0.85]
- **Horizon Dark Category Review Workflow** — docs_screenshots_horizon_review_dark_review_progress, docs_screenshots_horizon_review_dark_transaction_review_card, docs_screenshots_horizon_review_dark_transaction_context, docs_screenshots_horizon_review_dark_category_choice_grid, docs_screenshots_horizon_review_dark_remember_merchant_rule, docs_screenshots_horizon_review_dark_review_actions [EXTRACTED 1.00]
- **Horizon Transaction Categorization Review Workflow** — docs_screenshots_horizon_review_light_review_progress, docs_screenshots_horizon_review_light_transaction_under_review, docs_screenshots_horizon_review_light_category_selection_grid, docs_screenshots_horizon_review_light_merchant_memory_rule, docs_screenshots_horizon_review_light_review_actions [EXTRACTED 1.00]
- **Horizon Transaction Exploration Workspace** — docs_screenshots_horizon_transactions_dark_profile_account_period_context, docs_screenshots_horizon_transactions_dark_transaction_search_filters, docs_screenshots_horizon_transactions_dark_dense_transaction_table, docs_screenshots_horizon_transactions_dark_merchant_account_detail, docs_screenshots_horizon_transactions_dark_category_badges, docs_screenshots_horizon_transactions_dark_accounting_state_cues [INFERRED 0.95]
- **Horizon Light Transaction Exploration** — docs_screenshots_horizon_transactions_light_transaction_count, docs_screenshots_horizon_transactions_light_account_period_filters, docs_screenshots_horizon_transactions_light_search_filter_toolbar, docs_screenshots_horizon_transactions_light_transaction_table, docs_screenshots_horizon_transactions_light_merchant_descriptions, docs_screenshots_horizon_transactions_light_account_attribution, docs_screenshots_horizon_transactions_light_category_badges, docs_screenshots_horizon_transactions_light_signed_and_excluded_amounts [EXTRACTED 1.00]
- **Four UI Direction Comparison** — docs_screenshots_landing_dark_meridian_direction, docs_screenshots_landing_dark_aurora_direction, docs_screenshots_landing_dark_ledger_direction, docs_screenshots_landing_dark_horizon_direction, docs_screenshots_landing_dark_shared_synthetic_dataset [EXTRACTED 1.00]
- **Spending Tracker UI Direction Set** — docs_screenshots_landing_light_meridian_direction, docs_screenshots_landing_light_aurora_direction, docs_screenshots_landing_light_ledger_direction, docs_screenshots_landing_light_horizon_direction [EXTRACTED 1.00]
- **Ledger Dark Financial Overview** — docs_screenshots_ledger_dashboard_dark_financial_kpi_strip, docs_screenshots_ledger_dashboard_dark_spending_trend, docs_screenshots_ledger_dashboard_dark_category_mix, docs_screenshots_ledger_dashboard_dark_category_budgets, docs_screenshots_ledger_dashboard_dark_upcoming_recurring, docs_screenshots_ledger_dashboard_dark_largest_purchases, docs_screenshots_ledger_dashboard_dark_recent_transactions [EXTRACTED 1.00]
- **Ledger Dense Analytical Dashboard** — docs_screenshots_ledger_dashboard_light_compact_kpi_strip, docs_screenshots_ledger_dashboard_light_spending_trend_chart, docs_screenshots_ledger_dashboard_light_category_mix_chart, docs_screenshots_ledger_dashboard_light_category_budget_tracker, docs_screenshots_ledger_dashboard_light_upcoming_recurring_charges, docs_screenshots_ledger_dashboard_light_largest_purchases, docs_screenshots_ledger_dashboard_light_recent_transaction_table [INFERRED 0.95]
- **Ledger Budget Monitoring Context** — docs_screenshots_ledger_dashboard_light_budget_overrun_signal, docs_screenshots_ledger_dashboard_light_category_mix_chart, docs_screenshots_ledger_dashboard_light_category_budget_tracker, docs_screenshots_ledger_dashboard_light_recent_transaction_table [INFERRED 0.85]
- **Ledger Transaction Category Review Workflow** — docs_screenshots_ledger_review_dark_review_progress, docs_screenshots_ledger_review_dark_transaction_queue, docs_screenshots_ledger_review_dark_transaction_detail, docs_screenshots_ledger_review_dark_category_assignment_grid, docs_screenshots_ledger_review_dark_merchant_auto_apply_rule, docs_screenshots_ledger_review_dark_review_actions [EXTRACTED 1.00]
- **Ledger Light Category Review Workflow** — docs_screenshots_ledger_review_light_review_progress, docs_screenshots_ledger_review_light_current_transaction, docs_screenshots_ledger_review_light_transaction_details, docs_screenshots_ledger_review_light_category_assignment_grid, docs_screenshots_ledger_review_light_merchant_memory_rule, docs_screenshots_ledger_review_light_review_actions, docs_screenshots_ledger_review_light_review_queue [EXTRACTED 1.00]
- **Ledger Transaction Exploration Workflow** — docs_screenshots_ledger_transactions_dark_account_period_filters, docs_screenshots_ledger_transactions_dark_transaction_search, docs_screenshots_ledger_transactions_dark_category_type_filters, docs_screenshots_ledger_transactions_dark_inclusion_summary, docs_screenshots_ledger_transactions_dark_transaction_ledger_table [EXTRACTED 1.00]
- **Ledger Transaction Row Encoding** — docs_screenshots_ledger_transactions_dark_account_indicators, docs_screenshots_ledger_transactions_dark_category_badges, docs_screenshots_ledger_transactions_dark_signed_amounts, docs_screenshots_ledger_transactions_dark_exclusion_badges [EXTRACTED 1.00]
- **Ledger Transaction Analysis Workspace** — docs_screenshots_ledger_transactions_light_transaction_scope_summary, docs_screenshots_ledger_transactions_light_account_period_context, docs_screenshots_ledger_transactions_light_search_category_type_filters, docs_screenshots_ledger_transactions_light_high_density_transaction_grid, docs_screenshots_ledger_transactions_light_account_identity_markers, docs_screenshots_ledger_transactions_light_category_badges, docs_screenshots_ledger_transactions_light_excluded_and_credit_cues [INFERRED 0.95]
- **Meridian Dark Financial Overview** — docs_screenshots_meridian_dashboard_dark_financial_kpi_cards, docs_screenshots_meridian_dashboard_dark_spending_trend, docs_screenshots_meridian_dashboard_dark_category_breakdown, docs_screenshots_meridian_dashboard_dark_category_budgets, docs_screenshots_meridian_dashboard_dark_upcoming_recurring, docs_screenshots_meridian_dashboard_dark_largest_purchases, docs_screenshots_meridian_dashboard_dark_recent_transactions [EXTRACTED 1.00]
- **Meridian Professional-Friendly Dashboard** — docs_screenshots_meridian_dashboard_light_gradient_spending_hero, docs_screenshots_meridian_dashboard_light_secondary_metric_cards, docs_screenshots_meridian_dashboard_light_spending_trend_chart, docs_screenshots_meridian_dashboard_light_category_breakdown_chart, docs_screenshots_meridian_dashboard_light_category_budget_tracker, docs_screenshots_meridian_dashboard_light_upcoming_recurring_charges, docs_screenshots_meridian_dashboard_light_largest_purchases, docs_screenshots_meridian_dashboard_light_recent_transaction_table [INFERRED 0.95]
- **Meridian Spending Decision Context** — docs_screenshots_meridian_dashboard_light_gradient_spending_hero, docs_screenshots_meridian_dashboard_light_category_breakdown_chart, docs_screenshots_meridian_dashboard_light_category_budget_tracker, docs_screenshots_meridian_dashboard_light_recent_transaction_table, docs_screenshots_meridian_dashboard_light_excluded_activity_transparency [INFERRED 0.85]
- **Meridian Transaction Category Review Workflow** — docs_screenshots_meridian_review_dark_review_progress, docs_screenshots_meridian_review_dark_transaction_queue, docs_screenshots_meridian_review_dark_transaction_detail, docs_screenshots_meridian_review_dark_category_choice_grid, docs_screenshots_meridian_review_dark_merchant_memory_rule, docs_screenshots_meridian_review_dark_review_actions [EXTRACTED 1.00]
- **Meridian Light Category Review Workflow** — docs_screenshots_meridian_review_light_review_progress, docs_screenshots_meridian_review_light_current_transaction, docs_screenshots_meridian_review_light_transaction_details, docs_screenshots_meridian_review_light_category_assignment_grid, docs_screenshots_meridian_review_light_merchant_memory_rule, docs_screenshots_meridian_review_light_review_actions, docs_screenshots_meridian_review_light_review_queue [EXTRACTED 1.00]
- **Meridian Transaction Exploration Workflow** — docs_screenshots_meridian_transactions_dark_account_period_filters, docs_screenshots_meridian_transactions_dark_transaction_search, docs_screenshots_meridian_transactions_dark_category_type_inclusion_filters, docs_screenshots_meridian_transactions_dark_transaction_count_summary, docs_screenshots_meridian_transactions_dark_transaction_table [EXTRACTED 1.00]
- **Meridian Transaction Row Encoding** — docs_screenshots_meridian_transactions_dark_account_indicators, docs_screenshots_meridian_transactions_dark_category_status_badges, docs_screenshots_meridian_transactions_dark_signed_amounts, docs_screenshots_meridian_transactions_dark_excluded_transaction_states [EXTRACTED 1.00]
- **Meridian Transaction Management Workspace** — docs_screenshots_meridian_transactions_light_transaction_scope_summary, docs_screenshots_meridian_transactions_light_profile_account_period_context, docs_screenshots_meridian_transactions_light_search_faceted_filters, docs_screenshots_meridian_transactions_light_dense_comfortable_transaction_table, docs_screenshots_meridian_transactions_light_account_identity_markers, docs_screenshots_meridian_transactions_light_category_badges, docs_screenshots_meridian_transactions_light_accounting_inclusion_cues [INFERRED 0.95]

## Communities (58 total, 12 thin omitted)

### Community 0 - "Account API Services"
Cohesion: 0.05
Nodes (82): Account, get_account(), get_accounts(), patch_account(), post_account(), post_account_archive(), post_account_restore(), Query (+74 more)

### Community 1 - "Profile Data Model"
Cohesion: 0.06
Nodes (52): Account, Credit-card account persistence model., A masked card account owned by exactly one profile., Base, datetime, Shared SQLAlchemy declarative base and timestamp helpers., Return an aware UTC timestamp for Python-side inserts and updates., Base for every persisted domain model. (+44 more)

### Community 2 - "Database Migration Setup"
Cohesion: 0.06
Nodes (50): database_url(), Alembic environment for the local SQLite database., Return Alembic's URL form of the configured local SQLite path., Run migrations without opening a database connection., Run migrations using an existing connection., Run migrations with the application's configured SQLite engine., run_migrations(), run_migrations_offline() (+42 more)

### Community 3 - "Horizon UI Components"
Cohesion: 0.18
Nodes (28): AuroraDashboard(), CategoryCard(), Hero(), horizon, HorizonDashboard(), MONTH_LABEL, NAV, REVIEW_CATEGORIES (+20 more)

### Community 4 - "Project Governance Docs"
Cohesion: 0.08
Nodes (31): API Lint and Test Gate, Continuous Integration, Web Typecheck and Build Gate, Mandatory Workboard Protocol, API Development Operations, Alembic Migration Workflow, API Runtime Dependency Stack, API Test and Lint Toolchain (+23 more)

### Community 5 - "Meridian Review Components"
Cohesion: 0.11
Nodes (22): AuroraReview(), TxRow(), HorizonReview(), TxRow(), AmountCell(), MiniTxn(), Review(), TxnTableRow() (+14 more)

### Community 6 - "Money Date Utilities"
Cohesion: 0.12
Nodes (23): parse_iso_date(), Strict calendar-date parsing and serialization., Parse a canonical ``YYYY-MM-DD`` calendar date., Serialize a calendar date, rejecting datetime-like subclasses., serialize_iso_date(), add_cents(), parse_cents(), Exact integer-cent money operations.  Decimal text is accepted only at an input (+15 more)

### Community 7 - "Frontend Mock Data"
Cohesion: 0.11
Nodes (25): accountById, accounts, between(), categories, daysInMonth, iso(), makeTransactions(), merchants (+17 more)

### Community 8 - "FastAPI Application Lifecycle"
Cohesion: 0.10
Nodes (18): dispose_database(), Dispose lazily initialized application database resources., invalid_update_handler(), lifespan(), FastAPI application entrypoint.  Run locally with::      uvicorn app.main:app, Log startup and dispose lazily initialized database resources on exit., Map absent and out-of-scope resources to the same response shape., Return readable validation feedback for explicit null updates. (+10 more)

### Community 9 - "Frontend Routing Theme"
Cohesion: 0.16
Nodes (14): App(), SCREENS, Switcher(), directionById, directions, DirectionMeta, ScreenKey, Landing() (+6 more)

### Community 10 - "TypeScript Configuration"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+13 more)

### Community 11 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (20): dependencies, react, react-dom, react-router-dom, recharts, devDependencies, @types/react, @types/react-dom (+12 more)

### Community 12 - "Meridian Dark Transactions"
Cohesion: 0.22
Nodes (13): Per-Transaction Account Indicators, Account and Period Filters, Balanced Detail and Warmth Dark Visual System, Colour-Coded Category and Uncategorized Badges, Category Type and Inclusion Filters, Muted Excluded Transaction States, Hayden Personal Profile Context, Signed Expense Income and Refund Amounts (+5 more)

### Community 13 - "Ledger UI Components"
Cohesion: 0.17
Nodes (6): chartTooltip, ledger, MONTH_LABEL, NAV, REVIEW_CHOICES, PREV_YM

### Community 14 - "Aurora Light Transactions"
Cohesion: 0.23
Nodes (12): Per-Transaction Account Attribution, Account and Period Filters, Aurora Transactions Light Theme, Color-Coded Category Badges, Excluded Payment and Interest Activity, Merchant and Raw Description Details, Hayden Personal Profile, Transaction Search and Filter Toolbar (+4 more)

### Community 15 - "Horizon Light Dashboard"
Cohesion: 0.26
Nodes (12): Overall Budget Progress, Spending by Category Breakdown, Excluded Activity Transparency, Gradient Financial Summary Hero, Horizon Dashboard Screen — Light Theme, Largest Purchases Ranking, Horizon Primary Navigation, Profile, Account, and Period Context (+4 more)

### Community 16 - "Ledger Dark Dashboard"
Cohesion: 0.24
Nodes (12): Account and Period Filters, Category Budget Progress List, Category Mix Donut and Legend, July Dashboard Overview Summary, Dense Monthly Financial KPI Strip, Largest Purchases List, Ledger Dashboard Dark Theme, Hayden Personal Profile (+4 more)

### Community 17 - "Ledger Light Dashboard"
Cohesion: 0.26
Nodes (12): Budget Overrun Signal, Category Budget Tracker, Category Mix Chart, Compact Financial KPI Strip, Dense Finance Command Navigation, Excluded Activity Accounting, Largest Purchases Ranking, Ledger Dashboard Screen — Light Theme (+4 more)

### Community 18 - "Ledger Dark Transactions"
Cohesion: 0.24
Nodes (12): Per-Transaction Account Indicators, Account and Period Filters, Dark High-Density Analyst Cockpit Visual System, Colour-Coded Category Badges, Category and Transaction Type Filters, Dense Ledger Top Navigation with Active Transactions State, Excluded Transaction Badges, Included and Excluded Transaction Summary (+4 more)

### Community 19 - "Meridian Dark Dashboard"
Cohesion: 0.26
Nodes (12): All Accounts and July 2026 Filters, Spending by Category Donut and Legend, Tracked Category Budget Progress, July 2026 Dashboard Summary, Monthly Financial KPI Cards, July 2026 Largest Purchases, Meridian Dashboard Dark Theme, Hayden Personal Profile (+4 more)

### Community 20 - "Meridian Light Dashboard"
Cohesion: 0.26
Nodes (12): Spending by Category Breakdown, Category Budget Tracker, Excluded Activity Transparency, Gradient Spending and Budget Hero, Largest Purchases Ranking, Meridian Dashboard Screen — Light Theme, Profile, Account, and Period Context, Recent Multi-Account Transaction Table (+4 more)

### Community 21 - "Horizon Dark Dashboard"
Cohesion: 0.33
Nodes (11): Account and Period Filters, Category Spending Breakdown, Horizon Dark Personal Finance Dashboard, Excluded Activity Accounting Rule, Gradient Monthly Financial Summary, Largest Purchase Ranking, Hayden Personalized Profile Context, Spending Trend Visualization (+3 more)

### Community 22 - "Horizon Light Transactions"
Cohesion: 0.25
Nodes (11): Per-Transaction Account Attribution, Account and Period Filters, Color-Coded Category Badges, Horizon Transactions Light Theme, Merchant and Raw Description Details, Hayden Personal Profile, Transaction Search and Filter Toolbar, Signed and Excluded Transaction Amounts (+3 more)

### Community 23 - "Light UI Comparison"
Cohesion: 0.24
Nodes (11): Aurora Calm Modern Banking Direction, Spending Tracker Light UI Direction Comparison Page, One Dataset Four UI Directions Comparison, Horizon Bold and Colourful Direction, Identical Synthetic Spending Dataset, Ledger Dense Data-Forward Analyst Direction, Per-Screen Light and Dark Theme Toggle, Meridian Recommended UI Direction (+3 more)

### Community 24 - "Ledger Light Review"
Cohesion: 0.27
Nodes (11): All Accounts and July 2026 Filters, Nine Category Assignment Choices, Petro-Canada Suggested Transaction, Ledger Category Review Light Theme, Petro-Canada Auto-Apply Merchant Rule, Hayden Personal Profile, Skip and Confirm Category Actions, Category Review Progress 0 of 10 (+3 more)

### Community 25 - "Meridian Dark Review"
Cohesion: 0.29
Nodes (11): Account and Period Review Filters, Balanced Dense and Warm Dark Visual System, Nine-Category Choice Grid, Remember Merchant for Future Transactions Rule, Hayden Personal Profile Context, Skip and Disabled Confirm Category Actions, Ten to Categorise and Zero Done Progress, Meridian Dark Category Review Screen (+3 more)

### Community 26 - "Meridian Light Review"
Cohesion: 0.27
Nodes (11): All Accounts and July 2026 Filters, Nine Category Assignment Cards, Petro-Canada Uncategorized Transaction, Petro-Canada Future Transaction Rule, Meridian Category Review Light Theme, Hayden Personal Profile, Skip and Confirm Category Actions, Category Review Progress 0 of 10 (+3 more)

### Community 27 - "Aurora UI Components"
Cohesion: 0.22
Nodes (7): aurora, NAV, Topbar(), Direction, CURRENT_YM, formatMonthLabel(), categoryById

### Community 28 - "Aurora Light Dashboard"
Cohesion: 0.33
Nodes (10): Account and Period Filters, Aurora Dashboard Light Theme, Spending by Category Breakdown, Monthly Financial KPI Cards, Largest Purchases List, Hayden Personal Profile, Recent Transactions List, Sidebar Navigation (+2 more)

### Community 29 - "Aurora Dark Review"
Cohesion: 0.33
Nodes (10): Account and Period Filters, Category Selection Grid, Merchant-Keyword Category Suggestion with Confidence, Dark Indigo Card-Based Review Interface, Remember Merchant for Future Transactions Rule, Skip and Confirm Category Actions, Ten-Item Review Progress, Aurora Dark Category Review Screen (+2 more)

### Community 30 - "Aurora Light Review"
Cohesion: 0.29
Nodes (10): Account and Period Filters, Aurora Review Categories Light Theme, Category Choice Grid, Merchant Match Confidence Evidence, Hayden Personal Profile, Remember Merchant for Future Transactions Control, Skip and Confirm Category Actions, Category Review Progress (+2 more)

### Community 31 - "Horizon Dark Review"
Cohesion: 0.27
Nodes (10): Account and Period Filters, Large Category Choice Grid, Horizon Review Dark Theme, Hayden Personal Profile, Remember Petro-Canada Rule Control, Skip and Confirm Category Actions, Category Review Progress, Horizon Top Navigation (+2 more)

### Community 32 - "Horizon Light Review"
Cohesion: 0.31
Nodes (10): Account and Period Filters, Nine-Category Selection Grid, Remember Merchant for Future Transactions Rule, Hayden Personal Profile Context, Skip and Confirm Category Actions, Ten-Item Review Progress, Horizon Light Category Review Screen, Compact Top Navigation with Active Review State (+2 more)

### Community 33 - "Dark UI Comparison"
Cohesion: 0.29
Nodes (10): Aurora Calm Banking Direction, Controlled UI Direction Comparison, Per-Direction Screen Links, Horizon Bold Fintech Direction, Ledger Data-Forward Direction, Meridian Recommended Direction, Shared Synthetic Spending Dataset, Light and Dark Theme Toggle (+2 more)

### Community 34 - "Ledger Dark Review"
Cohesion: 0.33
Nodes (10): Account and Period Review Filters, Dark Dense Analyst Cockpit Visual System, Nine-Category Assignment Grid, Dense Ledger Top Navigation with Active Review State, Remember Merchant and Auto-Apply Rule, Skip and Confirm Category Actions, Zero of Ten Categories Reviewed Progress, Ledger Dark Category Review Screen (+2 more)

### Community 35 - "Financial Derived Data"
Cohesion: 0.22
Nodes (7): CategorySpend, CUR, MonthlyPoint, budgets, incomeSchedules, recurringSeries, transactions

### Community 36 - "Aurora Dark Dashboard"
Cohesion: 0.39
Nodes (9): Account and Period Filters, Category Spending Breakdown, Dark Indigo Card-Based Visual System, Aurora Dark Personal Finance Dashboard, Monthly Financial Summary, Hayden Personal Profile Context, Persistent Sidebar Navigation, Spending Trend Visualization (+1 more)

### Community 37 - "Ledger Light Transactions"
Cohesion: 0.33
Nodes (9): Account Identity Markers, Account and Period Context Controls, Compact Color-Coded Category Badges, Ledger Finance Command Navigation, Excluded Activity and Credit Cues, High-Density Multi-Month Transaction Grid, Ledger Transactions Screen — Light Theme, Search, Category, and Type Filters (+1 more)

### Community 38 - "Meridian Light Transactions"
Cohesion: 0.33
Nodes (9): Multi-Account Identity Markers, Accounting Inclusion and Credit Cues, Friendly Color-Coded Category Badges, Dense-but-Comfortable Transaction Table, Meridian Transactions Screen — Light Theme, Profile, Account, and Period Context, Rounded Meridian Primary Navigation, Search and Faceted Transaction Filters (+1 more)

### Community 39 - "Aurora Dark Transactions"
Cohesion: 0.36
Nodes (8): Account and Month Context Controls, Aurora Transactions Screen — Dark Theme, Color-Coded Category Status Badges, Dense Multi-Account Transaction Ledger, Personal Finance Navigation Sidebar, Active Personal Profile Context, Spending Inclusion and Exclusion Cues, Transaction Search and Filter Toolbar

### Community 40 - "Horizon Dark Transactions"
Cohesion: 0.39
Nodes (8): Accounting State and Inclusion Cues, Color-Coded Transaction Categories, Dense Multi-Month Transaction Table, Horizon Transactions Screen — Dark Theme, Horizon Horizontal Navigation, Merchant and Account Detail Rows, Profile, Account, and Period Context, Transaction Search and Faceted Filters

### Community 41 - "Migration Baseline"
Cohesion: 0.40
Nodes (4): downgrade(), Create no domain tables; BE-03 owns the initial domain schema., Remove no domain tables from the empty baseline., upgrade()

### Community 42 - "Profile Account Migration"
Cohesion: 0.40
Nodes (4): downgrade(), Create isolated profile and account storage., Remove account storage before its owning profiles., upgrade()

## Knowledge Gaps
- **151 isolated node(s):** `spending-tracker-api`, `name`, `private`, `version`, `type` (+146 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InvalidUpdateError` connect `Account API Services` to `FastAPI Application Lifecycle`, `Profile Data Model`, `Money Date Utilities`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `Profile` connect `Profile Data Model` to `Account API Services`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `create_db_engine()` connect `Database Migration Setup` to `Account API Services`, `Profile Data Model`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `ProfileCreate` (e.g. with `TimestampedRead` and `test_create_schemas_normalize_names_and_validate_masked_fields()`) actually correct?**
  _`ProfileCreate` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `create_account()` (e.g. with `post_account()` and `require_profile()`) actually correct?**
  _`create_account()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `create_profile()` (e.g. with `post_profile()` and `test_account_archive_preserves_record_and_filters_default_list()`) actually correct?**
  _`create_profile()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Profile` (e.g. with `Account` and `Base`) actually correct?**
  _`Profile` has 6 INFERRED edges - model-reasoned connections that need verification._