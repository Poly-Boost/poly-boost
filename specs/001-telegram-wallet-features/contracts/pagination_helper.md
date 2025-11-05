# PaginationHelper Contract

**Module**: `poly_boost.bot.utils.pagination`
**Purpose**: Generic pagination utility for Telegram bot list displays
**Pattern**: Stateless utility class with static methods

## Class Definition

```python
from typing import TypeVar, Generic, List, Optional
from dataclasses import dataclass
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

T = TypeVar('T')


@dataclass
class PaginatedData(Generic[T]):
    """
    Container for paginated list data.

    Generic type T can be Position, Order, Activity, or any list item type.
    Immutable dataclass for type safety.
    """

    items: List[T]
    """Items on current page (max page_size items)."""

    page: int
    """Current page number (1-indexed)."""

    page_size: int
    """Items per page (typically 10)."""

    total_items: int
    """Total items across all pages."""

    total_pages: int
    """Total pages (calculated from total_items and page_size)."""

    has_next: bool
    """True if there are more pages after current."""

    has_prev: bool
    """True if there are pages before current."""


class PaginationHelper:
    """
    Utility class for paginating lists in Telegram bot.

    Provides stateless pagination logic and inline keyboard generation.
    No instance state required - all methods are static.
    """
```

## Interface Methods

### 1. paginate

**Signature**:
```python
@staticmethod
def paginate(
    items: List[T],
    page: int = 1,
    page_size: int = 10
) -> PaginatedData[T]:
    """
    Paginate a list of items.

    Args:
        items: Full list of items to paginate.
        page: Page number to retrieve (1-indexed). Default: 1.
        page_size: Number of items per page. Default: 10.

    Returns:
        PaginatedData[T] containing current page items and metadata.

    Raises:
        ValueError: If page < 1 or page_size < 1.

    Preconditions:
        - items can be empty list (returns empty page)
        - page must be >= 1 (auto-clamped if out of range)
        - page_size must be >= 1

    Postconditions:
        - Returns PaginatedData with items for current page
        - total_pages calculated as ceil(total_items / page_size)
        - has_next = True if page < total_pages
        - has_prev = True if page > 1
        - If page > total_pages, clamps to total_pages (returns last page)
        - If items is empty, returns empty page with total_pages = 0

    Example:
        >>> items = ["a", "b", "c", "d", "e"]
        >>> paginated = PaginationHelper.paginate(items, page=1, page_size=2)
        >>> assert paginated.items == ["a", "b"]
        >>> assert paginated.page == 1
        >>> assert paginated.total_pages == 3
        >>> assert paginated.has_next == True
        >>> assert paginated.has_prev == False
    """
```

**Business Rules**:
- **Page Clamping**: If page > total_pages and total_pages > 0, clamp to total_pages (return last page)
- **Page Clamping**: If page < 1, clamp to 1 (return first page)
- **Empty List**: If items is empty, return PaginatedData with empty items list and total_pages = 0
- **Partial Last Page**: Last page may have fewer items than page_size (e.g., 11 items with page_size=10 → page 2 has 1 item)
- **Calculation**: `total_pages = ceil(total_items / page_size)` using integer division: `(total_items + page_size - 1) // page_size`

**Edge Cases**:
| Input | Output |
|-------|--------|
| items=[], page=1 | PaginatedData(items=[], page=1, total_items=0, total_pages=0, has_next=False, has_prev=False) |
| items=[1,2,3], page=5 | PaginatedData(items=[3], page=1, ...) ← clamped to page 1 |
| items=[1...15], page=2, page_size=10 | PaginatedData(items=[11,12,13,14,15], page=2, total_pages=2, has_next=False, has_prev=True) |

**Implementation Details**:
```python
@staticmethod
def paginate(items: List[T], page: int = 1, page_size: int = 10) -> PaginatedData[T]:
    total_items = len(items)

    # Validate inputs
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    if page < 1:
        raise ValueError("page must be >= 1")

    # Calculate total pages
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0

    # Clamp page to valid range
    if total_pages > 0 and page > total_pages:
        page = total_pages
    elif page < 1:
        page = 1

    # Calculate slice indices
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    page_items = items[start_index:end_index]

    return PaginatedData(
        items=page_items,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=(page < total_pages),
        has_prev=(page > 1)
    )
```

---

### 2. create_pagination_keyboard

