"""Minimal gradient descent demo for the machine-learning knowledge base.

Related node: ml_gradient_descent
Source IDs: book_hands_on_ml_3e_zh, docs_sklearn_user_guide
"""

from __future__ import annotations


def optimize(initial_x: float = 5.0, learning_rate: float = 0.1, steps: int = 30) -> list[float]:
    """Minimize f(x) = (x - 2)^2 with gradient descent."""
    x = initial_x
    history = [x]
    for _ in range(steps):
        gradient = 2 * (x - 2)
        x = x - learning_rate * gradient
        history.append(x)
    return history


if __name__ == "__main__":
    values = optimize()
    print(f"final_x={values[-1]:.4f}")
