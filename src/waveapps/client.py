"""
WaveApp API Client

Handles GraphQL queries and mutations for WaveApp integration.
"""

import requests
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from .models import Customer, Product, Invoice, InvoiceItem


logger = logging.getLogger(__name__)


class WaveAppClient:
    """Client for interacting with WaveApp's GraphQL API"""
    
    BASE_URL = "https://gql.waveapps.com/graphql/public"
    
    def __init__(self, api_token: str, business_id: str):
        """
        Initialize WaveApp client
        
        Args:
            api_token: WaveApp API token
            business_id: WaveApp business ID
        """
        self.api_token = api_token
        self.business_id = business_id
        self.customers_cache: Optional[List[Customer]] = None
        self.products_cache: Optional[List[Product]] = None
        
    def _execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query against WaveApp API
        
        Args:
            query: GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            Response data from the API
            
        Raises:
            Exception: If the API request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            
        try:
            response = requests.post(self.BASE_URL, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for GraphQL errors
            if "errors" in data:
                error_messages = [err.get("message", str(err)) for err in data["errors"]]
                raise Exception(f"GraphQL errors: {', '.join(error_messages)}")
                
            return data.get("data", {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise Exception(f"Failed to execute WaveApp query: {e}")
    
    def get_customers(self, force_refresh: bool = False) -> List[Customer]:
        """
        Fetch all customers for the business
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            List of Customer objects
        """
        if self.customers_cache and not force_refresh:
            return self.customers_cache
            
        query = """
        query GetCustomers($businessId: ID!) {
          business(id: $businessId) {
            customers(page: 1, pageSize: 1000) {
              edges {
                node {
                  id
                  name
                  email
                }
              }
            }
          }
        }
        """
        
        variables = {"businessId": self.business_id}
        
        try:
            data = self._execute_query(query, variables)
            edges = data.get("business", {}).get("customers", {}).get("edges", [])
            
            customers = [
                Customer(
                    id=edge["node"]["id"],
                    name=edge["node"]["name"],
                    email=edge["node"].get("email")
                )
                for edge in edges
            ]
            
            self.customers_cache = customers
            logger.info(f"Fetched {len(customers)} customers from WaveApp")
            return customers
            
        except Exception as e:
            logger.error(f"Failed to fetch customers: {e}")
            raise
    
    def get_products(self, force_refresh: bool = False) -> List[Product]:
        """
        Fetch all products/services for the business
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            List of Product objects
        """
        if self.products_cache and not force_refresh:
            return self.products_cache
            
        query = """
        query GetProducts($businessId: ID!) {
          business(id: $businessId) {
            products(page: 1, pageSize: 500) {
              edges {
                node {
                  id
                  name
                  description
                  unitPrice
                  isSold
                  incomeAccount {
                    id
                    name
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {"businessId": self.business_id}
        
        try:
            data = self._execute_query(query, variables)
            edges = data.get("business", {}).get("products", {}).get("edges", [])
            
            products = [
                Product(
                    id=edge["node"]["id"],
                    name=edge["node"]["name"],
                    price=float(edge["node"].get("unitPrice", 0)),
                    description=edge["node"].get("description", "")
                )
                for edge in edges
                if edge["node"].get("isSold", True)  # Only include products marked for sale
            ]
            
            self.products_cache = products
            logger.info(f"Fetched {len(products)} products from WaveApp")
            return products
            
        except Exception as e:
            logger.error(f"Failed to fetch products: {e}")
            raise
    
    def create_invoice(self, invoice: Invoice) -> Invoice:
        """
        Create an invoice in WaveApp
        
        Args:
            invoice: Invoice object with customer_id, items, and dates
            
        Returns:
            Updated Invoice object with invoice_id, invoice_number, total, and view_url
        """
        # Build line items for the mutation
        items_input = []
        for item in invoice.items:
            items_input.append({
                "productId": item.product_id,
                "quantity": str(item.quantity),  # GraphQL expects string for Decimal
                "description": item.description
            })
        
        mutation = """
        mutation CreateInvoice($input: InvoiceCreateInput!) {
          invoiceCreate(input: $input) {
            invoice {
              id
              invoiceNumber
              total {
                value
                currency {
                  code
                }
              }
              viewUrl
            }
            didSucceed
            inputErrors {
              message
              path
            }
          }
        }
        """
        
        # Prepare invoice input
        invoice_input = {
            "businessId": self.business_id,
            "customerId": invoice.customer_id,
            "items": items_input,
            "invoiceDate": invoice.invoice_date.strftime("%Y-%m-%d")
        }
        
        if invoice.due_date:
            invoice_input["dueDate"] = invoice.due_date.strftime("%Y-%m-%d")
        
        variables = {"input": invoice_input}
        
        try:
            data = self._execute_query(mutation, variables)
            result = data.get("invoiceCreate", {})
            
            if not result.get("didSucceed"):
                errors = result.get("inputErrors", [])
                error_messages = [err.get("message", str(err)) for err in errors]
                raise Exception(f"Invoice creation failed: {', '.join(error_messages)}")
            
            # Update invoice with response data
            invoice_data = result.get("invoice", {})
            invoice.invoice_id = invoice_data.get("id")
            invoice.invoice_number = invoice_data.get("invoiceNumber")
            invoice.total = float(invoice_data.get("total", {}).get("value", 0))
            invoice.view_url = invoice_data.get("viewUrl")
            
            logger.info(f"Created invoice {invoice.invoice_number} for customer {invoice.customer_id}")
            return invoice
            
        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            raise
    
    def get_customer_by_name(self, name: str) -> Optional[Customer]:
        """
        Find a customer by name (case-insensitive)
        
        Args:
            name: Customer name to search for
            
        Returns:
            Customer object if found, None otherwise
        """
        customers = self.get_customers()
        name_lower = name.lower()
        
        for customer in customers:
            if customer.name.lower() == name_lower:
                return customer
        
        return None
    
    def get_product_by_name(self, name: str) -> Optional[Product]:
        """
        Find a product by name (case-insensitive)
        
        Args:
            name: Product name to search for
            
        Returns:
            Product object if found, None otherwise
        """
        products = self.get_products()
        name_lower = name.lower()
        
        for product in products:
            if product.name.lower() == name_lower:
                return product
        
        return None
    
    def get_draft_invoices(self, customer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch draft invoices for the business
        
        Args:
            customer_id: Optional customer ID to filter drafts
            
        Returns:
            List of draft invoice dictionaries
        """
        query = """
        query GetDraftInvoices($businessId: ID!) {
          business(id: $businessId) {
            invoices(page: 1, pageSize: 100, status: DRAFT) {
              edges {
                node {
                  id
                  invoiceNumber
                  invoiceDate
                  customer {
                    id
                    name
                  }
                  items {
                    product {
                      id
                      name
                    }
                    quantity
                    description
                  }
                  total {
                    value
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {"businessId": self.business_id}
        
        try:
            data = self._execute_query(query, variables)
            edges = data.get("business", {}).get("invoices", {}).get("edges", [])
            
            drafts = []
            for edge in edges:
                node = edge["node"]
                draft_customer_id = node.get("customer", {}).get("id")
                
                # Filter by customer if specified
                if customer_id and draft_customer_id != customer_id:
                    continue
                
                drafts.append({
                    "id": node.get("id"),
                    "invoice_number": node.get("invoiceNumber"),
                    "invoice_date": node.get("invoiceDate"),
                    "customer_id": draft_customer_id,
                    "customer_name": node.get("customer", {}).get("name"),
                    "items": node.get("items", []),
                    "total": float(node.get("total", {}).get("value", 0))
                })
            
            logger.info(f"Found {len(drafts)} draft invoices")
            return drafts
            
        except Exception as e:
            logger.error(f"Failed to fetch draft invoices: {e}")
            return []
    
    def update_invoice(self, invoice_id: str, invoice: Invoice, existing_draft: Dict[str, Any]) -> Invoice:
        """
        Update an existing draft invoice in WaveApp by appending new items
        
        Args:
            invoice_id: ID of the draft invoice to update
            invoice: Invoice object with new data to append
            existing_draft: Existing draft invoice data from get_draft_invoices()
            
        Returns:
            Updated Invoice object
        """
        # Merge existing draft items with new items
        # Group by product_id and combine quantities and descriptions
        merged_items = {}
        
        # Add existing draft items
        for existing_item in existing_draft.get('items', []):
            product_id = existing_item.get('product', {}).get('id')
            if product_id:
                quantity = float(existing_item.get('quantity', 0))
                description = existing_item.get('description', '')
                merged_items[product_id] = {
                    'quantity': quantity,
                    'descriptions': [description] if description else []
                }
        
        # Add/merge new items
        for item in invoice.items:
            if item.product_id in merged_items:
                # Append to existing item
                merged_items[item.product_id]['quantity'] += item.quantity
                if item.description:
                    merged_items[item.product_id]['descriptions'].append(item.description)
            else:
                # New item
                merged_items[item.product_id] = {
                    'quantity': item.quantity,
                    'descriptions': [item.description] if item.description else []
                }
        
        # Build line items for the mutation
        items_input = []
        for product_id, item_data in merged_items.items():
            # Combine all descriptions with separator
            combined_description = ' | '.join(item_data['descriptions'])
            items_input.append({
                "productId": product_id,
                "quantity": str(item_data['quantity']),
                "description": combined_description
            })
        
        mutation = """
        mutation UpdateInvoice($input: InvoiceUpdateInput!) {
          invoiceUpdate(input: $input) {
            invoice {
              id
              invoiceNumber
              total {
                value
                currency {
                  code
                }
              }
              viewUrl
            }
            didSucceed
            inputErrors {
              message
              path
            }
          }
        }
        """
        
        # Prepare invoice input
        invoice_input = {
            "invoiceId": invoice_id,
            "customerId": invoice.customer_id,
            "items": items_input,
            "invoiceDate": invoice.invoice_date.strftime("%Y-%m-%d")
        }
        
        if invoice.due_date:
            invoice_input["dueDate"] = invoice.due_date.strftime("%Y-%m-%d")
        
        variables = {"input": invoice_input}
        
        try:
            data = self._execute_query(mutation, variables)
            result = data.get("invoiceUpdate", {})
            
            if not result.get("didSucceed"):
                errors = result.get("inputErrors", [])
                error_messages = [err.get("message", str(err)) for err in errors]
                raise Exception(f"Invoice update failed: {', '.join(error_messages)}")
            
            # Update invoice with response data
            invoice_data = result.get("invoice", {})
            invoice.invoice_id = invoice_data.get("id")
            invoice.invoice_number = invoice_data.get("invoiceNumber")
            invoice.total = float(invoice_data.get("total", {}).get("value", 0))
            invoice.view_url = invoice_data.get("viewUrl")
            
            logger.info(f"Updated invoice {invoice.invoice_number} (ID: {invoice_id})")
            return invoice
            
        except Exception as e:
            logger.error(f"Failed to update invoice: {e}")
            raise