**Signature**:
```python
@staticmethod
def create_pagination_keyboard(
    paginated_data: PaginatedData,
    callback_prefix: str,
    additional_buttons: Optional[List[List[InlineKeyboardButton]]] = None
) -> InlineKeyboardMarkup:
    """
    Create inline keyboard with pagination navigation.

    Generates ⬅️ Previous / Page X/Y / Next ➡️ buttons.
    Hides pagination if only one page or empty list.

    Args:
        paginated_data: PaginatedData with pagination metadata.
        callback_prefix: Prefix for callback_data (e.g., "pos_page" → "pos_page_2").
        additional_buttons: Optional additional button rows to append below pagination.

    Returns:
        InlineKeyboardMarkup with pagination buttons (and additional buttons if provided).

    Raises:
        None (safe to call with any PaginatedData).

    Preconditions:
        - paginated_data must be valid PaginatedData instance
        - callback_prefix should be unique per list type (e.g., "pos_page", "order_page")

    Postconditions:
        - Returns InlineKeyboardMarkup with navigation buttons
        - If total_pages <= 1, returns empty keyboard (or only additional_buttons)
        - Previous button shown only if has_prev = True
        - Next button shown only if has_next = True
        - Middle button always shows "Page X/Y" (not clickable)

    Example:
        >>> paginated = PaginationHelper.paginate(items, page=2, page_size=10)
        >>> keyboard = PaginationHelper.create_pagination_keyboard(
        ...     paginated,
        ...     callback_prefix="pos_page"
        ... )
        >>> # Result: [[⬅️ Previous, Page 2/5, Next ➡️]]
    """
```

**Business Rules**:
- **Hide Pagination**: If `total_pages <= 1`, return empty keyboard (no pagination needed)
- **Hide Pagination**: If `is_empty() = True`, return empty keyboard per FR-007
- **Previous Button**: Only show if `has_prev = True`
- **Next Button**: Only show if `has_next = True`
- **Page Indicator**: Middle button shows "Page {current}/{total}" (callback_data="noop" to prevent interaction)
- **Additional Buttons**: Appended below pagination row (useful for "Back" button, etc.)

**Button Layout Examples**:

```
# Page 1 of 5:
[Page 1/5] [Next ➡️]

# Page 3 of 5:
[⬅️ Previous] [Page 3/5] [Next ➡️]

# Page 5 of 5:
[⬅️ Previous] [Page 5/5]

# Single page (hide pagination):
(no buttons)

# With additional buttons:
[⬅️ Previous] [Page 2/3] [Next ➡️]
[🔙 Back to Menu]
```

**Callback Data Format**:
```
Previous button: "{callback_prefix}_{page - 1}"
Next button: "{callback_prefix}_{page + 1}"
Page indicator: "noop" (ignored by bot)

Examples:
- "pos_page_1" (positions page 1)
- "order_page_3" (orders page 3)
- "activity_page_2" (activities page 2)
```

**Implementation Details**:
```python
@staticmethod
def create_pagination_keyboard(
    paginated_data: PaginatedData,
    callback_prefix: str,
    additional_buttons: Optional[List[List[InlineKeyboardButton]]] = None
) -> InlineKeyboardMarkup:
    buttons = []

    # Hide pagination for empty lists or single page (per FR-007)
    if paginated_data.total_pages > 1:
        nav_buttons = []

        # Previous button
        if paginated_data.has_prev:
            nav_buttons.append(
                InlineKeyboardButton(
                    "⬅️ Previous",
                    callback_data=f"{callback_prefix}_{paginated_data.page - 1}"
                )
            )

        # Page indicator (not clickable)
        nav_buttons.append(
            InlineKeyboardButton(
                f"Page {paginated_data.page}/{paginated_data.total_pages}",
                callback_data="noop"
            )
        )

        # Next button
        if paginated_data.has_next:
            nav_buttons.append(
                InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=f"{callback_prefix}_{paginated_data.page + 1}"
                )
            )

        buttons.append(nav_buttons)

    # Add additional buttons below pagination
    if additional_buttons:
        buttons.extend(additional_buttons)

    return InlineKeyboardMarkup(buttons)
```

---

## Helper Properties (PaginatedData)

### start_index

```python
@property
def start_index(self) -> int:
    """0-based start index of first item on current page."""
    return (self.page - 1) * self.page_size
```

### end_index

```python
@property
def end_index(self) -> int:
    """0-based end index (exclusive) of last item on current page."""
    return self.start_index + len(self.items)
```

### is_empty

```python
def is_empty(self) -> bool:
    """True if no items in entire dataset."""
    return self.total_items == 0
```

### is_single_page

```python
def is_single_page(self) -> bool:
    """True if only one page exists (no pagination needed)."""
    return self.total_pages <= 1
```

---

## Dependencies

**Required Imports**:
```python
from typing import TypeVar, Generic, List, Optional
from dataclasses import dataclass
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
```

**External Services**:
- `telegram.InlineKeyboardButton`: Telegram inline button
- `telegram.InlineKeyboardMarkup`: Telegram inline keyboard layout

---

## Error Handling Strategy

**No Exceptions**: This utility is designed to never raise exceptions in normal use.

**Defensive Programming**:
- Auto-clamp out-of-range page numbers
- Handle empty lists gracefully
- Return empty keyboard for single-page lists

**Logging**: Not required (utility logic is trivial)

---

## Testing Contract

