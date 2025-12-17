"""
Data models for WaveApp entities
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class Customer:
    """Represents a WaveApp customer (client)"""
    id: str
    name: str
    email: Optional[str] = None
    
    def __repr__(self):
        return f"Customer(id={self.id}, name={self.name})"


@dataclass
class Product:
    """
    Represents a WaveApp product/service
    Note: price is stored for reference only - WaveApp calculates line item totals automatically
    """
    id: str
    name: str
    price: float  # defaultSellPrice from WaveApp
    description: Optional[str] = None
    
    def __repr__(self):
        return f"Product(id={self.id}, name={self.name}, price={self.price})"


@dataclass
class InvoiceItem:
    """
    Represents a line item on an invoice
    WaveApp automatically calculates total as: Product.defaultSellPrice × quantity
    """
    product_id: str
    quantity: float  # Hours worked
    description: str  # Aggregated notes from all time entries for this service
    
    def __repr__(self):
        return f"InvoiceItem(product_id={self.product_id}, quantity={self.quantity})"


@dataclass
class Invoice:
    """Represents a WaveApp invoice"""
    customer_id: str
    items: List[InvoiceItem]
    invoice_date: datetime = field(default_factory=datetime.now)
    due_date: Optional[datetime] = None
    
    # These will be populated after invoice creation
    invoice_id: Optional[str] = None
    invoice_number: Optional[str] = None
    total: Optional[float] = None
    view_url: Optional[str] = None
    
    def __repr__(self):
        return f"Invoice(customer_id={self.customer_id}, items={len(self.items)})"
