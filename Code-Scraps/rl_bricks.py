import random
import math


# ════════════════════════════════════════════════════════════════════
#  BRICK 1 — ENV
#  The world. Knows nothing about learning. Only reacts.
#  Contract: reset() → state,  step(action) → (next_state, reward, done)
# ════════════════════════════════════════════════════════════════════

class Env:

    @property
    def actions(self) -> list:
        """All actions available in this environment."""
        raise NotImplementedError

    @property
    def states(self) -> list:
        """All states in this environment."""
        raise NotImplementedError

    def reset(self):
        """Start a new episode. Return the initial state."""
        raise NotImplementedError

    def step(self, action):
        """
        Apply action to the current state.
        Return (next_state, reward, done).
        """
        raise NotImplementedError


# ════════════════════════════════════════════════════════════════════
#  BRICK 2 — POLICY
#  Accumulated knowledge. Survives strategy swaps.
#  The strategy writes into it. The agent reads from it.
#  Can be deterministic (argmax) or stochastic (sample).
# ════════════════════════════════════════════════════════════════════

class Policy:

    def select_action(self, state, actions) -> str:
        """
        Given a state, return an action.
        Deterministic  → always the same action for that state.
        Stochastic     → sample from a distribution over actions.
        """
        raise NotImplementedError

    def update(self, **kwargs):
        """
        Absorb what the strategy learned.
        kwargs is open so any algorithm can pass what it needs:
          Q-learning      → update(state, action, value)
          Policy gradient → update(state, action, probability)
          Actor-critic    → update(state, action, advantage, value)
        """
        raise NotImplementedError

    def snapshot(self) -> dict:
        """Return a serialisable copy of the current policy state."""
        raise NotImplementedError


class DeterministicPolicy(Policy):
    """
    Always picks the action with the highest Q-value.
    Written by Q-learning, Value Iteration, or any value-based method.
    """

    def __init__(self, states, actions):
        self.actions = actions
        self.Q = {s.name: {a: 0.0 for a in actions} for s in states}
        self.history = []

    def select_action(self, state, actions):
        return max(self.Q[state.name], key=self.Q[state.name].get)

    def update(self, **kwargs):
        s = kwargs["state"]
        a = kwargs["action"]
        v = kwargs["value"]
        self.Q[s.name][a] = v
        self.history.append((s.name, a, v))

    def snapshot(self):
        return {"type": "deterministic", "Q": {k: dict(v) for k, v in self.Q.items()}}


class StochasticPolicy(Policy):
    """
    Samples actions from a probability distribution per state.
    Written by Policy Gradient or any distribution-based method.
    Starts uniform — no preference.
    """

    def __init__(self, states, actions):
        self.actions = actions
        n = len(actions)
        self.probs = {s.name: {a: 1/n for a in actions} for s in states}
        self.history = []

    def select_action(self, state, actions):
        dist    = self.probs[state.name]
        choices = list(dist.keys())
        weights = list(dist.values())
        return random.choices(choices, weights=weights, k=1)[0]

    def update(self, **kwargs):
        s    = kwargs["state"]
        a    = kwargs["action"]
        prob = kwargs["probability"]
        self.probs[s.name][a] = prob
        total = sum(self.probs[s.name].values())
        self.probs[s.name] = {k: v / total for k, v in self.probs[s.name].items()}
        self.history.append((s.name, a, prob))

    def snapshot(self):
        return {"type": "stochastic", "probs": {k: dict(v) for k, v in self.probs.items()}}


# ════════════════════════════════════════════════════════════════════
#  BRICK 3 — LEARNING STRATEGY
#  The algorithm. Reads from and writes into the policy.
#  Does NOT own the policy — it is a tool, not an identity.
#  Swap it at any time without touching the policy.
# ════════════════════════════════════════════════════════════════════

class LearningStrategy:

    def select_action(self, state, actions, policy: Policy) -> str:
        """Decide which action to take, consulting the policy."""
        raise NotImplementedError

    def update(self, state, action, reward, next_state, done, policy: Policy):
        """Observe the outcome and write updated knowledge into the policy."""
        raise NotImplementedError


