# Review a property or a minimized failure

First identify what would make the assertion fail. A check that calls the function
twice may establish determinism, but cannot by itself establish that either result
is correct. Comparing a calculation with the same formula copied into the test
misses defects shared by both copies.

Inspect the generator's actual domain and health-check output. Prefer constrained
strategies over extensive filtering; retain relevant zero/empty/equality/maximal
cases. Ensure invalid examples genuinely violate the input contract, and that
valid examples are not rejected because they are inconvenient for the implementation.

Useful harness properties include applying the same configuration twice without
changes, preserving user text outside a managed block, and ensuring that raising a
coverage threshold cannot turn a fixed failing report into success. Each property
needs its stated domain; for example, preservation assumes valid, unique managed
markers rather than requiring malformed documents to be accepted.

For a counterexample, reduce it with the real framework, then read the independent
contract and relevant code. Separate:

- A correct input that reveals an implementation defect.
- An input outside the promised domain that the generator wrongly admitted.
- A property the specification does not actually promise.
- Shared environment, ordering or state that invalidates test isolation.

Record the minimized example, expected result and reason. Fix the responsible
artifact within the requested scope. Preserve a concrete regression alongside a
corrected generated test. If the oracle is uncertain, report uncertainty instead
of changing expected output to the implementation's current answer.
