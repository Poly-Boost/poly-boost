"""
Generic pagination utility for Telegram bot list displays.

Provides stateless pagination logic and inline keyboard generation
for handling paginated lists in the Telegram bot.
"""

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

    @property
    def start_index(self) -> int:
        """0-based start index of first item on current page."""
        return (self.page - 1) * self.page_size

    @property
    def end_index(self) -> int:
        """0-based end index (exclusive) of last item on current page."""
        return self.start_index + len(self.items)

    def is_empty(self) -> bool:
        """True if no items in entire dataset."""
        return self.total_items == 0

    def is_single_page(self) -> bool:
        """True if only one page exists (no pagination needed)."""
        return self.total_pages <= 1


class PaginationHelper:
    """
    Utility class for paginating lists in Telegram bot.

    Provides stateless pagination logic and inline keyboard generation.
    No instance state required - all methods are static.
    """

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

        Example:
            >>> items = ["a", "b", "c", "d", "e"]
            >>> paginated = PaginationHelper.paginate(items, page=1, page_size=2)
            >>> assert paginated.items == ["a", "b"]
            >>> assert paginated.page == 1
            >>> assert paginated.total_pages == 3
            >>> assert paginated.has_next == True
            >>> assert paginated.has_prev == False
        """
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

    @staticmethod
    def create_pagination_keyboard(
        paginated_data: PaginatedData,
        callback_prefix: str,
        additional_buttons: Optional[List[List[InlineKeyboardButton]]] = None
    ) -> InlineKeyboardMarkup:
        """
        Create inline keyboard with pagination navigation.

        Generates Previous / Page X/Y / Next buttons.
        Hides pagination if only one page or empty list.

        Args:
            paginated_data: PaginatedData with pagination metadata.
            callback_prefix: Prefix for callback_data (e.g., "pos_page" -> "pos_page_2").
            additional_buttons: Optional additional button rows to append below pagination.

        Returns:
            InlineKeyboardMarkup with pagination buttons (and additional buttons if provided).

        Example:
            >>> paginated = PaginationHelper.paginate(items, page=2, page_size=10)
            >>> keyboard = PaginationHelper.create_pagination_keyboard(
            ...     paginated,
            ...     callback_prefix="pos_page"
            ... )
            >>> # Result: [[Previous, Page 2/5, Next]]
        """
        buttons = []

        # Hide pagination for empty lists or single page
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
