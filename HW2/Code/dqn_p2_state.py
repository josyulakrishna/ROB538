import torch
import torch.nn as nn
import torch.nn.functional as F
import random

from tensorboardX import SummaryWriter
from tqdm import tqdm
from my_grid import *

# https://github.com/gxywy/pytorch-dqn/blob/master/dqn.py

class ExperienceReplayBuffer():
    def __init__(self, capacity):
        self.capacity = capacity
        self.buffer = []
        self.position = 0

    def push(self, state, action, reward, next_state, done):
        if len(self.buffer) < self.capacity:
            # self.buffer.pop(0)
            # self.buffer.append((state, action, reward, next_state, done))
            self.buffer.append(None)
        self.buffer[self.position] = (state, action, reward, next_state, done)
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size):
        return random.sample(self.buffer, batch_size)

    def __len__(self):
        return len(self.buffer)

class Net(nn.Module):
    def __init__(self, output):
        super(Net, self).__init__()
        self.fc1 = nn.Linear(4, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, output)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)

        return x

class DQN(nn.Module):
    def __init__(self, n_actions):
        super(DQN, self).__init__()
        self.n_actions = n_actions
        self.eval_net_1 = Net(n_actions)
        self.target_net_1 = Net(n_actions)
        self.eval_net_2 = Net(n_actions)
        self.target_net_2 = Net(n_actions)
        self.optimizer_1 = torch.optim.RMSprop(self.eval_net_1.parameters(), lr=1e-4, alpha=0.95, eps=0.01) ## 10.24 fix alpha and eps
        self.optimizer_2 = torch.optim.RMSprop(self.eval_net_2.parameters(), lr=1e-4, alpha=0.95, eps=0.01)
        self.loss_func = torch.nn.MSELoss()
        self.replay_memory_1 = ExperienceReplayBuffer(1000)
        self.replay_memory_2 = ExperienceReplayBuffer(1000)
        self.steps = 0
        self.eval_net_1.cuda()
        self.target_net_1.cuda()
        self.eval_net_2.cuda()
        self.target_net_2.cuda()


    def choose_action(self, state, eval_net, epsilon):
        if random.random() > epsilon:
            state = torch.unsqueeze(torch.FloatTensor(state), 0).cuda()
            actions_value = eval_net.forward(state)
            action = torch.max(actions_value, 1)[1].data.cpu().numpy()[0]
        else:
            action = random.randint(0, self.n_actions - 1)
        return action

    def store_transition_1(self, state, action, reward, next_state, done):
        self.replay_memory_1.push(state, action, reward, next_state, done)

    def store_transition_2(self, state, action, reward, next_state, done):
        self.replay_memory_2.push(state, action, reward, next_state, done)


    def learn(self, batch_size):
        self.steps += 1
        if self.steps % 100 == 0:
            self.target_net_1.load_state_dict(self.eval_net_1.state_dict())
            self.target_net_2.load_state_dict(self.eval_net_2.state_dict())

        self.optimizer_1.zero_grad()
        self.optimizer_2.zero_grad()

        batch_1 = self.replay_memory_1.sample(batch_size)
        batch_state_1, batch_action_1, batch_reward_1, batch_next_state_1, batch_done_1 = zip(*batch_1)
        batch_state_1 = torch.stack(batch_state_1).cuda()
        batch_action_1 = torch.LongTensor(batch_action_1).cuda()
        batch_reward_1 = torch.FloatTensor(batch_reward_1).cuda()
        batch_next_state_1 = torch.stack(batch_next_state_1).cuda()
        batch_done_1 = torch.FloatTensor(batch_done_1).cuda()
        q_eval_1 = self.eval_net_1(batch_state_1).gather(1, batch_action_1.unsqueeze(1)).squeeze(1)
        q_next_1 = self.target_net_1(batch_next_state_1).detach()
        q_target_1 = batch_reward_1 + 0.99 * q_next_1.max(1)[0] * (1 - batch_done_1)
        loss_1 = self.loss_func(q_eval_1, q_target_1)
        loss_1.backward()
        self.optimizer_1.step()


        ######
        batch_2 = self.replay_memory_2.sample(batch_size)
        batch_state_2, batch_action_2, batch_reward_2, batch_next_state_2, batch_done_2 = zip(*batch_2)
        batch_state_2 = torch.stack(batch_state_2).cuda()
        batch_action_2 = torch.LongTensor(batch_action_2).cuda()
        batch_reward_2 = torch.FloatTensor(batch_reward_2).cuda()
        batch_next_state_2 = torch.stack(batch_next_state_2).cuda()
        batch_done_2 = torch.FloatTensor(batch_done_2).cuda()
        q_eval_2 = self.eval_net_2(batch_state_2).gather(1, batch_action_2.unsqueeze(1)).squeeze(1)
        q_next_2 = self.target_net_2(batch_next_state_2).detach()
        q_target_2 = batch_reward_2 + 0.99 * q_next_2.max(1)[0] * (1 - batch_done_2)
        loss_2 = self.loss_func(q_eval_2, q_target_2)
        loss_2.backward()
        self.optimizer_2.step()