class QLearning(LearningStrategy):
    """
    Off-policy TD learning.
    Explores with epsilon-greedy, updates via the Bellman equation.
    Writes Q-values into a DeterministicPolicy.
    """

    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.3):
        self.alpha   = alpha    # learning rate
        self.gamma   = gamma    # discount factor
        self.epsilon = epsilon  # exploration rate

    def select_action(self, state, actions, policy: Policy):
        if random.random() < self.epsilon:
            return random.choice(actions)       # explore
        return policy.select_action(state, actions)  # exploit

    def update(self, state, action, reward, next_state, done, policy: Policy):
        q      = policy.Q[state.name][action]
        q_next = 0.0 if done else max(policy.Q[next_state.name].values())
        new_q  = q + self.alpha * (reward + self.gamma * q_next - q)
        policy.update(state=state, action=action, value=new_q)

    def decay_epsilon(self, rate=0.995, floor=0.05):
        self.epsilon = max(floor, self.epsilon * rate)


class RandomStrategy(LearningStrategy):
    """
    Baseline: uniform random. Never learns.
    Useful for comparing against a trained agent.
    """

    def select_action(self, state, actions, policy: Policy):
        return random.choice(actions)

    def update(self, state, action, reward, next_state, done, policy: Policy):
        pass  # nothing to learn


# ════════════════════════════════════════════════════════════════════
#  BRICK 4 — AGENT
#  The self. Owns the policy (permanent). Borrows the strategy (swappable).
#  Contains no learning logic — purely coordinates the other bricks.
# ════════════════════════════════════════════════════════════════════

class Agent:

    def __init__(self, strategy: LearningStrategy, policy: Policy):
        self.policy   = policy    # permanent — never replaced
        self.strategy = strategy  # swappable — plug any algorithm in
        self.memory   = []        # full experience trace

    def act(self, state, actions) -> str:
        """Ask the strategy what to do, passing the policy as context."""
        return self.strategy.select_action(state, actions, self.policy)

    def learn(self, state, action, reward, next_state, done):
        """Tell the strategy what happened; it writes into the policy."""
        self.strategy.update(state, action, reward, next_state, done, self.policy)
        self.memory.append((state.name, action, reward, next_state.name, done))

    def swap_strategy(self, new_strategy: LearningStrategy):
        """
        Replace the learning algorithm.
        The policy — and everything it has learned — is untouched.
        """
        self.strategy = new_strategy


# ════════════════════════════════════════════════════════════════════
#  BRICK 5 — TRAINING LOOP
#  The builder. Clicks all bricks together and runs episodes.
#  Owns episode bookkeeping. The agent and policy know nothing about episodes.
# ════════════════════════════════════════════════════════════════════

def run(env: Env, agent: Agent, n_episodes=500, max_steps=50, verbose=False) -> list:
    """
    Run the agent in the environment for n_episodes.

    Each episode:
      1. Reset the world → get initial state
      2. Loop until done or max_steps:
           a. Agent acts   → action
           b. World reacts → next_state, reward, done
           c. Agent learns → policy updated in place
      3. Decay epsilon if the strategy supports it
      4. Record total reward

    Returns the reward history (one value per episode) for visualisation.
    """
    history = []

    for ep in range(n_episodes):
        state        = env.reset()
        total_reward = 0.0
        done         = False

        for _ in range(max_steps):
            action                   = agent.act(state, env.actions)
            next_state, reward, done = env.step(action)
            agent.learn(state, action, reward, next_state, done)
            state        = next_state
            total_reward += reward
            if done:
                break

        if hasattr(agent.strategy, "decay_epsilon"):
            agent.strategy.decay_epsilon()

        history.append(total_reward)

        if verbose and (ep + 1) % 100 == 0:
            avg = sum(history[-100:]) / 100
            print(f"  ep {ep+1:>4} | avg reward (last 100): {avg:>8.1f}"
                  f" | epsilon: {getattr(agent.strategy, 'epsilon', '-'):.3f}")

    return history