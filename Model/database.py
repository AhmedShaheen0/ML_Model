import sqlite3
import requests
import logging
import random
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
disable_warnings(InsecureRequestWarning)

# API endpoints
API_BASE_URL = "http://ahmedshaheen0000-001-site1.dtempurl.com/Activity"
FEEDBACK_API_URL = "http://ahmedshaheen0000-001-site1.dtempurl.com/ML"
ACTIONS_API_URL = "http://ahmedshaheen0000-001-site1.dtempurl.com/ML/actions"

# Authorization header
headers = {
    "Authorization": "Basic MTExNzY0ODA6NjAtZGF5ZnJlZXRyaWFs"
}



# Create a SQLite database
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Create tables
c.execute('''
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_name TEXT,
    duration REAL,
    place_name TEXT,
    latitude REAL,
    longitude REAL,
    date TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT,
    feedback INTEGER,
    activity_id INTEGER,
    reward REAL,
    observation TEXT,
    FOREIGN KEY (activity_id) REFERENCES activities(id)
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action INTEGER,
    activity_id INTEGER,
    FOREIGN KEY (activity_id) REFERENCES activities(id)
)
''')

# Fetch data from API with SSL verification disabled
response = requests.get(f"{API_BASE_URL}",headers=headers, verify=False)
activities = response.json()

# Insert data into activities table, ignoring duplicates
for activity in activities:
    c.execute('''
    INSERT OR IGNORE INTO activities (id, activity_name, duration, place_name, latitude, longitude, date)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        activity['id'],
        activity['name'],
        activity['duration'],
        activity['place']['placeName'],
        activity['place']['latitude'],
        activity['place']['longitude'],
        activity['date']
    ))
# Insert initial data into feedback table
initial_data = [
    ("IN_VEHICLE", "0", 1, 10, "I enjoyed driving."),
    ("ON_BICYCLE", "1", 2, -5, "I got tired from cycling."),
    ("RUNNING", "0", 3, 15, "It was a great run!"),
    ("STILL", "1", 4, 0, "I was just relaxing."),
    ("WALKING", "0", 5, 8, "I enjoyed walking around the park."),
]

for state, feedback, activity_id, reward, observation in initial_data:
    c.execute('''
    INSERT INTO feedback (state, feedback, activity_id, reward, observation)
    VALUES (?, ?, ?, ?, ?)
    ''', (state, feedback, activity_id, reward, observation))

c.execute('''
    INSERT INTO actions (action, activity_id)
    VALUES (?, ?)
    ''', (0 , 5))
conn.commit()
conn.close()

class DatabaseInterface:
    def get_initial_state(self):
        pass

    def get_user_feedback(self, predicted_activity):
        pass

    def update_state_with_feedback(self, user_feedback, current_state):
        pass

    def check_if_day_ends(self):
        pass

    def get_initial_location(self):
        pass

    def get_Locations(self):
        pass

    def get_location_from_database(self, state: str) -> str:
        pass

    def get_activity_from_database(self, activity_id: int) -> str:
        pass

    def get_all_activities(self):
        pass

    def get_activities_by_place(self, place_name: str):
        pass

class SQLiteDatabaseInterface(DatabaseInterface):
    def __init__(self, db_path='database.db'):
        self.db_path = db_path

    def get_initial_state(self):
        return "STILL"

    def get_user_feedback(self, activity):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
        SELECT feedback.feedback
        FROM feedback
        JOIN activities ON feedback.activity_id = activities.id
        WHERE activities.activity_name = ?
        ''', (activity,)) 
        result = c.fetchone()
        conn.close()
        return result[0] 
    
    def update_state_with_feedback(self, user_feedback, current_state):
        next_states = {
            "IN_VEHICLE": "ON_BICYCLE",
            "ON_BICYCLE": "RUNNING",
            "RUNNING": "STILL",
            "STILL": "WALKING",
            "WALKING": "UNKNOWN",
            "UNKNOWN": "IN_VEHICLE"
        }
        return next_states.get(current_state, "STILL")

    def check_if_day_ends(self):
        return random.choice([True, False])

    def get_initial_location(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT place_name FROM activities LIMIT 1")
        result = c.fetchone()
        conn.close()
        return result[0] 
    
    def get_Locations(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT DISTINCT place_name FROM activities")
        locations = [row[0] for row in c.fetchall()]
        conn.close()
        return locations

    def get_location_from_database(self, state: str) -> str:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
        SELECT activities.place_name
        FROM activities
        JOIN feedback ON activities.id = feedback.activity_id
        WHERE feedback.state = ?''', (state,)) 
        result = c.fetchone()
        conn.close()
        return result[0] if result else "Akhenaten Museum"

    def get_activity_from_database(self, action: int) -> str:
        logging.info(f"Fetching activity for action ID: {action}")
        
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            logging.info("Database connection and cursor created successfully.")
            
            # Execute the query
            c.execute("SELECT activity_name  FROM activities WHERE id=?", (action,))
            
            # Fetch the result
            activity = c.fetchone()
            logging.info(f"Query executed. Result: {activity}")
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return "Database Error"
        finally:
            conn.close()
            logging.info("Database connection closed.")
        
        logging.info(f"Found activity: {activity} for action ID: {action}")
        return activity

    def get_all_activities(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT activity_name FROM activities")
        activities = [row[0] for row in c.fetchall()]
        conn.close()
        return activities

    def get_activities_by_place(self, place_name: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, activity_name FROM activities WHERE place_name=?", (place_name,))
        activities = c.fetchall()
        conn.close()
        return activities

    def save_feedback(self, state, activity_id, feedback, reward=None, observation=None):
         # Save feedback to the SQLite database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
        INSERT INTO feedback (state, feedback, activity_id, reward, observation)
        VALUES (?, ?, ?, ?, ?)
        ''', (state, feedback, activity_id, reward, observation))
        conn.commit()
        conn.close()
        
        # Save feedback to the .NET API
        feedback_data = {
            "State": state,
            "Feedback": feedback,
            "ActivityID": activity_id,
            "Reward": reward,
            "Observation": observation
        }
        response = requests.post(f"{FEEDBACK_API_URL}/Create",headers=headers, json=feedback_data, verify=False)
        if response.status_code != 200:
            logging.error(f"Failed to save feedback: {response.text}")

 

    def save_action(self, action, activity_id):
    # Debugging: Print action and activity_id
        print(f"Saving action: {action}, activity_id: {activity_id}")

        # Save action to the SQLite database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO actions (action, activity_id) VALUES (?, ?)''', (action, activity_id))
        conn.commit()
        conn.close()

        # Post action to the .NET API
        action_data = {
            "ActionValue": action,
            "ActivityID": activity_id
        }
        response = requests.post(ACTIONS_API_URL,headers=headers, json=action_data, verify=False)
        if response.status_code != 201:
            logging.error(f"Failed to post action: {response.text}")