def train():
    dqn = DQN(4)
    writer = SummaryWriter('runs/rob538a2/p2_state')

    for i_episode in tqdm(range(10000)):
        # initialize grid start agent at random position
        grid, goals = custom_grid(2)
        total_reward_1 = 0
        total_reward_2 = 0
        # agent postion list of tuples
        # actions list of integers
        agent_pos_1 = (random.randint(0, 4), random.randint(0, 9))
        agent_pos_2 = (random.randint(0, 4), random.randint(0, 9))
        # neighbours = getNeighbours(agent_pos_1[0], agent_pos_1[1], grid.desc)
        # if len(neighbours) < 4:
        #     neighbours += [0] * (4 - len(neighbours))
        neighbours = []
        state_1 = list(agent_pos_1) + list(agent_pos_2) + neighbours

        state_1 = torch.FloatTensor(state_1)

        # neighbours = getNeighbours(agent_pos_2[0], agent_pos_2[1], grid.desc)
        # if len(neighbours) < 4:
        #     neighbours += [0] * (4 - len(neighbours))

        state_2 = list(agent_pos_1) + list(agent_pos_2) + neighbours

        state_2 = torch.FloatTensor(state_2)

        for t in range(100):
            action_1 = dqn.choose_action(state_1, dqn.eval_net_1, 0.1)
            action_2 = dqn.choose_action(state_2, dqn.eval_net_2, 0.1)

            agent_positions, rewards, done, goals, neighbours, img = step(grid, [action_1, action_2], [agent_pos_1, agent_pos_2],  goals)
            # next_state_1 = list(agent_positions[0]) + list(agent_positions[1]) + neighbours[:4]
            # next_state_2 = list(agent_positions[0]) + list(agent_positions[1]) + neighbours[4:]

            next_state_1 = list(agent_positions[0]) + list(agent_positions[1])
            next_state_2 = list(agent_positions[0]) + list(agent_positions[1])

            total_reward_1 += rewards[0]
            total_reward_2 += rewards[1]
            next_state_1 = torch.FloatTensor(next_state_1)
            next_state_2 = torch.FloatTensor(next_state_2)
            dqn.store_transition_1(state_1, action_1, rewards[0], next_state_1, done)
            dqn.store_transition_2(state_2, action_2, rewards[1], next_state_2, done)

            agent_pos_1 = agent_positions[0]
            agent_pos_2 = agent_positions[1]

            if dqn.replay_memory_1.__len__() > 50:
                dqn.learn(32)
            if done:
                break

            state_1 = next_state_1
            state_2 = next_state_2
        writer.add_scalar('reward_agent_1', total_reward_1, i_episode)
        writer.add_scalar('reward_agent_2', total_reward_2, i_episode)
    # save model
    torch.save(dqn.eval_net_1.state_dict(), 'dqn_2agents_p2_a1.pth')
    torch.save(dqn.eval_net_2.state_dict(), 'dqn_2agents_p2_a2.pth')
    writer.close()

if __name__ == '__main__':
    train()
