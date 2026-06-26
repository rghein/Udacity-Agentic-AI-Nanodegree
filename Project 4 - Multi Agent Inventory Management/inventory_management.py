import ast
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import dotenv
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy import Engine, create_engine
from sqlalchemy.sql import text

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper", "category": "paper", "unit_price": 0.05},
    {"item_name": "Letter-sized paper", "category": "paper", "unit_price": 0.06},
    {"item_name": "Cardstock", "category": "paper", "unit_price": 0.15},
    {"item_name": "Colored paper", "category": "paper", "unit_price": 0.10},
    {"item_name": "Glossy paper", "category": "paper", "unit_price": 0.20},
    {"item_name": "Matte paper", "category": "paper", "unit_price": 0.18},
    {"item_name": "Recycled paper", "category": "paper", "unit_price": 0.08},
    {"item_name": "Eco-friendly paper", "category": "paper", "unit_price": 0.12},
    {"item_name": "Poster paper", "category": "paper", "unit_price": 0.25},
    {"item_name": "Banner paper", "category": "paper", "unit_price": 0.30},
    {"item_name": "Kraft paper", "category": "paper", "unit_price": 0.10},
    {"item_name": "Construction paper", "category": "paper", "unit_price": 0.07},
    {"item_name": "Wrapping paper", "category": "paper", "unit_price": 0.15},
    {"item_name": "Glitter paper", "category": "paper", "unit_price": 0.22},
    {"item_name": "Decorative paper", "category": "paper", "unit_price": 0.18},
    {"item_name": "Letterhead paper", "category": "paper", "unit_price": 0.12},
    {"item_name": "Legal-size paper", "category": "paper", "unit_price": 0.08},
    {"item_name": "Crepe paper", "category": "paper", "unit_price": 0.05},
    {"item_name": "Photo paper", "category": "paper", "unit_price": 0.25},
    {"item_name": "Uncoated paper", "category": "paper", "unit_price": 0.06},
    {"item_name": "Butcher paper", "category": "paper", "unit_price": 0.10},
    {"item_name": "Heavyweight paper", "category": "paper", "unit_price": 0.20},
    {"item_name": "Standard copy paper", "category": "paper", "unit_price": 0.04},
    {"item_name": "Bright-colored paper", "category": "paper", "unit_price": 0.12},
    {"item_name": "Patterned paper", "category": "paper", "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates", "category": "product", "unit_price": 0.10},
    {"item_name": "Paper cups", "category": "product", "unit_price": 0.08},
    {"item_name": "Paper napkins", "category": "product", "unit_price": 0.02},
    {"item_name": "Disposable cups", "category": "product", "unit_price": 0.10},
    {"item_name": "Table covers", "category": "product", "unit_price": 1.50},
    {"item_name": "Envelopes", "category": "product", "unit_price": 0.05},
    {"item_name": "Sticky notes", "category": "product", "unit_price": 0.03},
    {"item_name": "Notepads", "category": "product", "unit_price": 2.00},
    {"item_name": "Invitation cards", "category": "product", "unit_price": 0.50},
    {"item_name": "Flyers", "category": "product", "unit_price": 0.15},
    {"item_name": "Party streamers", "category": "product", "unit_price": 0.05},
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},
    {"item_name": "Paper party bags", "category": "product", "unit_price": 0.25},
    {"item_name": "Name tags with lanyards", "category": "product", "unit_price": 0.75},
    {"item_name": "Presentation folders", "category": "product", "unit_price": 0.50},

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock", "category": "specialty", "unit_price": 0.50},
    {"item_name": "80 lb text paper", "category": "specialty", "unit_price": 0.40},
    {"item_name": "250 gsm cardstock", "category": "specialty", "unit_price": 0.30},
    {"item_name": "220 gsm poster paper", "category": "specialty", "unit_price": 0.35},
]

#######################
## Utility Functions ##
#######################

