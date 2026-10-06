# Process tracing: mechanisms, predictions and rivals

How to state a process-tracing mechanism as parts, write predictions that can fail, and give the rivals the same treatment: the part that has to be done before any evidence is read, and that decides whether the rest of the method has anything to work on.

Back to [process tracing](process-tracing.md).

## A mechanism is parts, not a story

Beach and Pedersen's formulation is the useful one: a mechanism is a sequence of parts, each of which is an entity engaging in an activity. The entity is somebody or something that acts. The activity is what it does that carries causal force to the next part.

"The training improved service quality" names no entity and no activity, so it yields no prediction and cannot be traced. Broken into parts it might run: trained supervisors (entity) began holding monthly case reviews (activity); case reviews surfaced errors in referral (activity) that supervisors then raised with clinic managers (entity, activity); managers changed the referral form (entity, activity); staff using the changed form referred more accurately (entity, activity).

Four parts. Each either happened or did not, and each should have left something behind. That is the difference between a mechanism and a claim.

Two disciplines while decomposing.

**Each part must be capable of failing on its own.** If part three cannot be false while parts two and four are true, it is not a separate part, it is a restatement.

**Stop at the level where evidence exists.** Decomposition can go on indefinitely, with no natural floor. The floor in practice is the level at which a part would have left a trace somebody could find. Going finer produces predictions nothing could test.

## Predictions, which are the product

For each part, write what should be observable if that part operated, and what should be observable if it did not. Both halves. A prediction with no disconfirming counterpart cannot fail. A test that cannot fail is decoration.

The form to write them in:

- **What.** The specific thing: a document, a decision, a line in a budget, a recollection from a person in a position to know.
- **Where it would be.** Which source, or which kind of source. This is what makes the search checkable afterwards.
- **Why its presence would be surprising if the mechanism did not run.** The argument for its probative value. That is the [evidence tests](process-tracing-evidence-tests.md) question, and it belongs here rather than attached later as a label.
- **What its absence would mean.** Whether not finding it is decisive, damaging or unremarkable.

Write predictions specific enough that two people would agree whether the thing was found. "Evidence of manager engagement" fails that. "Minutes of at least one management meeting between March and June recording a decision about the referral form" passes it.

## Rivals get the same treatment

A rival explanation named in a sentence and never tested does nothing for the inference. The probative value of any piece of evidence comes from how unlikely it would be under the rivals. So the rivals have to be specific enough for that to be assessable.

Three families worth writing out for programme work.

**Something else caused it.** A different programme, a policy change, a change in prices, a new manager who would have done this anyway. Name the specific alternative rather than the category.

**It was already happening.** The trend predates the intervention. This is the rival most often ignored, and usually the strongest, because the evidence for the mechanism operating is often equally consistent with it.

**It did not happen.** The outcome is reported rather than real, or is real and smaller than claimed. Worth writing out where the outcome rests on self-report.

For each rival, write predictions the same way. Then note where a prediction is shared: a piece of evidence consistent with both the mechanism and a rival has no discriminating power however striking it looks. Marking those in advance stops them being reported as findings.

## Registering the register

The predictions have to be fixed before the search, and a reader has to be able to see that they were. This is the method's central claim to rigour and the one thing published process tracing almost never demonstrates.

Two ways it goes wrong even in careful hands. Predictions get sharpened after a first pass through the material, so what began as "some record of a management decision" becomes, after somebody has seen the minutes, "a decision about the referral form", which the evidence then confirms. And predictions get dropped without a note when nothing turns up, so the register reaching the report contains only the tests that passed.

Both are prevented by the same discipline: version the register, date each version, and report the whole of the final one, including the predictions that failed and the ones abandoned. Revising a register is legitimate. Revising it without a trace is the fault.

A code step's column definitions are a register of this kind: the designer writes each prediction as a value of a nominal or binary column, with what counts and what does not, before any document is read. A run's record is not rewritten once made, so a register tightened after a first pass runs as a new workflow with its own resolved settings and its own coded rows; both stay in the record rather than the first being overwritten, which is [the argument for running it there](process-tracing-in-rubicon.md). The record shows the order rather than enforcing it: nothing compares when a definition was written with when the reading began, so keeping the order is still the author's job.

## What to record per prediction

At registration: the part it belongs to, the hypothesis or rival it serves, what would be found and where, the argument for why its presence is unlikely under the rivals, and what its absence would mean.

After the search: found or not found, the passages if found, where the search ran if not, and what the result did to confidence. A prediction never searched for is a different thing from one searched for and not found. The register has to distinguish them.

That last distinction is the whole of the [negative-evidence problem](process-tracing-evidence-tests.md#absence-of-evidence). Coding a prediction as a column over the sample's documents keeps the two apart: a document outside the sample carries no row and no count, while a document inside it that the coder found wanting is counted among those read and coded absent. A code step's record says which sections of each document it read and any whose reply could not be read, which is how far an absent result can be trusted.
