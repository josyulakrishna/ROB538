import numpy as np
import itertools
import matplotlib
import pickle
from collections import defaultdict
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
sns.set_theme(style="whitegrid")
np.random.seed(42)
# import random, sys
# seed = random.randrange(sys.maxsize)
# rng = random.Random(seed)
# print("Seed was:", seed)

#El Farol bar problem
# z_prime is the state where action of agent i is different from the system state
# state of agent is 0, 1
# system state is a collection of agent attendance  to bar.
# x_k is the attendance on night k
# b is the optimal number of people in the bar
# global reward is the system reward per week


class ElFarol :
    def __init__(self, n_agents = 20, b = 5, k= 6):
        self.n_agents = n_agents
        self.b = b
        self.state = np.zeros(n_agents)
        # self.x = None #attendance on night
        self.iterations = 10000
        self.k = k
        self.gamma = 0.99
        self.total_weeks = 10000
        self.global_reward = []
        self.xk = np.zeros((self.total_weeks, self.k)) #collection of attendance over k nights
        self.z = np.zeros(( self.total_weeks, k, n_agents)) #state of agent i
        self.agent_estimate = np.zeros((n_agents, k))
        self.agent_buffer = [[] for i in range(n_agents)]
        self.global_buffer = []
        self.night_rewards = np.zeros((self.total_weeks, n_agents, self.k))
        self.V = defaultdict(lambda: defaultdict(list))

    def reset(self):
        self.state = np.zeros(self.n_agents)
        self.xk = np.zeros((self.total_weeks, self.k))
        self.z = np.zeros(( self.total_weeks, self.k, self.n_agents))
        self.agent_estimate = np.zeros((self.n_agents, self.k))
        self.agent_buffer = [[] for i in range(self.n_agents)]
        self.global_buffer = []
        self.night_rewards = np.zeros((self.total_weeks, self.n_agents, self.k))
        self.global_reward = []

    def chooseAction(self, agent_i, reward_choice=1):
        if reward_choice=="random":
            action = np.random.choice([0,1])
        if reward_choice=="greedy":
            action = np.argmax(self.agent_estimate[agent_i])
        if reward_choice=="epsilon":
            epsilon = 0.1
            if np.random.random() < epsilon:
                action = np.random.choice([0,1])
            else:
                action = np.argmax(self.agent_estimate[agent_i])
        return action

    def generate_fake_data(self):
        for week in range(self.total_weeks):
            for agent in range(self.n_agents):
                night = np.random.choice(self.k, 1)[0]
                self.z[week, night, agent] = 1
            for night in range(self.k):
                self.xk[week, night] = self.z[week, night, :].sum()

    def dynamics(self):
        for week in range(self.total_weeks):
            for night in range(self.k):
                attendance = []
                for agent_i in range(self.n_agents):
                    action = self.chooseAction(agent_i, reward_choice="random")
                    attendance.append(action)
                    self.z[week, night, agent_i ] = action
                self.xk[week, night ] = np.array(attendance).sum() #state of the bar on night k
            self.global_reward.append(self.week_reward(week))

    def moving_average(self):
        #get moving average reward of 3 previous nights
        rewards = []
        w = 3
        for i in range(len(self.buffer) - w + 1):
             rewards.append(sum(self.xk[i:i+w])/w)
        return rewards

    def insert_buffer(self, g, a, reward, agent_i):
        if g:
            if len(self.global_buffer) > 100:
                self.global_buffer.pop(0)
                self.global_buffer.append(reward)
            else:
                self.global_buffer.append(reward)

        if a:
            if len(self.agent_buffer[agent_i]) > 100:
                self.agent_buffer[agent_i].pop(0)
            else:
                self.agent_buffer[agent_i].append(reward)

    def week_reward(self, week):
        G = self.xk[week]@np.exp(-self.xk[week]/self.b)
        self.insert_buffer(g=True, a=False, reward=G, agent_i=None)
        return G

    def get_reward(self, x, reward_choice=1, night=0):
        if reward_choice == 0:
            #global reward
            gi = x@np.exp(-x/self.b)

        if reward_choice == 1:
            #night reward
            # gi = (self.b / x) #if x < self.b else -1* self.b /x
            gi = x * np.exp(-x/self.b) # if x < self.b else -1* x * np.exp(-x/self.b)

        if reward_choice == 2:
            #difference reward
            # c_i  = np.random.choice(self.n_agents, size = (self.k,))
            # c_i = x
            # c_i = np.array([self.b]*self.k) #best
            # c_i[night] = x[night]-1
            # c_i = x
            # c_i[night] = c_i[night]-1
            # gi = (x@np.exp(-x/self.b) - c_i@np.exp(-c_i/self.b))#  if x[night] < self.b else -1*(x@np.exp(-x/self.b) - c_i@np.exp(-c_i/self.b))
            # gi = x[night]*np.exp(-x[night]/self.b) - c_i[night]*np.exp(-c_i[night]/self.b) # if x[night] < self.b else -1*(
            gi = (x @ np.exp(-x / self.b) - (x-1) @ np.exp(-(x-1) / self.b))  #

        if reward_choice == 3:
            # local difference reward
            # c_i  = np.random.choice(self.n_agents, size = (1,))[0]
            # c_i = self.b #best
            # c_i = x[night]
            c_i = x-1
            gi = x*np.exp(-x/self.b) - c_i*np.exp(-c_i/self.b) # if x[night] < self.b else -1*(

        return gi

    def sensitivity(self, agent_i, k, week, choice=1):
        """Return the sensitivity/learnability of gi in G."""
        # agent_i is the index of the agent
        # k is the number of nights
        # choice is the 0,1 attend or not
        z = self.z[week, k, :]

        if choice == 1:
            # gi_z = self.local_reward(reward_choice, self.xk[week, k], week, agent_i)
            # gi_z = self.b /z[k] #if z[k] <= self.b else -self.b/z[k]
            gi_z = z[k] * np.exp(-z[k]/self.b) #if z[k] <= self.b else -z[k] * np.exp(-z[k]/self.b)

            z_i = z[k]

            z_prime = np.random.choice(self.n_agents, size = (self.k,))

            z_i_prime = z_prime[agent_i]

            # gi_z - gi(z-z_i+z_i_prime) z_tmp = z-z_i+z_i_prime
            # some gimmick to concatenate z and z_prime
            if agent_i== 0:
                z_tmp = np.concatenate(([z_i_prime], z[1:]))
            else:
                z_tmp = np.concatenate((z[:agent_i], [z_i_prime], z[agent_i+1:]))

            # term1 = z_tmp.sum() / self.b #if z_tmp.sum() <= self.b else -z_tmp.sum() / self.b
            term1 = z_tmp.sum() * np.exp(-z_tmp.sum()/self.b)
            numerator = gi_z - term1

            if agent_i== 0:
                z_tmp = np.concatenate(([z_i], z_prime[1:]))
            else:
                z_tmp = np.concatenate((z_prime[:agent_i], [z_i], z_prime[agent_i+1:]))

            # term2 = z_tmp.sum() / self.b #if z_tmp.sum() <= self.b else -z_tmp.sum() / self.b
            term2 = z_tmp.sum() * np.exp(-z_tmp.sum()/self.b)

            denominator = gi_z - term2

            if np.isnan(numerator/denominator):
                return 0
            else:
                return (numerator/denominator)
        if choice == 2:
            # c_i = np.random.choice(self.n_agents, size=(self.k,))
            # G_z_prime  = c_i@np.exp(-c_i/self.b)
            # gi_z = self.global_reward[week] - G_z_prime
            # # gi_z - gi(z-z_i+z_i_prime) z_tmp = z-z_i+z_i_prime
            # # some gimmick to concatenate z and z_prime
            # z_tmp = z
            # c_i_tmp = c_i
            # z_tmp[week] = c_i[week]
            # c_i_tmp[week] = z[week]
            # gi_z_prime = z_tmp@np.exp(-z_tmp/self.b) - c_i_tmp@np.exp(-c_i_tmp/self.b)
            # numerator_term1 = gi_z - gi_z_prime
            # z_tmp[week] = c_i[week]
            # numerator_term2 =
            # # term2 = c_i[]
            # # denominator = gi_z -
            return 0
        if choice == 3:
            return 0


    def factordness(self, agent_i, k, week, choice):
        # z_prime is a state which only differs from z in the state of component i
        G_z = self.global_reward[week]
        G_z_prime = 0
        z = self.z[week, k, :]

        if choice == 0:
            return 1

        if choice == 1:
            z_i_prime = np.random.choice(self.n_agents, size=(1,))[0]
            z[k] = z_i_prime
            G_z_prime = z @ np.exp(-z / self.b)
            # gi_z = self.b/z[k] #if z[k] < self.b else -1 * self.b /z[k]
            gi_z = z[k] * np.exp(-z[k] / self.b)  # if z[k] < self.b else -1 * z[k] * np.exp(-z[k]/self.b)
            gi_z_prime = z_i_prime * np.exp(-z_i_prime / self.b)  # if z_i_prime < self.b else -1 * z_i_prime * np.exp(-z_i_prime/self.b)
            # gi_z_prime = self.b/z_i_prime #if z_i_prime < self.b else -1 * self.b /z_i_prime
            if (gi_z-gi_z_prime)*(G_z-G_z_prime) > 0:
                return 1
            else:
                return -1

        if choice == 2:
            z_i_prime = np.random.choice(self.n_agents, size=(self.k,))
            z_i_prime[k] = z[k]
            G_z_prime_2 = z_i_prime @ np.exp(-z_i_prime / self.b)
            gi_z = (G_z-G_z_prime)  #if z[k] < self.b else -1 * 2*(G_z-G_z_prime)
            gi_z_prime = (G_z_prime - G_z_prime_2)
            if (gi_z-gi_z_prime)*(G_z-G_z_prime) > 0:
                return 1
            else:
                return -1
        if choice == 3:
            return 1
        # gi_z_prime = z[k]*np.exp(-z[k]/self.b)

        # return (gi_z-gi_z_prime)*(G_z-G_z_prime)


    ######### Learning Algorithms #########
    def q_learning(self, choice):
        gamma = 0.99
        alpha = 0.9
        # delta = np.ones((self.n_agents, self.k))
        global_reward = []
        epsilon = 0.5
        agent_choice = np.zeros((self.total_weeks, self.k, self.n_agents))
        agent_reward = np.zeros((self.total_weeks, self.k, self.n_agents))
        temperature = 0
        for week in range(self.total_weeks):
            temperature = temperature + 1
            # print(temperature, week)
            agent_attendances = np.zeros(self.k)
            for agent_i in range(self.n_agents):
                if temperature < (self.total_weeks - self.total_weeks/3):
                    night =  np.random.choice(self.k, 1)[0] if np.random.rand() < epsilon else np.argmax(self.agent_estimate[agent_i,:])
                else:
                    night = np.argmax(self.agent_estimate[agent_i,:])
                self.z[week, night, agent_i] = 1
                agent_attendances[night] += 1
                agent_choice[week, night, agent_i] += 1

            self.xk[week] = agent_attendances
            self.global_reward.append(agent_attendances @ np.exp(-agent_attendances / self.b))

            for agent_i in range(self.n_agents):
                for night in range(self.k):
                    if agent_choice[week, night, agent_i] == 1:
                        # reward choice 1 is night reward
                        # reward choice = 2 is the difference reward which requires night of attendance
                        if choice==0:
                            x = agent_attendances
                        if choice == 1:
                            x = agent_attendances[night]
                        if choice == 2:
                            x = agent_attendances
                        if choice == 3:
                            x = agent_attendances[night]
                        reward = self.get_reward(x, reward_choice=choice, night=night)
                        self.agent_estimate[agent_i, night] += alpha*(reward + gamma*np.max(self.agent_estimate[agent_i, :]) - self.agent_estimate[agent_i, night])
                        # self.agent_estimate[agent_i, night] += alpha *reward
                        # self.agent_estimate[agent_i, night] += 0.4*(reward - self.agent_estimate[agent_i, night])
                        # self.agent_estimate[agent_i, night] = 0.5*self.agent_estimate[agent_i, night] + 0.9*(reward + gamma*max(self.agent_estimate[agent_i, :]) - self.agent_estimate[agent_i, night])
                        agent_reward[week, night, agent_i] = reward


        return agent_choice, agent_reward

