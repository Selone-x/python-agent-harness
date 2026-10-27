# Evidence for a requirement verdict

Keep each requirement's reasoning independently inspectable. Include:

- Requirement ID, exact document location/version and whether it is mandatory.
- Testable predicate: inputs, expected result/error, invariant and stated exceptions.
- Implementation locations actually read, including caller/callee and alternate paths.
- Searches and their results, especially for `absent`; describe scope cutoffs.
- Relevant test locations, independent expected-value source and actual commands/results.
- Verdict, counterevidence considered, consequence and documentation uncertainty.
- Independent review status; do not label self-review as independent confirmation.

For a partial implementation, identify both an enforced path and a violating path.
For an absence, consider whether enforcement belongs to a caller, dependency or
configuration rather than the function named in the requirement. For stronger
behavior, establish the additional restriction and its observable consequence.

Example: a specification promises that retrying an event cannot create a second
order. Finding a cache named `deduplication` is insufficient. Trace which event ID
is saved, when it is committed, what happens after a timeout, and whether retry
uses the same ID. A test must observe order creation and the repeated outcome;
counting visits to a helper does not establish the business invariant.

End a report with requirements not checked, inaccessible documents, unavailable
dependencies and tests not executed. A limited scope may be complete within its
bounds; do not imply whole-project compliance from that limited result.
