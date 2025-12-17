"""
WaveApp Integration Module

This module provides integration with WaveApp's GraphQL API for invoice generation.
"""

from .client import WaveAppClient
from .models import Customer, Product, Invoice, InvoiceItem

__all__ = ['WaveAppClient', 'Customer', 'Product', 'Invoice', 'InvoiceItem']
