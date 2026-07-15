# Lesson 5 — The Forward Pass

This lesson is surprisingly short because you've already learned almost everything.

The **forward pass** simply answers:

> **Given an input, how do I compute the prediction?**

Nothing is learned here.

No gradients.

No optimization.

Just computation.

---

## Think of a calculator

Imagine a calculator.

```text
Input

2 + 3

↓

Calculator

↓

5
```

The calculator isn't learning.

It is simply computing.

A neural network during the forward pass is exactly the same.

```text
Input

↓

Layer 1

↓

Activation

↓

Layer 2

↓

Activation

↓

Output
```

---

# Building our first real network

Instead of

```python
class MyModel(nn.Module):

    def __init__(self):
        super().__init__()

    def forward(self,x):
        return x
```

we now build

```python
class MyModel(nn.Module):

    def __init__(self):
        super().__init__()

        self.layer1 = nn.Linear(5,8)
        self.relu = nn.ReLU()
        self.layer2 = nn.Linear(8,2)

    def forward(self,x):

        x = self.layer1(x)

        x = self.relu(x)

        x = self.layer2(x)

        return x
```

Let's understand every line.

---

# The constructor

```python
self.layer1 = nn.Linear(5,8)
```

means

```text
5 features

↓

8 learned features
```

Then

```python
self.relu
```

means

```text
Apply ReLU
```

Then

```python
self.layer2 = nn.Linear(8,2)
```

means

```text
8 features

↓

2 outputs
```

Notice something.

The constructor **doesn't process data**.

It only builds the machine.

---

# The forward function

Now the interesting part.

```python
x = self.layer1(x)
```

Suppose

```python
x =

[
2,
0,
1,
0,
0
]
```

Shape

```text
(5,)
```

After

```python
self.layer1(x)
```

Shape becomes

```text
(8,)
```

Graphically

```text
5

↓

Linear

↓

8
```

---

Next

```python
x = self.relu(x)
```

The shape stays

```text
(8,)
```

because ReLU never changes dimensions.

It only changes values.

Example

Before

```text
[-3,
2,
7,
-1]
```

After

```text
[0,
2,
7,
0]
```

---

Finally

```python
x = self.layer2(x)
```

Shape

```text
(2,)
```

Graphically

```text
8

↓

Linear

↓

2
```

---

Finally

```python
return x
```

The prediction is returned.

---

# Visualizing the data

Suppose the input is

```python
[2,
0,
1,
0,
0]
```

The network performs

```text
Input

[2,0,1,0,0]

↓

Linear

↓

[0.32,
-0.84,
1.11,
...
]

↓

ReLU

↓

[0.32,
0,
1.11,
...
]

↓

Linear

↓

[-1.52,
3.81]
```

Those last two numbers are your model's prediction.

---

# Where does learning happen?

Notice something.

Nothing in

```python
def forward(...)
```

changes the weights.

Nothing.

The weights stay exactly the same.

```text
Forward

↓

Compute prediction

↓

Done
```

That's why it's called

> **forward pass**

The information only travels

```text
Input

↓

Output
```

---

# Running the network

Once the model exists

```python
model = MyModel()
```

Suppose

```python
state = torch.tensor(
    [2,0,1,0,0],
    dtype=torch.float32
)
```

Prediction

```python
y = model(state)
```

PyTorch internally performs

```text
state

↓

forward()

↓

prediction
```

Notice again

we never call

```python
model.forward(state)
```

PyTorch does that automatically.

---

# Batch input

Now remember yesterday's discussion.

Suppose

```python
states = torch.tensor([
    [2,0,1,0,0],
    [1,1,0,0,1],
    [3,2,1,1,0]
])
```

Shape

```text
(3,5)
```

Three samples.

Five features.

Feed them

```python
prediction = model(states)
```

Now

```text
Input

(3,5)

↓

Linear

↓

(3,8)

↓

ReLU

↓

(3,8)

↓

Linear

↓

(3,2)
```

Notice

every layer changes

only

the last dimension.

---

# Why is it called "forward"?

Because there is another pass.

```text
Forward

Input

↓

Prediction

----------------

Backward

Loss

↓

Gradients
```

The backward pass walks through the network **in reverse**.

We'll learn that soon.

---

# A very important mental model

At this point, you can think of every neural network as **a pipeline of tensor transformations**.

For example:

```text
(3,5)

↓

Linear(5,8)

↓

(3,8)

↓

ReLU

↓

(3,8)

↓

Linear(8,2)

↓

(3,2)
```

If you can keep track of the **shape** after every operation, you'll understand almost every architecture you encounter.

---

# Before we move to Loss...

I want to pause for one conceptual question because it's the turning point of machine learning.

Imagine our network predicts

```text
Prediction = [0.7]
```

but the correct answer is

```text
Target = [1.0]
```

The network has no idea whether **0.7** is "good" or "bad."

Someone has to tell it:

> "You were wrong by this much."

That "someone" is the **loss function**.

In my opinion, **loss functions** are not just another PyTorch component—they are the bridge between *making a prediction* and *learning from mistakes*. Once you understand the loss, the ideas of backpropagation and optimization become much more intuitive. That's exactly what we'll tackle next.

