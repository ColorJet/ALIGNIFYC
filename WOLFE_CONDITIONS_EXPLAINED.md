# Wolfe Conditions & Line Search - Early Stopping Explained

## What Are Wolfe Conditions?

The **Wolfe conditions** are mathematical criteria that determine when a line search optimization has found a "good enough" step size. They're a KEY stopping mechanism for QuasiNewtonLBFGS and other line search optimizers.

### Two Conditions Must Be Met:

#### 1. **Sufficient Decrease (Armijo Condition)**
```
f(x + α*p) ≤ f(x) + c₁ * α * ∇f(x)ᵀp
```
**Meaning**: The new position must decrease the cost function by at least `c₁ * gradient * step_size`

**Parameter**: `WolfeParameterSigma` = 0.0001 (typically 0.0001 to 0.001)
- Smaller = More strict (requires more decrease)
- Larger = More lenient

#### 2. **Curvature Condition**
```
|∇f(x + α*p)ᵀp| ≤ c₂ * |∇f(x)ᵀp|
```
**Meaning**: The gradient at the new position must be sufficiently flat (not too steep)

**Parameter**: `WolfeParameterGamma` = 0.9 (typically 0.9 for Newton, 0.1 for steepest descent)
- Closer to 1.0 = More strict curvature requirement
- Newton methods use 0.9, gradient descent uses 0.1

## Why This Matters for Early Stopping

### Without Wolfe Conditions (ASGD)
```
Iteration 1: cost = 1000 → step
Iteration 2: cost = 950  → step
Iteration 3: cost = 945  → step
Iteration 4: cost = 943  → step
...
Iteration 500: cost = 942 → STOP (max iterations)
```
**Problem**: Keeps iterating even when barely improving (945 → 943 in 497 iterations!)

### With Wolfe Conditions (QuasiNewtonLBFGS)
```
Iteration 1: cost = 1000 → step (Wolfe satisfied ✓)
Iteration 2: cost = 950  → step (Wolfe satisfied ✓)
Iteration 3: cost = 945  → step (Wolfe satisfied ✓)
Iteration 4: cost = 943  → step (Wolfe NOT satisfied ✗)
Line search fails to find valid step → STOP EARLY!
```
**Result**: Stops at iteration 4 when improvement becomes negligible!

## Elastix Parameters Explained

### Core Stopping Parameters

```python
# Wolfe condition enforcement
"StopIfWolfeNotSatisfied": "true"  # ← KEY! Stop if line search can't satisfy Wolfe
```
- `true`: Stop when no valid step found (EARLY STOPPING!)
- `false`: Continue with invalid steps (may diverge)

### Wolfe Condition Tuning

```python
# Sufficient decrease parameter (c₁)
"WolfeParameterSigma": "0.0001"
```
- Range: 0.0001 to 0.001
- Smaller = Requires more decrease per step
- **0.0001** = Standard strict value (recommended)

```python
# Curvature parameter (c₂)
"WolfeParameterGamma": "0.9"
```
- Range: 0.1 to 0.99
- **0.9** = For Newton methods (QuasiNewton, L-BFGS)
- **0.1** = For steepest descent methods
- Larger = More strict curvature requirement

### Line Search Accuracy

```python
# L-BFGS update accuracy
"LBFGSUpdateAccuracy": "5"
```
- Range: 3 to 10
- Lower = Faster but less accurate
- Higher = Slower but more accurate
- **5** = Good balance

```python
# Maximum line search iterations per optimization step
"MaximumNumberOfLineSearchIterations": "20"
```
- How many times to try finding a valid step
- If exceeded, Wolfe conditions are NOT satisfied
- If `StopIfWolfeNotSatisfied=true`, this triggers early stopping!

## Real-World Example

### Fabric Registration Scenario

**Image characteristics**: Fabric texture with 10-pixel shift

#### Without Wolfe Stopping (ASGD)
```
Resolution 1 (8x):  100 iterations → cost: 1000 → 800
Resolution 2 (4x):  100 iterations → cost: 800  → 650
Resolution 3 (2x):  150 iterations → cost: 650  → 620
Resolution 4 (1x):  150 iterations → cost: 620  → 618
TOTAL: 500 iterations, time: 2.5s
```
**Problem**: Last 150 iterations only improved 620 → 618 (0.3% improvement!)

#### With Wolfe Stopping (QuasiNewtonLBFGS)
```
Resolution 1 (8x):  25 iterations → cost: 1000 → 800 ✓
Resolution 2 (4x):  30 iterations → cost: 800  → 650 ✓
Resolution 3 (2x):  45 iterations → cost: 650  → 620 ✓
Resolution 4 (1x):  20 iterations → cost: 620  → 619
  Iteration 21: Line search fails (Wolfe not satisfied)
  → STOP! (cost improvement < tolerance)
TOTAL: 120 iterations, time: 0.9s
```
**Result**: 76% faster! (2.5s → 0.9s)

## Parameter Combinations

