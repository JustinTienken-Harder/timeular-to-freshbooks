import pytest
from src.freshbooks.client import FreshbooksClient

@pytest.fixture
def freshbooks_client():
    return FreshbooksClient(api_key='test_api_key')

def test_authenticate(freshbooks_client):
    assert freshbooks_client.authenticate() is True

def test_create_invoice(freshbooks_client):
    invoice_data = {
        'client_id': '123',
        'amount': 100.0,
        'description': 'Test Invoice'
    }
    response = freshbooks_client.create_invoice(invoice_data)
    assert response['status'] == 'success'
    assert response['invoice']['amount'] == 100.0

def test_get_invoices(freshbooks_client):
    invoices = freshbooks_client.get_invoices()
    assert isinstance(invoices, list)  # Assuming it returns a list of invoices
    assert len(invoices) >= 0  # There should be at least 0 invoices returned