**Unit Tests Required**:
```python
# tests/unit/bot/test_pagination_helper.py

def test_paginate_first_page():
    """First page has correct items and metadata."""

def test_paginate_middle_page():
    """Middle page has both prev and next."""

def test_paginate_last_page():
    """Last page has no next button."""

def test_paginate_single_page():
    """Single page list has no pagination buttons."""

def test_paginate_empty_list():
    """Empty list returns empty page with total_pages=0."""

def test_paginate_page_out_of_range():
    """Out-of-range page clamped to valid range."""

def test_paginate_partial_last_page():
    """Last page with fewer items than page_size."""

def test_create_keyboard_first_page():
    """First page keyboard has no Previous button."""

def test_create_keyboard_middle_page():
    """Middle page keyboard has both Previous and Next."""

def test_create_keyboard_last_page():
    """Last page keyboard has no Next button."""

def test_create_keyboard_single_page():
    """Single page keyboard is empty."""

def test_create_keyboard_empty_list():
    """Empty list keyboard is empty."""

def test_create_keyboard_with_additional_buttons():
    """Additional buttons appended below pagination."""
```

**Mock Requirements**:
- No mocks needed (pure utility functions)
- Test with sample data (lists of strings, integers, or mock Position objects)

---

## Performance Contract

**Latency Targets**:
- `paginate`: O(1) time complexity (list slice), <1ms
- `create_pagination_keyboard`: O(1) time complexity, <1ms

**Memory**:
- No internal state (stateless utility)
- PaginatedData contains only one page of items (not entire list)

**Concurrency**:
- Thread-safe (no shared state, immutable dataclass)

---

## Usage Examples

### Example 1: Paginate Positions List

```python
from poly_boost.bot.utils.pagination import PaginationHelper

# Get all positions from service
positions = position_service.get_positions(wallet)  # List[Position]

# Paginate to page 1
paginated = PaginationHelper.paginate(positions, page=1, page_size=10)

# Format message
message = f"📊 Positions (Page {paginated.page}/{paginated.total_pages})\n\n"
for i, position in enumerate(paginated.items, start=paginated.start_index):
    message += f"{i+1}. {position.market_question[:30]}... ({position.size} shares)\n"

# Create keyboard
keyboard = PaginationHelper.create_pagination_keyboard(
    paginated,
    callback_prefix="pos_page"
)

# Send to user
await update.message.reply_text(message, reply_markup=keyboard)
```

### Example 2: Handle Pagination Callback

```python
from telegram import Update
from telegram.ext import ContextTypes

async def handle_pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Parse page number from callback_data
    # Example: "pos_page_3" → page 3
    callback_data = query.data
    page = int(callback_data.split("_")[-1])

    # Re-fetch positions and paginate
    positions = position_service.get_positions(wallet)
    paginated = PaginationHelper.paginate(positions, page=page, page_size=10)

    # Format and send updated message
    message = format_positions_message(paginated)
    keyboard = PaginationHelper.create_pagination_keyboard(paginated, "pos_page")

    await query.edit_message_text(message, reply_markup=keyboard)
```

### Example 3: Empty List Handling

```python
# Get orders (may be empty)
orders = order_service.get_orders()

if not orders:
    # Show empty message (no pagination)
    await update.message.reply_text(
        "📋 Active Orders\n\n"
        "No active orders found."
    )
    return

# Paginate (pagination hidden if single page per FR-007)
paginated = PaginationHelper.paginate(orders, page=1, page_size=10)
keyboard = PaginationHelper.create_pagination_keyboard(paginated, "order_page")

# If single page, keyboard will be empty (as expected)
await update.message.reply_text(
    format_orders_message(paginated),
    reply_markup=keyboard
)
```

### Example 4: With Additional Buttons

```python
# Paginate activities
paginated = PaginationHelper.paginate(activities, page=2, page_size=10)

# Create pagination keyboard with "Back to Menu" button
additional_buttons = [
    [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
]

keyboard = PaginationHelper.create_pagination_keyboard(
    paginated,
    callback_prefix="activity_page",
    additional_buttons=additional_buttons
)

# Result:
# [⬅️ Previous] [Page 2/5] [Next ➡️]
# [🔙 Back to Menu]
```

---

## Integration Points

**Called By**:
- `poly_boost.bot.handlers.position_handler`: Position list pagination
- `poly_boost.bot.handlers.order_handler`: Order list pagination
- `poly_boost.bot.handlers.activity_handler`: Activity history pagination

**Calls**:
- `telegram.InlineKeyboardButton`: Button creation
- `telegram.InlineKeyboardMarkup`: Keyboard layout creation

---

## Type Safety

**Generic Type Support**:
```python
# Type-safe pagination for different entity types
paginated_positions: PaginatedData[Position] = PaginationHelper.paginate(positions)
paginated_orders: PaginatedData[Order] = PaginationHelper.paginate(orders)
paginated_activities: PaginatedData[Activity] = PaginationHelper.paginate(activities)

# Type checker ensures items have correct type
position: Position = paginated_positions.items[0]  # ✅ Type-safe
order: Order = paginated_orders.items[0]           # ✅ Type-safe
```

---

## Accessibility Considerations

**Button Text**:
- Use clear emoji indicators (⬅️ ➡️) for navigation
- Page indicator in format "Page X/Y" for clarity
- Avoid ambiguous labels like "<<" or ">>"

**Callback Data Naming**:
- Use consistent prefix pattern: `{entity}_page_{number}`
- Examples: `pos_page_3`, `order_page_1`, `activity_page_5`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-05 | Initial contract definition |
