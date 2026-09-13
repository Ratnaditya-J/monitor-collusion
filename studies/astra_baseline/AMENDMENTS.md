# Operational amendment A1

First response contained two byte-identical tool-request messages. The original parser concatenated them and failed JSON parsing. It now accepts identical repeated output once, rejecting conflicting messages. Two regression tests added; all 12 checks pass. No scientific outcome had been produced or inspected. Prompts, fixtures, settings, order and scoring remain frozen. Original FREEZE preserved; cached response reused without paid retry. First request usage-priced charge: $0.0157.
