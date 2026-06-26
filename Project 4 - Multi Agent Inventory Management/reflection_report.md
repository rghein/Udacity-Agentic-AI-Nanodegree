# Reflection Report

## Agent Workflow and Architecture

The agent workflow is illustrated in `agent_flow_diagram.md`. The system begins with a customer inquiry, which the Request Parser Agent converts into a structured `CustomerRequest`. A validation gate then keeps only exact catalog matches with positive quantities while preserving unsupported item names so they can be acknowledged in the final response.

The Orchestration Agent coordinates the main workflow in a fixed sequence. It first sends the validated request to the Inventory Agent, which checks available stock and identifies shortages. It then sends the request to the Quoting Agent, which calculates item prices, applies bulk discounts, and produces an itemized quote. Next, the Ordering Agent uses the inventory and quote results to either record a completed sale or recommend and record restock orders when inventory is insufficient. Finally, the customer-message formatter creates the `OrchestratorResponse`, presenting prices, fulfillment status, unsupported items, and restock estimates while excluding internal details such as cash balances, supplier costs, and raw database information.

The Orchestration Agent also has access to `get_financial_snapshot`, an internal audit tool that wraps `generate_financial_report`. This allows the required financial-report helper to be used through an agent tool while keeping cash balances, inventory values, and total assets out of the customer-facing message.

This architecture was chosen because each stage has a distinct responsibility. Separating parsing, inventory checking, quoting, ordering, and response formatting makes the workflow easier to control and reduces the risk that one agent will perform actions outside its role. The central orchestrator enforces the correct order of operations, while Pydantic models such as `CustomerRequest`, `InventoryResult`, `QuoteResult`, and `OrderResult` provide structured contracts between agents. This makes the system more predictable than passing loosely formatted natural-language messages between stages.

## Evaluation of Test Results

The 20 requests in `test_results.csv` exercised both fulfillment paths: 11 resulted in completed sales and nine triggered restocking because of inventory shortages. No request produced the generic internal-error response, showing that the workflow completed all test scenarios successfully.

The results demonstrate several strengths. Quotes consistently included quantities, discounts, line totals, and total prices. For example, request 3 applied a 15 percent bulk discount to 10,000 sheets of A4 paper, detected a shortage of 9,928 sheets, and provided an estimated restock date. The system also separated supported and unsupported products within the same inquiry, allowing recognized items to be quoted while clearly identifying products it could not match.

Cash balances and inventory values changed as sales and restock transactions were processed, demonstrating that agent decisions affected the shared business state. However, the CSV contains observed results rather than expected outcomes, so future testing should compare prices, shortages, decisions, and balances against predetermined values.

## Areas for Further Improvement

### 1. Improve product-name matching

Test responses contain unsupported descriptions that are similar to catalog products, such as "roll of streamers," "white printer paper," or "poster board." The strict exact-name validation protects the database, but it can also reject reasonable customer request terms. A future system could introduce a controlled alias table. High-confidence aliases would map to exact catalog identifiers, while ambiguous matches could trigger a clarification question. The exact catalog name would still be required before any database tool is called.

### 2. Support partial fulfillment and backorders

The current ordering decision is made for the request as a whole. When one item is short, the customer sale waits while restock orders are placed. A future version could offer the customer a choice between partial fulfillment, a single delayed shipment, or cancellation of unavailable line items. This would require tracking fulfillment status for each quote line and recording backorders separately from completed sales.