def generate_sample_inventory(
    paper_supplies: list,
    coverage: float = 0.4,
    seed: int = 137,
) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the
    full paper supply list.
    """
    np.random.seed(seed)
    num_items = int(len(paper_supplies) * coverage)
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False,
    )
    selected_items = [paper_supplies[i] for i in selected_indices]

    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),
            "min_stock_level": np.random.randint(50, 150),
        })

    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:
    """
    Set up the Munder Difflin database with transactions, quote requests,
    historical quotes, generated inventory, and opening cash.
    """
    try:
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],
            "units": [],
            "price": [],
            "transaction_date": [],
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        initial_date = datetime(2025, 1, 1).isoformat()

        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type",
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)
        initial_transactions = [{
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        }]

        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        pd.DataFrame(initial_transactions).to_sql(
            "transactions",
            db_engine,
            if_exists="append",
            index=False,
        )
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)
        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """Record a stock order or sale transaction."""
    try:
        date_str = date.isoformat() if isinstance(date, datetime) else date

        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """Retrieve a snapshot of positive inventory as of a specific date."""
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """Retrieve the current stock level of one item as of a date."""
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """Estimate supplier delivery date from order size and start date."""
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    delivery_date_dt = input_date_dt + timedelta(days=days)
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """Calculate cash balance as of a specific date."""
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    query = """
        SELECT transaction_type, price
        FROM transactions
        WHERE transaction_date <= :as_of_date
    """
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    if result.empty:
        return 0.0

    sales = result.loc[result["transaction_type"] == "sales", "price"].sum()
    stock_orders = result.loc[result["transaction_type"] == "stock_orders", "price"].sum()
    return float(sales - stock_orders)

def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """Generate cash, inventory, assets, and sales summary as of a date."""
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    cash = get_cash_balance(as_of_date)
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        current_stock = int(stock_info["current_stock"].iloc[0])
        item_value = current_stock * float(item["unit_price"])
        inventory_value += item_value
        inventory_summary.append({
            "item_name": item["item_name"],
            "current_stock": current_stock,
            "unit_price": float(item["unit_price"]),
            "inventory_value": round(item_value, 2),
        })

    sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales'
        AND item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
    """
    sales_summary = pd.read_sql(sales_query, db_engine, params={"as_of_date": as_of_date})

    return {
        "as_of_date": as_of_date,
        "cash_balance": round(cash, 2),
        "inventory_value": round(inventory_value, 2),
        "total_assets": round(cash + inventory_value, 2),
        "inventory_summary": inventory_summary,
        "sales_summary": sales_summary.to_dict(orient="records"),
    }

def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """Search historical quotes for rows matching any search term."""
    conditions = []
    params = {"limit": limit}

    for idx, term in enumerate(search_terms):
        key = f"term_{idx}"
        params[key] = f"%{term.lower()}%"
        conditions.append(
            f"""(
                lower(quote_explanation) LIKE :{key}
                OR lower(job_type) LIKE :{key}
                OR lower(event_type) LIKE :{key}
            )"""
        )

    if not conditions:
        return []

    where_clause = " OR ".join(conditions)
    query = f"""
        SELECT *
        FROM quotes
        WHERE {where_clause}
        ORDER BY request_id DESC
        LIMIT :limit
    """

    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

##############################
## MULTI AGENT STARTS HERE ###
##############################

######################
## Pydantic Schemas ##
######################

class RequestedItem(BaseModel):
    """One inventory item requested by a customer."""
    item_name: str = Field(description="Name of the requested inventory item")
    quantity: int = Field(gt=0, description="Number of units requested; must be greater than 0")

class CustomerRequest(BaseModel):
    """Structured version of a customer's request."""
    request_date: str = Field(description="Date of the customer request in YYYY-MM-DD format")
    job_type: Optional[str] = Field(default=None, description="Customer job type, if known")
    event_type: Optional[str] = Field(default=None, description="Customer event type, if known")
    original_request: str = Field(description="Original customer request text")
    items: list[RequestedItem] = Field(description="Items and quantities requested by the customer")
    unmatched_items: list[str] = Field(
        default_factory=list,
        description="Requested products that have no clear inventory match",
    )

