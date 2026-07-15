import random

# ════════════════════════════════════════════════════════════════════
#  WORLD — unchanged
# ════════════════════════════════════════════════════════════════════

class Box_in_Chessboard:
    def __init__(self, name, xy: tuple[int,int], color: str,
                 symbol: str = None, dirlist=list):
        self.name       = name
        self.coordinate = xy
        self.color      = color
        self.reward     = 0
        self.symbol     = symbol
        self.neighbours = {
            "up":    dirlist[0],
            "down":  dirlist[1],
            "right": dirlist[2],
            "left":  dirlist[3],
            "stand": self
        }

    def reward_(self):
        if   self.symbol == "X": self.reward = -100
        elif self.symbol == "O": self.reward =  100
        else:                    self.reward =  -10

    def next_state(self, action):
        if self.neighbours[action] is None:
            return self
        return self.neighbours[action]


s1 = Box_in_Chessboard("s1", (0,0), "white", "X",  [None,None,None,None])
s2 = Box_in_Chessboard("s2", (2,0), "white", "O",  [None,None,None,None])
s3 = Box_in_Chessboard("s3", (4,0), "white", "X",  [None,None,None,None])
s4 = Box_in_Chessboard("s4", (0,1), "white",  None, [None,None,None,None])
s5 = Box_in_Chessboard("s5", (1,1), "grey",   None, [None,None,None,None])
s6 = Box_in_Chessboard("s6", (2,1), "white",  None, [None,None,None,None])
s7 = Box_in_Chessboard("s7", (3,1), "grey",   None, [None,None,None,None])
s8 = Box_in_Chessboard("s8", (4,1), "white",  None, [None,None,None,None])

s1.neighbours = {"up": s4,   "down": None, "right": None, "left": None, "stand": s1}
s2.neighbours = {"up": s6,   "down": None, "right": None, "left": None, "stand": s2}
s3.neighbours = {"up": s8,   "down": None, "right": None, "left": None, "stand": s3}
s4.neighbours = {"up": None, "down": s1,   "right": s5,   "left": None, "stand": s4}
s5.neighbours = {"up": None, "down": None, "right": s6,   "left": s4,   "stand": s5}
s6.neighbours = {"up": None, "down": s2,   "right": s7,   "left": s5,   "stand": s6}
s7.neighbours = {"up": None, "down": None, "right": s8,   "left": s6,   "stand": s7}
s8.neighbours = {"up": None, "down": s3,   "right": None, "left": s7,   "stand": s8}

States  = [s1, s2, s3, s4, s5, s6, s7, s8]
Actions = ["up", "down", "right", "left"]


# ════════════════════════════════════════════════════════════════════
#  BRICK 1 — ENV
# ════════════════════════════════════════════════════════════════════

class Env:
    @property
    def actions(self) -> list:          raise NotImplementedError
    @property
    def states(self)  -> list:          raise NotImplementedError
    def reset(self):                    raise NotImplementedError
    def step(self, action: str):        raise NotImplementedError


class ChessboardEnv(Env):

    def __init__(self, states, actions, start):
        self._states  = states
        self._actions = actions
        self._start   = start
        self._current = start

    @property
    def actions(self): return self._actions
    @property
    def states(self):  return self._states
    @property
    def current(self): return self._current

    def reset(self):
        self._current = self._start
        return self._current

    def step(self, action):
        next_s        = self._current.next_state(action)  # your logic
        next_s.reward_()                                   # your logic
        reward        = float(next_s.reward)
        done          = next_s.symbol in ("X", "O")
        self._current = next_s
        return next_s, reward, done


# ════════════════════════════════════════════════════════════════════
#  BRICK 2 — POLICY
# ════════════════════════════════════════════════════════════════════

class Policy:
    def select_action(self, state, actions) -> str:  raise NotImplementedError
    def update(self, **kwargs):                       raise NotImplementedError
    def snapshot(self) -> dict:                       raise NotImplementedError


