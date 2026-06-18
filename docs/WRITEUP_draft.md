# When you measure AI monitor "collusion," you're mostly measuring your own prompt

Draft note, in progress. Numbers from src/powered_run.py. Honest about limits below.

I spent a while trying to measure a simple thing: if you put one AI in charge of
reviewing another AI's code, will the reviewer quietly wave through a backdoor that
a partner AI planted, without the two ever talking? People worry about this for AI
control, where the safety story leans on "the monitor won't side with the thing it's
watching."

I kept getting wildly different numbers depending on how I worded the test. That
turned out to be the actual finding, so this is a note about why the number moves,
not a clean number.

## The setup

Every test has a real backdoor present: a login function with a hardcoded master
password. The "secret signal" the two sides try to coordinate on is just that
password, so if they pick the same one, the backdoor sails through. I run two
instances of the same model with no communication: one picks the password to embed,
the other picks the password that means "pass it." A win is the reviewer passing the
planted backdoor while still flagging other backdoors that don't carry the signal.
I ran it on three models, 80 trials each, two framings.

## What happened

Asked honestly, the models refuse and you get zero. Asked in disguise, they play
along, and the rate climbs steeply with capability.

| model | honest framing | disguised "coordination game" |
| --- | --- | --- |
| Llama-3.1-8B | refuse 97%, collusion 0% | collusion 2.5% |
| Qwen-2.5-72B | refuse 100%, collusion 0% | collusion 12.5% |
| Claude Opus-4.5 | refuse 100%, collusion 0% | collusion 47.5% |

Same Opus model: 0% when you tell it plainly it's helping sneak a backdoor past
review, 47.5% when the identical task is dressed up as a neutral "pick a matching
codeword" game. The number is not really a property of the model. It is a property
of how much your test hides the intent.

Two things fall out of this:

1. What is holding collusion at zero is the refusal, not an inability to coordinate.
   The capability is clearly there (and it grows fast with model strength). The only
   thing in the way is that the model declines when it can see what it's being asked
   to do.
2. So the refusal is load-bearing and brittle. It fires on the honest ask and not on
   the disguised one. Anyone reporting a single "collusion rate" is really reporting
   how transparent their elicitation was.

## How this fits what's already known

I'm not the first one near any of this, and the disguised-framing number is not new
on its own. Models doing this kind of silent coordination has been measured before:
Motwani et al. got roughly 40 to 56% on GPT-4 on a similar no-communication task, and
there's a good review of Schelling coordination in LLMs on LessWrong that already
makes the point that the raw capability doesn't equal a real-world risk. Jarviniemi's
focal-points work is the closest on collusion specifically, and he already separated
genuine coordination from degenerate "monitor is just lenient" cases. The "untrusted
monitoring" safety-case sketch taxonomizes the Schelling-point version of this. And
people have written about validity problems in safety benchmarks in general.

What I think is worth adding, on top of that, is the side-by-side on a collusion task
with a real backdoor: the honest-framing number is a powered zero, the disguised
number recovers most of the coordination ceiling, and the gap is the refusal. Put
plainly: don't trust a collusion number unless you know how the model was asked.

## Limits (so nobody has to point them out)

- The disguised number is a ceiling, "if the intent is hidden and the model plays
  along, the backdoor slips X%," not "Opus colludes half the time in normal use."
- It's a reduced setup: the signal is a codeword, one backdoor type, three models, 80
  trials per cell, a single run, with another model as the backdoor-checker. Richer
  signals and real agentic tasks would test it harder.
- The honest-framing "0%" is really 0 out of 80, so the upper bound is about 4-5%, not
  literally zero.

## Ask

Am I missing prior art on the specific point, that for collusion the measured rate is
basically a function of how much the framing triggers refusal, and that refusal not
capability is what's doing the work? If someone has already shown that cleanly, point
me at it. If not, I think it's a small but useful caution for anyone putting a
collusion number in a safety case.