class InventoryCheck(BaseModel):
    """Inventory availability result for one requested item."""
    item_name: str
    requested_quantity: int
    available_quantity: int
    shortage: int
    can_fulfill_now: bool

class InventoryResult(BaseModel):
    """Inventory availability results for a full customer request."""
    request_date: str
    checks: list[InventoryCheck]
    all_items_available: bool

class QuoteLineItem(BaseModel):
    """One priced line item in a quote."""
    item_name: str
    quantity: int
    catalog_unit_price: float
    discount_rate: float
    unit_price: float
    line_total: float

class QuoteResult(BaseModel):
    """Complete quote generated for a customer request."""
    request_date: str
    line_items: list[QuoteLineItem]
    total_amount: float
    quote_explanation: str
    historical_quotes_used: int = 0

class RestockRecommendation(BaseModel):
    """Suggested supplier order for an inventory shortage."""
    item_name: str
    shortage: int
    suggested_order_quantity: int
    estimated_delivery_date: str
    estimated_cost: float

class OrderResult(BaseModel):
    """Result of recording sales and restock transactions."""
    request_date: str
    sales_recorded: bool
    restocks_recorded: bool
    transaction_ids: list[int]
    restock_recommendations: list[RestockRecommendation]
    message: str

class OrchestratorResponse(BaseModel):
    """Final structured response from the multi-agent workflow."""
    request_date: str
    customer_message: str
    inventory_result: InventoryResult
    quote_result: QuoteResult
    order_result: Optional[OrderResult] = None

class FinancialSnapshot(BaseModel):
    """Internal financial audit snapshot for a request date."""
    request_date: str
    cash_balance: float
    inventory_value: float
    total_assets: float

##########################################################
## Set up and load env parameters and instantiate model ##
##########################################################

dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("UDACITY_OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv("UDACITY_OPENAI_BASE_URL")

if BASE_URL:
    model = OpenAIChatModel(
        MODEL_NAME,
        provider=OpenAIProvider(api_key=OPENAI_API_KEY, base_url=BASE_URL),
    )
else:
    model = OpenAIChatModel(
        MODEL_NAME,
        provider=OpenAIProvider(api_key=OPENAI_API_KEY),
    )

###########
## Tools ##
###########

def normalize_date(date: Union[str, datetime]) -> str:
    """Return a YYYY-MM-DD date string for tool calls."""
    if isinstance(date, datetime):
        return date.strftime("%Y-%m-%d")
    return str(date).split("T")[0]

def get_available_item_names() -> List[str]:
    """Return exact item names currently present in the inventory table."""
    inventory_df = pd.read_sql("SELECT item_name FROM inventory", db_engine)
    return inventory_df["item_name"].tolist()

def keep_known_request_items(customer_request: CustomerRequest) -> CustomerRequest:
    """Remove request items that are not exact inventory records or have invalid quantities."""
    valid_items = set(get_available_item_names())
    unmatched_items = list(customer_request.unmatched_items)

    for item in customer_request.items:
        if item.item_name not in valid_items and item.item_name not in unmatched_items:
            unmatched_items.append(item.item_name)

    known_items = [
        item for item in customer_request.items
        if item.item_name in valid_items and item.quantity > 0
    ]
    return customer_request.model_copy(
        update={"items": known_items, "unmatched_items": unmatched_items}
    )

def agent_safe_customer_request(customer_request: CustomerRequest) -> CustomerRequest:
    """Return a structured request for downstream agents without raw item text."""
    customer_request = keep_known_request_items(customer_request)
    return customer_request.model_copy(
        update={
            "original_request": "Parsed items are verified; raw request omitted after parsing.",
            "unmatched_items": [],
        }
    )

## Tools for inventory agent

def get_inventory_item(item_name: str) -> Dict:
    """Look up one inventory item by exact name."""
    inventory_df = pd.read_sql(
        "SELECT * FROM inventory WHERE item_name = :item_name",
        db_engine,
        params={"item_name": item_name},
    )

    if inventory_df.empty:
        raise ValueError(f"Unknown inventory item: {item_name}")

    return inventory_df.iloc[0].to_dict()

def list_available_inventory(as_of_date: Union[str, datetime]) -> Dict[str, int]:
    """Return all inventory with positive stock on the requested date."""
    return get_all_inventory(normalize_date(as_of_date))

def check_inventory_for_item(
    item_name: str,
    requested_quantity: int,
    as_of_date: Union[str, datetime],
) -> InventoryCheck:
    """Check whether one requested item can be fulfilled from current stock."""
    if requested_quantity <= 0:
        raise ValueError("requested_quantity must be greater than 0")

    date_str = normalize_date(as_of_date)
    stock_df = get_stock_level(item_name, date_str)
    available_quantity = int(stock_df["current_stock"].iloc[0])
    shortage = max(requested_quantity - available_quantity, 0)

    return InventoryCheck(
        item_name=item_name,
        requested_quantity=requested_quantity,
        available_quantity=available_quantity,
        shortage=shortage,
        can_fulfill_now=shortage == 0,
    )

def check_inventory_for_request(customer_request: CustomerRequest) -> InventoryResult:
    """Check inventory for every item in a structured customer request."""
    customer_request = keep_known_request_items(customer_request)
    checks = [
        check_inventory_for_item(
            item.item_name,
            item.quantity,
            customer_request.request_date,
        )
        for item in customer_request.items
    ]

    return InventoryResult(
        request_date=customer_request.request_date,
        checks=checks,
        all_items_available=all(check.can_fulfill_now for check in checks),
    )

## Tools for quoting agent

def get_item_unit_price(item_name: str) -> float:
    """Return the unit price for an exact inventory item name."""
    item = get_inventory_item(item_name)
    return float(item["unit_price"])

def calculate_bulk_discount(quantity: int) -> float:
    """Return a simple bulk discount rate based on quantity."""
    if quantity >= 1000:
        return 0.15
    if quantity >= 500:
        return 0.10
    if quantity >= 100:
        return 0.05
    return 0.0

def find_similar_historical_quotes(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """Search historical quote records for similar customer requests."""
    cleaned_terms = [term.strip().lower() for term in search_terms if term.strip()]
    return search_quote_history(cleaned_terms, limit=limit)

def create_quote_for_request(
    customer_request: CustomerRequest,
    historical_search_terms: Optional[List[str]] = None,
) -> QuoteResult:
    """Create a quote using inventory prices, bulk discounts, and historical context."""
    customer_request = keep_known_request_items(customer_request)
    line_items = []

    for requested_item in customer_request.items:
        unit_price = get_item_unit_price(requested_item.item_name)
        discount = calculate_bulk_discount(requested_item.quantity)
        discounted_unit_price = unit_price * (1 - discount)
        line_total = discounted_unit_price * requested_item.quantity

        line_items.append(
            QuoteLineItem(
                item_name=requested_item.item_name,
                quantity=requested_item.quantity,
                catalog_unit_price=round(unit_price, 4),
                discount_rate=discount,
                unit_price=round(discounted_unit_price, 4),
                line_total=round(line_total, 2),
            )
        )

    if historical_search_terms:
        search_terms = historical_search_terms
    else:
        search_terms = []

        if customer_request.job_type:
            search_terms.append(customer_request.job_type)

        if customer_request.event_type:
            search_terms.append(customer_request.event_type)

        for item in customer_request.items:
            search_terms.append(item.item_name)

    historical_quotes = find_similar_historical_quotes(search_terms)
    total_amount = round(sum(item.line_total for item in line_items), 2)

    return QuoteResult(
        request_date=customer_request.request_date,
        line_items=line_items,
        total_amount=total_amount,
        quote_explanation=(
            f"Quote is based on current unit prices, quantity discounts, "
            f"and {len(historical_quotes)} similar historical quote(s)."
        ),
        historical_quotes_used=len(historical_quotes),
    )

## Tools for ordering agent

def record_customer_sale(
    item_name: str,
    quantity: int,
    total_price: float,
    date: Union[str, datetime],
) -> int:
    """Record a customer sale after confirming stock is available."""
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    date_str = normalize_date(date)
    inventory_check = check_inventory_for_item(item_name, quantity, date_str)

    if not inventory_check.can_fulfill_now:
        raise ValueError(
            f"Not enough stock for {item_name}. "
            f"Requested {quantity}, available {inventory_check.available_quantity}."
        )

    return create_transaction(
        item_name=item_name,
        transaction_type="sales",
        quantity=quantity,
        price=round(total_price, 2),
        date=date_str,
    )

def recommend_restock_order(
    item_name: str,
    shortage: int,
    as_of_date: Union[str, datetime],
) -> RestockRecommendation:
    """Recommend a supplier order that covers a shortage and restores minimum stock."""
    if shortage <= 0:
        raise ValueError("shortage must be greater than 0")

    date_str = normalize_date(as_of_date)
    item = get_inventory_item(item_name)
    min_stock_level = int(item["min_stock_level"])
    unit_price = float(item["unit_price"])
    suggested_order_quantity = shortage + min_stock_level

    return RestockRecommendation(
        item_name=item_name,
        shortage=shortage,
        suggested_order_quantity=suggested_order_quantity,
        estimated_delivery_date=get_supplier_delivery_date(date_str, suggested_order_quantity),
        estimated_cost=round(suggested_order_quantity * unit_price, 2),
    )

def record_supplier_restock(
    recommendation: RestockRecommendation,
    date: Union[str, datetime],
) -> int:
    """Record a supplier stock order if there is enough cash available."""
    date_str = normalize_date(date)
    cash_balance = get_cash_balance(date_str)

    if cash_balance < recommendation.estimated_cost:
        raise ValueError(
            f"Insufficient cash to restock {recommendation.item_name}. "
            f"Needed ${recommendation.estimated_cost:.2f}, available ${cash_balance:.2f}."
        )

    return create_transaction(
        item_name=recommendation.item_name,
        transaction_type="stock_orders",
        quantity=recommendation.suggested_order_quantity,
        price=recommendation.estimated_cost,
        date=date_str,
    )

def fulfill_customer_request(
    customer_request: CustomerRequest,
    quote: QuoteResult,
    inventory_result: InventoryResult,
) -> OrderResult:
    """Record sales for available items and supplier orders for any shortages."""
    customer_request = keep_known_request_items(customer_request)
    transaction_ids = []
    restock_recommendations = []

    if not customer_request.items:
        return OrderResult(
            request_date=customer_request.request_date,
            sales_recorded=False,
            restocks_recorded=False,
            transaction_ids=[],
            restock_recommendations=[],
            message="No exact in-stock catalog items with valid quantities were found in the request.",
        )

    if inventory_result.all_items_available:
        for line_item in quote.line_items:
            transaction_ids.append(
                record_customer_sale(
                    line_item.item_name,
                    line_item.quantity,
                    line_item.line_total,
                    customer_request.request_date,
                )
            )

        return OrderResult(
            request_date=customer_request.request_date,
            sales_recorded=True,
            restocks_recorded=False,
            transaction_ids=transaction_ids,
            restock_recommendations=[],
            message="Customer sale recorded successfully.",
        )

    for check in inventory_result.checks:
        if check.shortage > 0:
            recommendation = recommend_restock_order(
                check.item_name,
                check.shortage,
                customer_request.request_date,
            )
            restock_recommendations.append(recommendation)
            transaction_ids.append(
                record_supplier_restock(recommendation, customer_request.request_date)
            )

    return OrderResult(
        request_date=customer_request.request_date,
        sales_recorded=False,
        restocks_recorded=bool(restock_recommendations),
        transaction_ids=transaction_ids,
        restock_recommendations=restock_recommendations,
        message="Restock order(s) recorded. Customer sale should wait until stock arrives.",
    )

## Tool for orchestrator agent

def build_customer_message(
    customer_request: CustomerRequest,
    quote: QuoteResult,
    order: OrderResult,
) -> str:
    """Build a complete customer response without exposing internal business data."""
    message_parts = []

    if quote.line_items:
        line_details = []
        for item in quote.line_items:
            pricing = (
                f"{item.quantity} x {item.item_name} at ${item.unit_price:.2f} each "
                f"= ${item.line_total:.2f}"
            )
            if item.discount_rate > 0:
                pricing += (
                    f" ({item.discount_rate:.0%} bulk discount applied to the "
                    f"${item.catalog_unit_price:.2f} catalog price)"
                )
            line_details.append(pricing)

        message_parts.append("Quote details: " + "; ".join(line_details) + ".")
        message_parts.append(f"Total quote: ${quote.total_amount:.2f}.")
    else:
        message_parts.append("No catalog items were available to quote.")

    if order.sales_recorded and order.restocks_recorded:
        message_parts.append(
            "Available items were processed, while items with insufficient stock require restocking."
        )
    elif order.sales_recorded:
        message_parts.append("All quoted items were available and the sale was recorded.")
    elif order.restocks_recorded:
        message_parts.append(
            "The order cannot be fully completed now because stock is insufficient; "
            "supplier restock requests were placed."
        )
    else:
        message_parts.append("No sale or restock transaction was recorded for this request.")

    if order.restock_recommendations:
        restock_details = [
            (
                f"{item.item_name}: {item.shortage} requested units were unavailable; "
                f"estimated restock delivery is {item.estimated_delivery_date}"
            )
            for item in order.restock_recommendations
        ]
        message_parts.append("Restock details: " + "; ".join(restock_details) + ".")

    if customer_request.unmatched_items:
        message_parts.append(
            "We could not quote these unsupported products: "
            + ", ".join(customer_request.unmatched_items)
            + "."
        )

    return " ".join(message_parts)

############
## Agents ##
############

request_parser_agent = Agent(
    model,
    output_type=CustomerRequest,
    system_prompt=(
        "You are a request parsing agent for Munder Difflin Paper Company. "
        "Extract requested inventory items and quantities from customer text. "
        "You must use only exact item_name values from the provided inventory catalog. "
        "Do not return any item_name that is not copied exactly from that catalog. "
        "If the customer uses a casual, plural, partial, or descriptive name, "
        "choose the closest exact catalog item. "
        "Keep quantities separate from item names; for example, return item_name='Flyers' "
        "and quantity=5000, never item_name='5,000 flyers'. "
        "If there is no clear catalog match, place the customer's original product name "
        "in unmatched_items and do not include it in items. "
        "Return only a CustomerRequest object."
    ),
)

def run_request_parser_agent(
    raw_request: str,
    request_date: str,
    job_type: Optional[str] = None,
    event_type: Optional[str] = None,
) -> CustomerRequest:
    """Parse raw customer text into a structured CustomerRequest."""
    available_items = get_available_item_names()

    prompt = (
        "Parse this customer request into structured data.\n\n"
        f"Request date: {request_date}\n"
        f"Job type: {job_type}\n"
        f"Event type: {event_type}\n\n"
        "Inventory catalog rules:\n"
        "- You must choose item_name values only from the exact list below.\n"
        "- Never invent, shorten, pluralize, or paraphrase item names.\n"
        "- Keep quantities separate from item names; use item_name='Flyers' and quantity=5000, not item_name='5,000 flyers'.\n"
        "- If the customer says a partial/common name, map it to the closest exact item name from the list.\n"
        "- Example: if the list contains 'Party streamers' and the customer says 'streamers', use 'Party streamers'.\n"
        "- If no exact catalog item is a clear match, add its original product name to unmatched_items.\n"
        "- Never include an unmatched product in items.\n"
        "- Only include items with a clear positive numeric quantity; if quantity is missing or zero, omit the item.\n\n"
        "Exact allowed item_name values:\n"
        f"{available_items}\n\n"
        "Customer request:\n"
        f"{raw_request}"
    )

    result = request_parser_agent.run_sync(prompt)
    parsed_request = result.output
    return keep_known_request_items(parsed_request)

inventory_agent = Agent(
    model,
    output_type=InventoryResult,
    tools=[list_available_inventory, check_inventory_for_request],
    system_prompt=(
        "You are the Inventory Agent for Munder Difflin Paper Company. "
        "Your job is to check whether requested paper products are available "
        "as of the request date. You may inspect list_available_inventory, then call "
        "check_inventory_for_request exactly once and return its result without recalculating it. "
        "Use item names exactly as they appear in the CustomerRequest. "
        "Only process entries in CustomerRequest.items; do not extract additional items "
        "from original_request. "
        "Do not rewrite, shorten, or infer alternate item names when calling tools. "
        "Return an InventoryResult. Do not quote prices, place orders, or record transactions."
    ),
)

def run_inventory_agent(customer_request: CustomerRequest) -> InventoryResult:
    """Run the inventory agent for a structured customer request."""
    customer_request = agent_safe_customer_request(customer_request)
    prompt = (
        "Check inventory for this customer request:\n"
        f"{customer_request.model_dump_json(indent=2)}"
    )

    result = inventory_agent.run_sync(prompt)
    return result.output

quoting_agent = Agent(
    model,
    output_type=QuoteResult,
    tools=[create_quote_for_request],
    system_prompt=(
        "You are the Quoting Agent for Munder Difflin Paper Company. "
        "Your job is to create accurate customer quotes using current inventory prices, "
        "bulk discounts, and similar historical quotes. "
        "Use item names exactly as they appear in the CustomerRequest. "
        "Only quote entries in CustomerRequest.items; do not extract additional items "
        "from original_request. "
        "Do not rewrite, shorten, or infer alternate item names when calling tools. "
        "Call create_quote_for_request exactly once and return its result without recalculating it, "
        "so every line item includes catalog price and discount details. "
        "Return a QuoteResult. Do not check inventory availability, record sales, "
        "or place supplier orders."
    ),
)

def run_quoting_agent(customer_request: CustomerRequest) -> QuoteResult:
    """Run the quoting agent for a structured customer request."""
    customer_request = agent_safe_customer_request(customer_request)
    prompt = (
        "Create a quote for this customer request:\n"
        f"{customer_request.model_dump_json(indent=2)}"
    )

    result = quoting_agent.run_sync(prompt)
    return result.output

ordering_agent = Agent(
    model,
    output_type=OrderResult,
    tools=[fulfill_customer_request],
    system_prompt=(
        "You are the Ordering Agent for Munder Difflin Paper Company. "
        "Your job is to record customer sales when inventory is available and "
        "record supplier restock orders when inventory is short. "
        "Call fulfill_customer_request exactly once and return its result without recalculating it. "
        "Use item names exactly as they appear in the CustomerRequest, InventoryResult, "
        "and QuoteResult. Only process entries in those structured fields; do not extract "
        "additional items from original_request. Do not rewrite, shorten, or infer alternate "
        "item names when calling tools. "
        "Return an OrderResult. Do not generate new quotes or change quoted prices."
    ),
)

def run_ordering_agent(
    customer_request: CustomerRequest,
    quote: QuoteResult,
    inventory_result: InventoryResult,
) -> OrderResult:
    """Run the ordering agent after inventory and quoting are complete."""
    customer_request = agent_safe_customer_request(customer_request)
    prompt = (
        "Process this customer request using the inventory result and quote.\n\n"
        "Customer request:\n"
        f"{customer_request.model_dump_json(indent=2)}\n\n"
        "Inventory result:\n"
        f"{inventory_result.model_dump_json(indent=2)}\n\n"
        "Quote:\n"
        f"{quote.model_dump_json(indent=2)}"
    )

    result = ordering_agent.run_sync(prompt)
    return result.output

def get_financial_snapshot(as_of_date: str) -> FinancialSnapshot:
    """Agent tool wrapper around generate_financial_report for internal audits."""
    report = generate_financial_report(as_of_date)
    return FinancialSnapshot(
        request_date=str(report["as_of_date"]),
        cash_balance=float(report["cash_balance"]),
        inventory_value=float(report["inventory_value"]),
        total_assets=float(report["total_assets"]),
    )

orchestration_agent = Agent(
    model,
    output_type=OrchestratorResponse,
    tools=[
        run_inventory_agent,
        run_quoting_agent,
        run_ordering_agent,
        build_customer_message,
        get_financial_snapshot,
    ],
    system_prompt=(
        "You are the Orchestration Agent for Munder Difflin Paper Company. "
        "Process the supplied CustomerRequest in this exact order: "
        "1. Call run_inventory_agent exactly once. "
        "2. Call run_quoting_agent exactly once. "
        "3. Call run_ordering_agent exactly once using the unchanged inventory "
        "and quote results. "
        "4. Call build_customer_message exactly once. "
        "5. Call get_financial_snapshot exactly once for internal audit logging only. "
        "Return an OrchestratorResponse containing the unchanged tool results. "
        "Do not calculate prices, inventory, shortages, or transactions yourself. "
        "Do not directly modify inventory or transactions except through the ordering agent. "
        "Never include cash balances, inventory values, total assets, supplier costs, "
        "or other internal financial details in customer_message."
    ),
)

def run_orchestration_agent(customer_request: CustomerRequest) -> OrchestratorResponse:
    """Use the orchestration agent to coordinate the complete workflow."""
    customer_request = keep_known_request_items(customer_request)

    prompt = (
        "Process this validated customer request through the complete workflow:\n\n"
        f"{customer_request.model_dump_json(indent=2)}"
    )

    result = orchestration_agent.run_sync(prompt)
    return result.output

#############################
## Test multi agent system ##
#############################

def run_test_scenarios():
    print("Initializing Database...")
    init_database(db_engine)

    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"],
            format="%m/%d/%y",
            errors="coerce",
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    snapshot = get_financial_snapshot(initial_date)
    current_cash = snapshot.cash_balance
    current_inventory = snapshot.inventory_value

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx + 1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        try:
            customer_request = run_request_parser_agent(
                raw_request=row["request"],
                request_date=request_date,
                job_type=row["job"],
                event_type=row["event"],
            )
            orchestrator_response = run_orchestration_agent(customer_request)
            response = orchestrator_response.customer_message
        except Exception as e:
            print(f"Internal processing error for request {idx + 1}: {e}")
            response = (
                "We could not complete this request. "
                "Please contact customer service for assistance."
            )

        snapshot = get_financial_snapshot(request_date)
        current_cash = snapshot.cash_balance
        current_inventory = snapshot.inventory_value

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append({
            "request_id": idx + 1,
            "request_date": request_date,
            "cash_balance": current_cash,
            "inventory_value": current_inventory,
            "response": response,
        })

        time.sleep(1)

    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_snapshot = get_financial_snapshot(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_snapshot.cash_balance:.2f}")
    print(f"Final Inventory: ${final_snapshot.inventory_value:.2f}")

    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results

if __name__ == "__main__":
    results = run_test_scenarios()
