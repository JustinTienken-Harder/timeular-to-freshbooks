import unittest
from src.timeular.client import TimeularClient

class TestTimeularClient(unittest.TestCase):

    def setUp(self):
        self.client = TimeularClient(api_key='test_api_key')

    def test_authenticate(self):
        response = self.client.authenticate()
        self.assertTrue(response['success'])

    def test_get_time_entries(self):
        entries = self.client.get_time_entries()
        self.assertIsInstance(entries, list)

    def test_create_time_entry(self):
        entry_data = {
            'start': '2023-01-01T00:00:00Z',
            'end': '2023-01-01T01:00:00Z',
            'tag_ids': ['test_tag_id']
        }
        response = self.client.create_time_entry(entry_data)
        self.assertTrue(response['success'])

if __name__ == '__main__':
    unittest.main()