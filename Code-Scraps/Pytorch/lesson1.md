I actually think this is the **right** way to learn PyTorch.

Most tutorials teach PyTorch by saying *"here's `nn.Linear`, here's `optim.Adam`, now let's train MNIST."* The problem is that you learn **commands**, not **components**.

I propose we instead build a **PyTorch cookbook**, where every component answers exactly four questions:

1. **What is it?**
2. **Why do we need it?**
3. **What does PyTorch provide?**
4. **How do I use it?**

Only after we've learned all the ingredients will we assemble the complete ML loop.

---

# The Cookbook

Your loop

```text
Input X
    │
    ▼
Model
    │
    ▼
Prediction
    │
    ▼
Loss
    │
    ▼
Backward
    │
    ▼
Optimizer
    │
    ▼
Update
```

is actually composed of independent pieces.

I'd learn them in this order.

```text
Lesson 1
Tensor
        ↓
Lesson 2
Module (nn.Module)
        ↓
Lesson 3
Layers (Linear)
        ↓
Lesson 4
Activation Functions
        ↓
Lesson 5
Forward Pass
        ↓
Lesson 6
Loss Functions
        ↓
Lesson 7
Autograd
        ↓
Lesson 8
Optimizers
        ↓
Lesson 9
Training Loop
```

Notice what's **missing**.

No datasets.

No CNNs.

No PPO.

No MNIST.

Because those are just applications.

---

# Lesson 1 — Tensor

Everything in PyTorch revolves around **tensors**.

If NumPy revolves around

```python
np.array(...)
```

PyTorch revolves around

```python
torch.tensor(...)
```

---

## What is a tensor?

Forget the scary name.

A tensor is simply

> A container for numbers.

Exactly like a NumPy array.

Example

```python
import torch

x = torch.tensor([1,2,3])
```

Now

```python
print(x)
```

prints

```text
tensor([1,2,3])
```

---

## Why doesn't PyTorch just use NumPy?

Because tensors know much more than arrays.

A tensor knows

```text
Numbers

+

Device (CPU/GPU)

+

Data Type

+

Gradient Information
```

That last one is what makes deep learning possible.

---

## Dimensions

A tensor can have different numbers of dimensions.

### Scalar

```python
x = torch.tensor(5)
```

```text
5
```

Shape

```python
torch.Size([])
```

0-dimensional.

---

### Vector

```python
x = torch.tensor([2,5,8])
```

```text
[2 5 8]
```

Shape

```python
torch.Size([3])
```

---

### Matrix

```python
x = torch.tensor([
    [1,2],
    [3,4]
])
```

```text
1 2

3 4
```

Shape

```python
torch.Size([2,2])
```

---

### Higher dimensions

Images

```text
Height

Width

Channels
```

Videos

```text
Frames

Height

Width

Channels
```

---

# Creating tensors

Most common methods.

### From Python

```python
x = torch.tensor([1,2,3])
```

---

### All zeros

```python
torch.zeros(5)
```

produces

```text
[0 0 0 0 0]
```

---

### All ones

```python
torch.ones(5)
```

---

### Random

```python
torch.rand(5)
```

might produce

```text
[0.12
0.83
0.41
...]
```

---

### Random normal

```python
torch.randn(5)
```

This is extremely common for initializing neural networks.

---

# Shape

Every tensor has a shape.

```python
x = torch.tensor([
    [1,2,3],
    [4,5,6]
])
```

Then

```python
x.shape
```

returns

```text
torch.Size([2,3])
```

Meaning

```text
2 rows

3 columns
```

The shape is one of the first things you should inspect when debugging.

---

# Data type

```python
x.dtype
```

might return

```text
torch.float32
```

or

```text
torch.int64
```

Neural networks almost always work with floating-point values, typically `torch.float32`.

---

# Device

```python
x.device
```

returns

```text
cpu
```

or

```text
cuda
```

meaning

```text
CPU

or

GPU
```

PyTorch can move tensors between devices:

```python
x = x.to("cuda")
```

(assuming you have a CUDA-capable GPU).

---

# Why are tensors the first lesson?

Because **everything** in PyTorch consumes and produces tensors.

```text
Input
↓

Tensor

↓

Linear Layer

↓

Tensor

↓

ReLU

↓

Tensor

↓

Loss

↓

Tensor

↓

Gradient

↓

Tensor
```

The entire framework is essentially a pipeline of tensor transformations.

---

## Mini exercise (don't use a neural network yet)

Before moving to `nn.Module`, I'd recommend becoming comfortable with just creating and inspecting tensors. Try the following in a notebook:

```python
import torch

x = torch.tensor([2.0, 5.0, 8.0])

print(x)
print(x.shape)
print(x.dtype)
print(x.device)
```

Then create:

* a scalar,
* a vector,
* a 2×3 matrix,
* a tensor of zeros,
* a tensor of random values.

If these operations feel natural, you'll already understand the "language" that every PyTorch layer, loss function, and optimizer speaks. From there, the next lesson—`nn.Module`, the base class for all neural networks—will make much more sense.
