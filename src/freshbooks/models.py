class Invoice:
    def __init__(self, invoice_id, client_id, amount, status, created_at):
        self.invoice_id = invoice_id
        self.client_id = client_id
        self.amount = amount
        self.status = status
        self.created_at = created_at

class Client:
    def __init__(self, client_id, name, email):
        self.client_id = client_id
        self.name = name
        self.email = email