### Aggressive (Fast, May Miss Fine Details)
```python
"WolfeParameterSigma": "0.001",      # Lenient decrease requirement
"WolfeParameterGamma": "0.95",       # Very strict curvature
"LBFGSUpdateAccuracy": "3",          # Lower accuracy
"MaximumNumberOfLineSearchIterations": "10"
```
**Use for**: Quick previews, well-aligned images

### Balanced (Recommended)
```python
"WolfeParameterSigma": "0.0001",     # Standard
"WolfeParameterGamma": "0.9",        # Standard for Newton
"LBFGSUpdateAccuracy": "5",          # Good balance
"MaximumNumberOfLineSearchIterations": "20"
```
**Use for**: General fabric registration, real-time use

### Conservative (Slow, High Accuracy)
```python
"WolfeParameterSigma": "0.00001",    # Very strict decrease
"WolfeParameterGamma": "0.85",       # Moderate curvature
"LBFGSUpdateAccuracy": "8",          # High accuracy
"MaximumNumberOfLineSearchIterations": "50"
```
**Use for**: Difficult registrations, final quality pass

## Debugging Wolfe Conditions

### Console Output Interpretation

**Good convergence:**
```
Resolution 0: Iteration 50: metric = 100.5
Wolfe conditions satisfied: true
Resolution 0: Iteration 51: metric = 95.3
...
Stopping condition: Converged! (Line search satisfied Wolfe conditions)
```

**Early stopping triggered:**
```
Resolution 2: Iteration 120: metric = 10.2
Line search: Could not find valid step satisfying Wolfe conditions
Stopping condition: StopIfWolfeNotSatisfied=true → EARLY STOP
```

**Warning - may need tuning:**
```
WARNING: Line search failed for 5 consecutive iterations
Consider adjusting WolfeParameterSigma or increasing MaximumNumberOfLineSearchIterations
```

## Common Issues & Solutions

### Issue: Registration stops too early (poor quality)
**Cause**: Wolfe conditions too strict  
**Solution**:
```python
"WolfeParameterSigma": "0.001",  # Increase from 0.0001
"MaximumNumberOfLineSearchIterations": "30"  # Increase from 20
```

### Issue: Registration still runs full iterations
**Cause**: Wolfe stopping not enabled  
**Solution**:
```python
"StopIfWolfeNotSatisfied": "true",  # Must be true!
"MinimumStepLength": "1e-6",  # Also helps stop early
```

### Issue: Registration fails with "Line search failed"
**Cause**: Wolfe conditions too strict or bad initialization  
**Solution**:
```python
"WolfeParameterSigma": "0.001",      # Relax
"WolfeParameterGamma": "0.8",        # Relax
"StopIfWolfeNotSatisfied": "false",  # Don't stop on failure
```

## Integration with Other Stopping Criteria

QuasiNewtonLBFGS uses **multiple stopping criteria**:

1. **Wolfe Conditions** (primary):
   - `StopIfWolfeNotSatisfied=true` → Stop when line search fails
   
2. **Minimum Step Length**:
   - `MinimumStepLength=1e-6` → Stop when steps become tiny
   
3. **Gradient Magnitude**:
   - `GradientMagnitudeTolerance=1e-6` → Stop when gradient flat
   
4. **Value Tolerance**:
   - `ValueTolerance=1e-5` → Stop when cost change small
   
5. **Maximum Iterations** (safety):
   - `MaximumNumberOfIterations=500` → Hard limit

**First condition met triggers stop!**

## Mathematical Background

### Why Newton Methods Need Wolfe?

Newton methods approximate the Hessian (second derivative):
```
x_{k+1} = x_k - [H(x_k)]^(-1) * ∇f(x_k)
```

**Problem**: Full Newton step may overshoot or diverge.

**Solution**: Line search finds optimal step size α:
```
x_{k+1} = x_k - α * [H(x_k)]^(-1) * ∇f(x_k)
```

Wolfe conditions ensure α is "good":
- Not too small (wastes iterations)
- Not too large (overshoots minimum)
- Curvature acceptable (converging, not diverging)

### L-BFGS Specifics

L-BFGS approximates Hessian from last `LBFGSMemory` iterations:
```
H_k ≈ f(s_0, y_0, s_1, y_1, ..., s_m, y_m)
where:
  s_i = x_{i+1} - x_i  (step)
  y_i = ∇f(x_{i+1}) - ∇f(x_i)  (gradient change)
  m = LBFGSMemory
```

Higher memory = better Hessian approximation = faster convergence  
But: More memory = slower per iteration

**Balance**: `LBFGSMemory=10` is standard

## References

- Nocedal & Wright, "Numerical Optimization" (2006), Chapter 3
- Elastix manual: https://elastix.lumc.nl/doxygen/parameter.html
- Wolfe, P. "Convergence Conditions for Ascent Methods" (1969)

---

**Key Takeaway**: `StopIfWolfeNotSatisfied=true` is the PRIMARY early stopping mechanism for QuasiNewtonLBFGS. Without it, the optimizer may run full iterations even when converged!

**Implementation Status**: ✅ Now correctly configured in `elastix_registration.py`
