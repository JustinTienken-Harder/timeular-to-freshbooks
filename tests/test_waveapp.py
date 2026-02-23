"""
Tests for WaveApp integration
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from waveapps.client import WaveAppClient
from waveapps.models import Customer, Product, Invoice, InvoiceItem


class TestWaveAppClient(unittest.TestCase):
    """Test WaveApp API client"""
    
    def setUp(self):
        """Set up test client"""
        self.api_token = "test_token_123"
        self.business_id = "test_business_id"
        self.client = WaveAppClient(self.api_token, self.business_id)
    
    def test_client_initialization(self):
        """Test client initialization"""
        self.assertEqual(self.client.api_token, self.api_token)
        self.assertEqual(self.client.business_id, self.business_id)
        self.assertIsNone(self.client.customers_cache)
        self.assertIsNone(self.client.products_cache)
    
    @patch('waveapps.client.requests.post')
    def test_get_customers(self, mock_post):
        """Test fetching customers"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "business": {
                    "customers": {
                        "edges": [
                            {
                                "node": {
                                    "id": "customer_1",
                                    "name": "Test Customer",
                                    "email": "test@example.com"
                                }
                            }
                        ]
                    }
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Get customers
        customers = self.client.get_customers()
        
        # Verify
        self.assertEqual(len(customers), 1)
        self.assertEqual(customers[0].id, "customer_1")
        self.assertEqual(customers[0].name, "Test Customer")
        self.assertEqual(customers[0].email, "test@example.com")
        
        # Verify cache
        self.assertIsNotNone(self.client.customers_cache)
        
        # Test cache hit (no new API call)
        mock_post.reset_mock()
        customers2 = self.client.get_customers()
        self.assertEqual(len(customers2), 1)
        mock_post.assert_not_called()
    
    @patch('waveapps.client.requests.post')
    def test_get_products(self, mock_post):
        """Test fetching products"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "business": {
                    "products": {
                        "edges": [
                            {
                                "node": {
                                    "id": "product_1",
                                    "name": "Consulting",
                                    "unitPrice": "150.00",
                                    "description": "Hourly consulting",
                                    "isSold": True
                                }
                            }
                        ]
                    }
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Get products
        products = self.client.get_products()
        
        # Verify
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].id, "product_1")
        self.assertEqual(products[0].name, "Consulting")
        self.assertEqual(products[0].price, 150.00)
    
    @patch('waveapps.client.requests.post')
    def test_get_draft_invoices(self, mock_post):
        """Test fetching draft invoices"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "business": {
                    "invoices": {
                        "edges": [
                            {
                                "node": {
                                    "id": "invoice_draft_1",
                                    "invoiceNumber": "DRAFT-001",
                                    "invoiceDate": "2024-03-01",
                                    "customer": {
                                        "id": "customer_1",
                                        "name": "Test Customer"
                                    },
                                    "items": [
                                        {
                                            "product": {
                                                "id": "product_1",
                                                "name": "Consulting"
                                            },
                                            "quantity": "5.0",
                                            "description": "Test work"
                                        }
                                    ],
                                    "total": {
                                        "value": "750.00"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Get draft invoices
        drafts = self.client.get_draft_invoices()
        
        # Verify
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["id"], "invoice_draft_1")
        self.assertEqual(drafts[0]["invoice_number"], "DRAFT-001")
        self.assertEqual(drafts[0]["customer_id"], "customer_1")
        self.assertEqual(drafts[0]["total"], 750.00)
    
    @patch('waveapps.client.requests.post')
    def test_get_draft_invoices_filtered(self, mock_post):
        """Test fetching draft invoices filtered by customer"""
        # Mock API response with multiple drafts
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "business": {
                    "invoices": {
                        "edges": [
                            {
                                "node": {
                                    "id": "invoice_draft_1",
                                    "invoiceNumber": "DRAFT-001",
                                    "invoiceDate": "2024-03-01",
                                    "customer": {
                                        "id": "customer_1",
                                        "name": "Customer 1"
                                    },
                                    "items": [],
                                    "total": {"value": "750.00"}
                                }
                            },
                            {
                                "node": {
                                    "id": "invoice_draft_2",
                                    "invoiceNumber": "DRAFT-002",
                                    "invoiceDate": "2024-03-02",
                                    "customer": {
                                        "id": "customer_2",
                                        "name": "Customer 2"
                                    },
                                    "items": [],
                                    "total": {"value": "500.00"}
                                }
                            }
                        ]
                    }
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Get draft invoices filtered by customer
        drafts = self.client.get_draft_invoices(customer_id="customer_1")
        
        # Verify only customer_1's draft is returned
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["customer_id"], "customer_1")
    
    @patch('waveapps.client.requests.post')
    def test_create_invoice(self, mock_post):
        """Test creating an invoice"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "invoiceCreate": {
                    "didSucceed": True,
                    "invoice": {
                        "id": "invoice_123",
                        "invoiceNumber": "INV-001",
                        "total": {
                            "value": "750.00",
                            "currency": {"code": "USD"}
                        },
                        "viewUrl": "https://waveapps.com/invoice/123"
                    },
                    "inputErrors": []
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Create invoice
        items = [
            InvoiceItem(
                product_id="product_1",
                quantity=5.0,
                description="Test consulting work"
            )
        ]
        invoice = Invoice(
            customer_id="customer_1",
            items=items,
            invoice_date=datetime(2024, 3, 1)
        )
        
        result = self.client.create_invoice(invoice)
        
        # Verify
        self.assertEqual(result.invoice_id, "invoice_123")
        self.assertEqual(result.invoice_number, "INV-001")
        self.assertEqual(result.total, 750.00)
        self.assertEqual(result.view_url, "https://waveapps.com/invoice/123")
    
    @patch('waveapps.client.requests.post')
    def test_update_invoice(self, mock_post):
        """Test updating a draft invoice"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "invoiceUpdate": {
                    "didSucceed": True,
                    "invoice": {
                        "id": "invoice_draft_1",
                        "invoiceNumber": "DRAFT-001",
                        "total": {
                            "value": "900.00",
                            "currency": {"code": "USD"}
                        },
                        "viewUrl": "https://waveapps.com/invoice/draft_1"
                    },
                    "inputErrors": []
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Update invoice
        items = [
            InvoiceItem(
                product_id="product_1",
                quantity=6.0,
                description="Updated consulting work"
            )
        ]
        invoice = Invoice(
            customer_id="customer_1",
            items=items,
            invoice_date=datetime(2024, 3, 1)
        )
        
        result = self.client.update_invoice("invoice_draft_1", invoice)
        
        # Verify
        self.assertEqual(result.invoice_id, "invoice_draft_1")
        self.assertEqual(result.invoice_number, "DRAFT-001")
        self.assertEqual(result.total, 900.00)
        
        # Verify mutation was called with correct parameters
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertIn('invoiceUpdate', payload['query'])
        self.assertEqual(payload['variables']['input']['invoiceId'], 'invoice_draft_1')
    
    @patch('waveapps.client.requests.post')
    def test_create_invoice_failure(self, mock_post):
        """Test invoice creation failure"""
        # Mock API response with error
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "invoiceCreate": {
                    "didSucceed": False,
                    "invoice": None,
                    "inputErrors": [
                        {"message": "Invalid customer ID", "path": "customerId"}
                    ]
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Attempt to create invoice
        items = [InvoiceItem(product_id="product_1", quantity=5.0, description="Test")]
        invoice = Invoice(
            customer_id="invalid_customer",
            items=items,
            invoice_date=datetime(2024, 3, 1)
        )
        
        with self.assertRaises(Exception) as context:
            self.client.create_invoice(invoice)
        
        self.assertIn("Invalid customer ID", str(context.exception))


class TestWaveAppModels(unittest.TestCase):
    """Test WaveApp models"""
    
    def test_customer_model(self):
        """Test Customer model"""
        customer = Customer(
            id="customer_1",
            name="Test Customer",
            email="test@example.com"
        )
        self.assertEqual(customer.id, "customer_1")
        self.assertEqual(customer.name, "Test Customer")
        self.assertEqual(customer.email, "test@example.com")
    
    def test_product_model(self):
        """Test Product model"""
        product = Product(
            id="product_1",
            name="Consulting",
            price=150.00,
            description="Hourly consulting"
        )
        self.assertEqual(product.id, "product_1")
        self.assertEqual(product.name, "Consulting")
        self.assertEqual(product.price, 150.00)
    
    def test_invoice_item_model(self):
        """Test InvoiceItem model"""
        item = InvoiceItem(
            product_id="product_1",
            quantity=5.0,
            description="Test work"
        )
        self.assertEqual(item.product_id, "product_1")
        self.assertEqual(item.quantity, 5.0)
        self.assertEqual(item.description, "Test work")
    
    def test_invoice_model(self):
        """Test Invoice model"""
        items = [
            InvoiceItem(product_id="product_1", quantity=5.0, description="Test work")
        ]
        invoice = Invoice(
            customer_id="customer_1",
            items=items,
            invoice_date=datetime(2024, 3, 1)
        )
        self.assertEqual(invoice.customer_id, "customer_1")
        self.assertEqual(len(invoice.items), 1)
        self.assertEqual(invoice.invoice_date.year, 2024)


if __name__ == '__main__':
    unittest.main()