class StochasticPolicy(Policy):
    """
    Your original design — kept intact.
    Holds a probability distribution per state.
    select_action() samples from it.
    update() will let the strategy shift the probabilities over time.
    """

    def __init__(self, states, actions):
        self.states  = states
        self.actions = actions
        self.pi      = {}

    def pi_0(self):
        """
        Initialise with a dominant random direction per state.
        80% on the chosen action, 10% each on two alternatives.
        Your original logic — untouched.
        """
        for s in self.states:
            a = random.choice(self.actions)
            n = self.actions.index(a)
            if n % 2 != 0:
                n -= 1
            self.pi[s.name] = {
                self.actions[n]:           0.8,
                self.actions[(n + 2) % 4]: 0.1,
                self.actions[(n + 3) % 4]: 0.1,
            }

    def select_action(self, state, actions=None):
        dist   = self.pi[state.name]
        keys   = list(dist.keys())
        values = list(dist.values())
        return random.choices(keys, weights=values, k=1)[0]

    def update(self, **kwargs):
        """
        Shift probability mass toward the action that worked.
        The strategy calls this after each step.
        kwargs expected: state, action, delta (how much to shift)
        """
        state  = kwargs["state"]
        action = kwargs["action"]
        delta  = kwargs.get("delta", 0.05)   # how much mass to shift

        dist = self.pi.get(state.name)
        if dist is None or action not in dist:
            return                            # state not in policy yet — skip

        # nudge the chosen action up, spread the loss across others
        others = [a for a in dist if a != action]
        if not others:
            return

        shift_each = delta / len(others)

        dist[action] = min(1.0, dist[action] + delta)
        for a in others:
            dist[a] = max(0.0, dist[a] - shift_each)

        # renormalise so it stays a valid distribution
        total = sum(dist.values())
        self.pi[state.name] = {a: v / total for a, v in dist.items()}

    def snapshot(self) -> dict:
        return {"type": "stochastic", "pi": {k: dict(v) for k, v in self.pi.items()}}


# ════════════════════════════════════════════════════════════════════
#  BRICK 3 — LEARNING STRATEGY  (placeholder — next brick)
# ════════════════════════════════════════════════════════════════════

class LearningStrategy:
    def select_action(self, state, actions, policy: Policy) -> str:
        raise NotImplementedError
    def update(self, state, action, reward, next_state, done, policy: Policy):
        raise NotImplementedError


# ════════════════════════════════════════════════════════════════════
#  BRICK 4 — AGENT
#
#  Owns   : policy  (permanent — never replaced)
#  Borrows: strategy (swappable — plug any algorithm in)
#
#  act()   → asks strategy what to do, passes policy as context
#  learn() → tells strategy what happened, strategy writes into policy
#  swap_strategy() → replaces algorithm, policy untouched
# ════════════════════════════════════════════════════════════════════

class Agent:

    def __init__(self, policy: Policy, strategy: LearningStrategy = None):
        self.policy   = policy      # permanent
        self.strategy = strategy    # swappable — can be None until plugged in
        self.memory   = []          # full experience trace

    def act(self, state) -> str:
        """
        Ask the strategy what to do.
        Strategy consults the policy and returns an action string.
        The agent does NOT touch the env — it only returns the action.
        """
        if self.strategy is None:
            # no strategy yet → fall back to policy directly
            return self.policy.select_action(state)
        return self.strategy.select_action(state, list(self.policy.pi.keys()), self.policy)

    def learn(self, state, action, reward, next_state, done):
        """
        Pass the experience to the strategy.
        Strategy computes the update and writes into the policy.
        Agent also appends to its own memory trace.
        """
        if self.strategy is not None:
            self.strategy.update(state, action, reward, next_state, done, self.policy)
        self.memory.append((state.name, action, reward, next_state.name, done))

    def swap_strategy(self, new_strategy: LearningStrategy):
        """
        Replace the learning algorithm.
        self.policy is never touched — all learning survives.
        """
        self.strategy = new_strategy


# ════════════════════════════════════════════════════════════════════
#  PLUGGING ENV AND AGENT TOGETHER — manual loop (no run() yet)
#
#  This is the raw wiring before the training loop brick exists.
#  Shows exactly which object calls which method and in what order.
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # 1. build the world
    env = ChessboardEnv(States, Actions, start=s5)

    # 2. build the policy and initialise it
    policy = StochasticPolicy(States, Actions)
    policy.pi_0()

    # 3. build the agent — plug policy in, no strategy yet
    agent = Agent(policy=policy)

    # 4. manual episode — env and agent talking to each other
    print("=== one episode — env + agent, no strategy yet ===\n")

    state = env.reset()
    print(f"  start: {state.name}\n")

    for step in range(10):

        # agent decides (uses policy directly — no strategy plugged in yet)
        action = agent.act(state)

        # env reacts
        next_state, reward, done = env.step(action)

        # agent observes and stores (no strategy → memory only)
        agent.learn(state, action, reward, next_state, done)

        print(f"  step {step+1}: {state.name} --[{action}]--> "
              f"{next_state.name:<3}  reward: {reward:>6.1f}  done: {done}")

        state = next_state

        if done:
            print(f"\n  episode ended at {next_state.name} "
                  f"(symbol: '{next_state.symbol}')")
            break

    print(f"\n  memory trace ({len(agent.memory)} steps):")
    for entry in agent.memory:
        print(f"    {entry}")

    print(f"\n  policy snapshot (first 3 states):")
    snap = policy.snapshot()
    for name, dist in list(snap["pi"].items())[:3]:
        print(f"    {name}: {dist}")
