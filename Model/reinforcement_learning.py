# reinforcement_learning.py

import gym
from gym import spaces
import numpy as np
from collections import deque
import random
from sklearn.preprocessing import LabelEncoder
from typing import Dict, Tuple
from database import DatabaseInterface  # Import DatabaseInterface

class ExperienceReplayBuffer:
    def __init__(self, capacity, alpha=0.6, beta=0.4):
        self.buffer = deque(maxlen=capacity)
        self.alpha = alpha
        self.beta = beta

    def add(self, experience):
        self.buffer.append(experience)

    def sample(self, batch_size):
        priorities = [self.buffer[i][4] ** self.alpha for i in range(len(self.buffer))]
        total_priority = sum(priorities)
        probabilities = [p / total_priority for p in priorities]
        indices = random.choices(range(len(self.buffer)), weights=probabilities, k=batch_size)
        return [self.buffer[i] for i in indices]

    def update_priorities(self, indices, priorities):
        for i, p in zip(indices, priorities):
            self.buffer[i] = (*self.buffer[i][:4], p ** self.beta)

class DailyActivityEnv(gym.Env):
    def __init__(self, db_interface: 'DatabaseInterface', replay_buffer: 'ExperienceReplayBuffer', simulation_speed: float = 1.0):
        super(DailyActivityEnv, self).__init__()
        self.db_interface = db_interface
        self.replay_buffer = replay_buffer

        possible_states = ['IN_VEHICLE', 'ON_BICYCLE', 'RUNNING', 'STILL', 'WALKING', 'UNKNOWN']
        possible_locations = self.db_interface.get_Locations()

        self.state_label_encoder = LabelEncoder()
        self.state_label_encoder.fit(possible_states)

        self.location_label_encoder = LabelEncoder()
        self.location_label_encoder.fit(possible_locations)

        self.observation_space = spaces.Box(
            low=0, high=1,
            shape=(2,),
            dtype=np.float32
        )

        self.current_state = self.db_interface.get_initial_state()
        self.current_location = self.db_interface.get_initial_location()
        self.update_action_space()

    def update_action_space(self):
        activities = self.db_interface.get_activities_by_place(self.current_location)
        self.action_space = spaces.Discrete(len(activities))

    def reset(self, **kwargs) -> np.ndarray:
        self.current_activity = None
        self.current_time = 0
        self.current_state = self.db_interface.get_initial_state()
        self.current_location = self.db_interface.get_initial_location()
        self.update_action_space()
        self.current_observation = self.encode_state(self.current_state, self.current_location)
        self.current_observation = np.array([self.current_observation])
        return self.current_observation

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        user_feedback = self.db_interface.get_user_feedback(action)
        reward = self.calculate_reward(user_feedback, action)
        next_state = self.db_interface.update_state_with_feedback(user_feedback, self.current_state)
        done = self.db_interface.check_if_day_ends()
        self.replay_buffer.add((self.current_state, action, reward, next_state, done))
        self.current_state = next_state
        self.current_location = self.db_interface.get_location_from_database(next_state)
        self.update_action_space()
        self.current_observation = self.encode_state(self.current_state, self.current_location)
        
        # Save feedback to the database
        self.db_interface.save_feedback(self.current_state, action, user_feedback, reward, str(self.current_observation))
        
        return np.array([self.current_observation]), reward, done, {}

    def encode_state(self, state, location):
        state_encoded = self.state_label_encoder.transform([state])[0]
        location_encoded = self.location_label_encoder.transform([location])[0]
        return np.array([state_encoded, location_encoded])

    def calculate_reward(self, user_feedback, action):
        return 1 if user_feedback == "Yes" else -1