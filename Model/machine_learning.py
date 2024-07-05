# machine_learning.py
import logging

import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

def train_ml_model():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        SELECT a.place_name, f.feedback, f.reward, ac.action
        FROM feedback f
        JOIN activities a ON f.activity_id = a.id
        JOIN actions ac ON ac.activity_id = f.activity_id
    ''')

    data = c.fetchall()
    number_of_rows = len(data)
    logging.info(f"Fetched {number_of_rows} rows from the database.")  # Log retrieved data count

    conn.close()

    if not data:
        raise ValueError("No data found in the database. Please ensure the database is populated with the required data.")

    df = pd.DataFrame(data, columns=['place_name', 'feedback', 'reward', 'action'])
    df['place_name'] = df['place_name'].astype('category').cat.codes

    X = df[['place_name', 'action']]
    y = df['feedback']

    if X.empty or y.empty:
        raise ValueError("The dataset is empty. Please check the data extraction process.")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred)

    print(f"Model Accuracy: {accuracy}")
    print("Classification Report:")
    print(report)

    return clf

# Train the model
ml_model = train_ml_model()