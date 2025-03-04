class TimeEntry:
    def __init__(self, id, description, start_time, end_time, user_id):
        self.id = id
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.user_id = user_id

class User:
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email