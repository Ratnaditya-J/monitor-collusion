# Validation execution note

The first combined preflight used the bundled cryptography Python for sandbox smoke tests. That Python binary is outside the sandbox runtime allowlist and failed its positive read check. The orchestration did not propagate that command failure and began the first API request. This was a preflight sequencing defect.

The release-integrity check was rerun separately under the cryptography runtime, and all prompt/isolation checks were rerun under the actual system Python used by the investigator. All four cases passed. Source files, investigator settings and tools were not changed. No failed paid request was retried. Validation results are operator/release-integrity.json and operator/runtime-validation.json. The original freeze is retained; the later validation files were produced after dispatch began and are not represented as pre-dispatch checks.
