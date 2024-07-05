from flask import Flask, request, jsonify
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
import pandas as pd
from database import SQLiteDatabaseInterface
from reinforcement_learning import DailyActivityEnv, ExperienceReplayBuffer
from machine_learning import train_ml_model

app = Flask(__name__)

db_interface = SQLiteDatabaseInterface()
replay_buffer = ExperienceReplayBuffer(capacity=1000)
env = DummyVecEnv([lambda: DailyActivityEnv(db_interface, replay_buffer)])
model = PPO("MlpPolicy", env, verbose=1)

ml_model = train_ml_model()

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    place_name = data.get('place_name')
    state = data.get('state')

    if not place_name or not state:
        return jsonify({'error': 'Place name and state are required'}), 400

    env.reset()
    env.envs[0].current_location = place_name
    env.envs[0].current_state = state

    current_observation = env.envs[0].encode_state(state, place_name)
    observation = np.array([current_observation])

    action = model.predict(observation)
    action = int(action[0])  # Accessing the first element of the tuple

    # Debugging: Print action
    print(f"Action predicted: {action}")

    # Get activities by place
    activities = db_interface.get_activities_by_place(place_name)
    if not activities:
        return jsonify({'error': 'No activities found for the given place'}), 404

    # Select activity based on action
    selected_activity = activities[action % len(activities)]

    # Debugging: Print selected activity
    print(f"Selected activity: {selected_activity}")

    # Save the action to the database
    db_interface.save_action(action, selected_activity[0])

    # Use machine learning model to improve prediction
    place_code = pd.Series([place_name]).astype('category').cat.codes[0]
    input_data = pd.DataFrame([[place_code, action]], columns=['place_name', 'action'])  # Fixing the UserWarning
    ml_prediction = ml_model.predict(input_data)

    return jsonify({'activity_Id': selected_activity[0], 'predicted_activity': selected_activity[1], 'ml_prediction': int(ml_prediction[0])})

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json
    activity_id = data.get('activity_id')
    feedback_value = data.get('feedback')
    state = data.get('state')

    if activity_id is None or feedback_value is None or state is None:
        return jsonify({'error': 'Invalid activity_id, feedback value, or state'}), 400

    # Save the feedback and state into the database
    db_interface.save_feedback(state, activity_id, feedback_value)

    return jsonify({'status': 'success', 'activity_id': activity_id, 'feedback': feedback_value, 'state': state})

@app.route('/suggest_plan', methods=['POST'])
def suggest_plan():
    data = request.json
    place_name = data.get('place_name')
    state = data.get('state')

    if not place_name or not state:
        return jsonify({'error': 'Place name and state are required'}), 400

    env.reset()
    env.envs[0].current_location = place_name
    env.envs[0].current_state = state

    current_observation = env.envs[0].encode_state(state, place_name)
    observation = np.array([current_observation])

    actions = []
    for _ in range(10):  # Suggest 10 activities for the next day
        action = model.predict(observation)
        action = int(action[0])  # Accessing the first element of the tuple
        actions.append(action)

    activities = [db_interface.get_activity_from_database(action) for action in actions]

    return jsonify({'suggested_activities': activities})

if __name__ == '__main__':
    app.run(debug=True)