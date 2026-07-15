Excellent. Now we reach what I think is the **first truly "deep learning" concept**.

Until now we've built a network like

```text
Input
   │
Linear
   │
Linear
   │
Linear
   │
Output
```

Surprisingly...

> **This is not a deep neural network.**

It looks deep, but mathematically it isn't.

---

# Lesson 4 — Activation Functions

## Why do we need them?

Let's build a very small network.

```python
layer1 = nn.Linear(2, 3)
layer2 = nn.Linear(3, 1)
```

Suppose

```
Input
↓

Linear

↓

Linear

↓

Output
```

Let's write the math.

First layer

[
h=W_1x+b_1
]

Second layer

[
y=W_2h+b_2
]

Replace (h):

[
y=W_2(W_1x+b_1)+b_2
]

Expand:

[
y=(W_2W_1)x+(W_2b_1+b_2)
]

Notice something.

This is still

[
y=Wx+b
]

A single linear equation.

So

```text
Linear

↓

Linear
```

is exactly equivalent to

```text
Linear
```

No extra learning power.

---

# The solution

Insert a nonlinear function.

```text
Linear

↓

Activation

↓

Linear
```

Now

[
y=W_2f(W_1x+b_1)+b_2
]

Because (f(\cdot)) is nonlinear,

the network can no longer collapse into one giant linear equation.

Now it can learn curves, boundaries, patterns, strategies...

---

# Think geometrically

Imagine data that looks like this.

```
○ ○ ○ ○

      × × × ×
```

A straight line cannot separate them.

A linear model fails.

---

After adding nonlinearities

the network can create curved boundaries.

```
○ ○ ○
  ○

========

      × × ×
        ×
```

This is why deep learning works.

---

# What is an activation function?

An activation function is simply

> A function applied to every output of a layer.

Instead of

```text
Input

↓

Linear

↓

Output
```

we do

```text
Input

↓

Linear

↓

Activation

↓

Output
```

---

# The most common ones

There are only a handful you'll use regularly.

```
ReLU

Tanh

Sigmoid

Softmax
```

Let's understand each one.

---

# 1. ReLU

Probably the most common activation today.

Definition

[
ReLU(x)=\max(0,x)
]

Examples

```
-5 → 0

-2 → 0

0 → 0

3 → 3

8 → 8
```

Graph

```
        /
       /
      /
-----/
```

Negative numbers become zero.

Positive numbers stay unchanged.

---

PyTorch

```python
relu = nn.ReLU()
```

Usage

```python
x = relu(x)
```

or

```python
x = torch.relu(x)
```

Both work.

---

Why ReLU?

Because it is

* simple
* fast
* works very well

Most hidden layers today use ReLU.

---

# 2. Tanh

Definition

[
\tanh(x)
]

Output is always between

```
-1

and

1
```

Graph

```
      -----
    /
---
    \
      -----
```

Examples

```
-100 → -1

-2 → -0.96

0 → 0

2 → 0.96

100 → 1
```

Notice

large values become compressed.

---

PyTorch

```python
tanh = nn.Tanh()
```

Usage

```python
x = tanh(x)
```

---

Where is it used?

Actor-Critic PPO often uses

```python
nn.Tanh()
```

because bounded activations can lead to smoother optimization.

You'll probably remember seeing this:

```python
self.shared = nn.Sequential(
    nn.Linear(...),
    nn.Tanh(),
    nn.Linear(...),
    nn.Tanh()
)
```

Now you know what those mysterious `Tanh()` calls are doing.

---

# 3. Sigmoid

Definition

[
\sigma(x)=\frac{1}{1+e^{-x}}
]

Outputs

```
0

↓

1
```

Examples

```
-10 → 0

0 → 0.5

10 → 1
```

Graph

```
      -----

    /

---

```

---

Why use it?

Mostly for

> probabilities.

Example

```
0.93
```

means

```
93% probability
```

Nowadays it's rarely used in hidden layers.

---

# 4. Softmax

Softmax is special.

Suppose the network predicts

```
[2

5

1]
```

These aren't probabilities.

Softmax converts them into

```
[0.04

0.93

0.03]
```

Notice

```
They add up to 1.
```

Perfect for

* image classification
* text classification

because the outputs represent probabilities over classes.

---

# Where do activations go?

A very common beginner mistake is

```
Linear

↓

Linear

↓

ReLU
```

Instead,

they go **between** layers.

```
Linear

↓

ReLU

↓

Linear

↓

ReLU

↓

Linear
```

The last layer often has **no activation** (or a task-specific one like Softmax).

---

# Putting it inside `forward()`

Now your `forward()` starts looking like this.

```python
def forward(self, x):

    x = self.layer1(x)
    x = self.relu(x)

    x = self.layer2(x)
    x = self.relu(x)

    x = self.layer3(x)

    return x
```

Read it as a pipeline:

```
Input

↓

Linear

↓

ReLU

↓

Linear

↓

ReLU

↓

Linear

↓

Prediction
```

---

# PyTorch's convenience: `nn.Sequential`

If the data flows in a straight line, PyTorch lets you define the pipeline compactly.

Instead of writing:

```python
self.layer1 = nn.Linear(5, 64)
self.relu1 = nn.ReLU()
self.layer2 = nn.Linear(64, 64)
self.relu2 = nn.ReLU()
```

you can write:

```python
self.network = nn.Sequential(
    nn.Linear(5, 64),
    nn.ReLU(),
    nn.Linear(64, 64),
    nn.ReLU(),
    nn.Linear(64, 4)
)
```

Then your `forward()` becomes almost trivial:

```python
def forward(self, x):
    return self.network(x)
```

`nn.Sequential` simply says:

> "Take the output of one layer and feed it directly into the next."

---

# The cookbook so far

You now know four of the core PyTorch building blocks:

| Component                      | What it is                        | Purpose                                                    |
| ------------------------------ | --------------------------------- | ---------------------------------------------------------- |
| `torch.Tensor`                 | A container of numbers            | Holds data                                                 |
| `nn.Module`                    | A model blueprint                 | Organizes layers and parameters                            |
| `nn.Linear`                    | A learnable linear transformation | Introduces weights and biases                              |
| `nn.ReLU()`, `nn.Tanh()`, etc. | Nonlinear functions               | Make the network capable of learning complex relationships |

At this point, you can **build** a neural network architecture. What you **can't** do yet is make it learn.

That's because we're still missing the other half of machine learning:

```
Prediction
      │
      ▼
Loss
      │
      ▼
Backpropagation
      │
      ▼
Optimizer
      │
      ▼
Updated weights
```

The next lesson is where the training process really begins: **loss functions**. That's the component that tells the network *how wrong it was*, giving it a direction for improvement. Once you understand the loss, backpropagation becomes much more intuitive.
