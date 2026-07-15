Excellent. Now we finally reach the first **learnable** component in PyTorch.

Everything before this was infrastructure.

Now we introduce the first object that actually contains **θ (parameters)**.

---

# Lesson 3 — `nn.Linear`

If I asked you to write the simplest possible machine learning model, you would probably write

[
y = wx + b
]

where

* (x) = input
* (w) = weight
* (b) = bias

This is exactly what `nn.Linear` implements.

---

# What is `nn.Linear`?

PyTorch's `nn.Linear` is simply a function

```text
Input

↓

Multiply by weights

↓

Add bias

↓

Output
```

Mathematically,

[
y = Wx + b
]

Nothing more.

---

# Why is it called "Linear"?

Because there is **no activation function** inside.

It performs only

```text
Multiply

+

Add
```

For example

```python
layer = nn.Linear(3,2)
```

means

```text
Input

[x₁,x₂,x₃]

↓

Linear

↓

[y₁,y₂]
```

---

# The constructor

```python
layer = nn.Linear(3,2)
```

This is one of the most important lines you'll ever write.

Let's decode it.

---

## First number

```python
3
```

means

> I expect **3 input features**.

Example

```python
x = torch.tensor([
    2.0,
    5.0,
    7.0
])
```

---

## Second number

```python
2
```

means

> Produce **2 outputs**.

So

```text
Input

3 numbers

↓

Linear

↓

2 numbers
```

---

# Where are the parameters?

The beautiful thing is

you don't create them yourself.

PyTorch automatically creates

```text
Weights

+

Bias
```

Let's inspect them.

```python
import torch.nn as nn

layer = nn.Linear(3,2)

print(layer.weight)

print(layer.bias)
```

You might see

```text
Weight

tensor([
 [0.13, 0.44,-0.27],
 [-0.81,0.32,0.56]
])
```

Bias

```text
tensor([
0.17,
-0.42
])
```

Notice something.

You never initialized them.

PyTorch did.

---

# Why random?

Suppose every neuron started with

```text
weight = 0
```

Every neuron would produce exactly the same output.

They'd learn exactly the same thing.

Random initialization breaks that symmetry.

---

# Forward pass

Suppose

```python
layer = nn.Linear(3,2)
```

Input

```python
x = torch.tensor([
    1.,
    2.,
    3.
])
```

Then

```python
y = layer(x)
```

Internally PyTorch computes

```text
Weights

2×3 matrix

×

Input

3×1 vector

+

Bias

↓

2×1 vector
```

---

Let's do the math manually.

Suppose

```text
Weights

[1 2 3]

[4 5 6]
```

Bias

```text
[1

2]
```

Input

```text
[10

20

30]
```

First output

```text
1×10

+

2×20

+

3×30

+

1
```

equals

```text
141
```

Second output

```text
4×10

+

5×20

+

6×30

+

2
```

equals

```text
322
```

Final output

```text
[141

322]
```

That is literally all `Linear` does.

---

# Shape is everything

Suppose

```python
nn.Linear(5,64)
```

The weights have shape

```text
64 × 5
```

because

```text
5 inputs

↓

64 outputs
```

Suppose

```python
nn.Linear(64,32)
```

Weights become

```text
32 × 64
```

Notice the pattern.

```text
Linear(a,b)

↓

Weights

b × a
```

I always remember it as

> **rows = outputs, columns = inputs**

---

# Stacking layers

Now something magical happens.

The output of one layer becomes the input of another.

```python
layer1 = nn.Linear(5,64)

layer2 = nn.Linear(64,32)

layer3 = nn.Linear(32,4)
```

Flow

```text
5

↓

64

↓

32

↓

4
```

Notice how the numbers match.

The previous output dimension becomes the next input dimension.

---

# Why 64?

This is a common beginner question.

Could we use

```python
nn.Linear(5,17)
```

Yes.

Or

```python
nn.Linear(5,100)
```

Also yes.

64 is simply a design choice.

It's called the **hidden dimension**.

Larger

```text
More parameters

↓

More expressive

↓

Slower
```

Smaller

```text
Fewer parameters

↓

Faster

↓

May not learn enough
```

---

# Your PPO example

Remember your state encoding?

Suppose you convert your state into

```python
[
x,
y,
is_white,
is_goal,
is_trap
]
```

That's

```text
5 features
```

Your network could begin with

```python
self.layer1 = nn.Linear(5,64)
```

Graphically

```text
State

↓

[2,0,1,0,0]

↓

Linear(5,64)

↓

64 learned features
```

Notice something important:

The network **doesn't know** what `x`, `y`, or `is_goal` mean.

It simply receives five numbers and learns how to combine them.

---

# Where do these parameters live?

When you write

```python
self.layer1 = nn.Linear(5,64)
```

inside your model,

the parameters become part of the model automatically.

You can inspect them:

```python
for name, param in model.named_parameters():
    print(name, param.shape)
```

For a simple model, you might see:

```text
layer1.weight    torch.Size([64, 5])
layer1.bias      torch.Size([64])
```

Later, when we introduce an optimizer like `Adam`, you won't pass individual weights to it. You'll simply write:

```python
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
```

because `model.parameters()` gathers **every learnable weight and bias** from all the `nn.Linear` layers you've defined.

---

# One remaining problem...

Imagine we build a network like this:

```python
self.l1 = nn.Linear(5,64)
self.l2 = nn.Linear(64,64)
self.l3 = nn.Linear(64,4)
```

and in `forward()` we do:

```python
x = self.l1(x)
x = self.l2(x)
x = self.l3(x)
```

It turns out this entire stack is still just **one big linear transformation**. In other words, three linear layers without anything between them are no more powerful than a single linear layer with appropriately chosen weights.

That is why the **next ingredient** is so important: **activation functions** (`ReLU`, `Tanh`, `Sigmoid`, etc.). They introduce **nonlinearity**, allowing the network to learn complex relationships instead of only straight-line mappings. Without them, deep neural networks wouldn't be any more expressive than simple linear regression.
