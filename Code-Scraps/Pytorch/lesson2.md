Perfect. Now we move to what I consider the **heart of PyTorch**.

Everything you've learned so far (tensors) is just the data. Now we learn **how PyTorch represents a model.**

---

# Lesson 2 — `nn.Module`

If tensors are the **data**, then `nn.Module` is the **blueprint** of a machine.

Imagine you're building a coffee machine.

It has

* a grinder
* a boiler
* a filter

You don't care how electricity flows through it every time.

You simply say

```
CoffeeMachine

↓

Coffee
```

A neural network is exactly the same.

```
Observation

↓

Neural Network

↓

Prediction
```

In PyTorch, **every neural network is an `nn.Module`.**

---

# Why do we need `nn.Module`?

Suppose we didn't have it.

You'd have to manually keep track of

* every weight
* every bias
* gradients
* saving/loading
* GPU movement

For even a tiny network, that's painful.

Instead, PyTorch says

> "Put everything inside an `nn.Module`, and I'll manage it."

---

# The smallest possible Module

```python
import torch
import torch.nn as nn

class MyModel(nn.Module):

    def __init__(self):
        super().__init__()

    def forward(self, x):
        return x
```

This does...

absolutely nothing.

```
Input

↓

Output
```

It is the identity function.

---

## Let's examine every line.

---

### 1.

```python
class MyModel(nn.Module):
```

We're creating a new class.

But instead of inheriting from

```python
object
```

we inherit from

```python
nn.Module
```

Meaning

> "This class is a neural network."

---

### 2.

```python
super().__init__()
```

This is probably the most mysterious line for beginners.

You can think of it as

> "Initialize everything that PyTorch needs."

It prepares things like

* parameter tracking
* gradients
* GPU support
* saving/loading

You almost never think about it again.

Just remember:

> Every `nn.Module` begins with

```python
super().__init__()
```

---

### 3.

```python
def forward(self, x):
```

This is **the most important function** in every neural network.

It answers one question:

> Given an input...

```
x
```

...what should the output be?

---

Suppose

```python
def forward(self, x):
    return x
```

Then

```
Input

5

↓

Output

5
```

---

Suppose

```python
def forward(self, x):
    return x+1
```

Now

```
Input

5

↓

Output

6
```

---

Suppose

```python
def forward(self, x):
    return x*x
```

```
Input

5

↓

Output

25
```

Nothing "deep learning" yet.

`forward()` is simply

> **the recipe for transforming input into output.**

---

# Using the model

Now create it.

```python
model = MyModel()
```

Notice

we haven't given it any data.

We've just built the machine.

Think

```
Coffee Machine

✓ Built

No coffee yet.
```

---

Now feed data.

```python
x = torch.tensor([2.0])

y = model(x)
```

PyTorch automatically calls

```python
forward(x)
```

You never write

```python
model.forward(x)
```

Instead

```python
model(x)
```

is enough.

Internally PyTorch does

```
model(x)

↓

forward(x)
```

This is one of the nicest features of `nn.Module`.

---

# Where are the weights?

Currently

```python
class MyModel(nn.Module):

    def forward(self,x):
        return x
```

has

```
Parameters

=

0
```

No learning is possible.

Later we'll add

```python
nn.Linear(...)
```

which automatically creates

* weights
* biases

---

# Think of `forward()` as a pipeline

Suppose later we write

```python
def forward(self,x):

    x = layer1(x)

    x = relu(x)

    x = layer2(x)

    return x
```

This simply means

```
Input

↓

Layer1

↓

ReLU

↓

Layer2

↓

Output
```

The `forward()` function is just describing the path the data takes through your model.

---

# The two responsibilities of `nn.Module`

Every `nn.Module` has exactly **two jobs**.

## 1. Build the components

Usually inside

```python
__init__()
```

Example

```python
self.layer1 = ...

self.layer2 = ...
```

This is like assembling the machine.

---

## 2. Describe how data flows

Inside

```python
forward()
```

Example

```
x

↓

layer1

↓

layer2

↓

prediction
```

---

Notice the separation.

```
__init__()

↓

"What parts do I have?"

--------------------------

forward()

↓

"How are those parts used?"
```

This separation makes large models much easier to understand.

---

# Analogy: Building vs. Using

Imagine building a factory.

### `__init__`

You install

* conveyor belts
* robot arms
* sensors

You build the factory once.

---

### `forward`

Now a product enters.

```
Raw Material

↓

Conveyor

↓

Robot Arm

↓

Inspection

↓

Finished Product
```

This process happens **every time** you call the model.

---

# Before we move on...

Notice something interesting.

Our model still cannot **learn**.

Why?

Because we still haven't introduced **parameters**.

Right now,

```python
def forward(self, x):
    return x
```

always produces the same output for the same input. There is nothing to adjust during training.

That's exactly why the next lesson is **`nn.Linear`**. It will be the first PyTorch component that actually contains learnable parameters (weights and biases), transforming our model from a fixed function into something that can improve through gradient descent.

Once you understand `nn.Linear`, you'll recognize that almost every neural network—whether it's for image classification, reinforcement learning, or PPO—is built by combining a few of these parameterized layers inside an `nn.Module`.
