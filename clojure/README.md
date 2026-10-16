# Tiny Clojure Regression

A small, dependency-free learning project for ordinary least-squares linear regression. It is deliberately separate from PROXORA's Python engine: the first goal is to learn Clojure with a familiar mathematical problem.

## Run it

From this directory, with Clojure CLI installed:

```bash
clojure -M -m proxora.regression
clojure -M:test
```

The example fits the observations `[[0 1] [1 3] [2 5] [3 7]]`, recovers the line `y = 1 + 2x`, and predicts `y = 9` at `x = 4`.

## The math

For observations `[x y]`, ordinary least squares computes:

- `slope = sum((x - mean-x) * (y - mean-y)) / sum((x - mean-x)^2)`
- `intercept = mean-y - slope * mean-x`
- `predict(model, x) = intercept + slope * x`

The implementation uses plain Clojure sequences, `map`, `reduce`, destructuring, maps, and functions. There are no external dependencies.

`predict-next` treats a sequence's positions as x-values `0, 1, 2, ...`, fits a line, then predicts the next position.

## Learning path

1. Read `src/proxora/regression.clj` and trace `fit` with the sample data.
2. Change the sample observations and run the tests.
3. Next, add a strategy contract and two interchangeable regression strategies.
4. After that, evaluate whether Clojure or Kotlin should own orchestration for a mobile-facing architecture.