def error_bars(x, w):
    #error bar for moving average
    return np.sqrt(np.convolve(np.array(x)**2, np.ones(w), 'valid') / w - moving_average(np.array(x), w)**2)
    # return np.std(x, axis=0)/np.sqrt(x.shape[0])

def moving_average(x, w):
    return np.convolve(x, np.ones(w), 'valid') / w

def running_mean(x, N):
    cumsum = np.cumsum(np.insert(x, 0, 0))
    return (cumsum[N:] - cumsum[:-N]) / float(N)

def factordness_and_sensitivity(elfarol, agent_i=1, choice=1):
    agent_sensitivities = []
    agent_factordness = []

    for week in range(elfarol.total_weeks):
            for k in range(elfarol.k):
                agent_factordness.append(elfarol.factordness(agent_i, k, week, choice))
                agent_sensitivities.append(elfarol.sensitivity(agent_i, k, week, choice))
    return agent_factordness, agent_sensitivities

def get_attendance_nights(elfarol, agent_choice):
    agent_attendance_nights = []
    for agent_i in range(agent_choice.shape[2]):
        agent_attendance_nights.append(agent_choice[:,:,agent_i].sum(axis=0))
    return agent_attendance_nights

# if __name__ == "__main__":
#     run_problem_3()
# 574450259 FRA