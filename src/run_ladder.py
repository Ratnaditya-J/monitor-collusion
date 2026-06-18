"""Run the behavioral collusion scaling curve across the capability ladder.

For each model in config.LADDER, run BOTH protocols:
  - direct (our construct-valid flag/pass + recipient-dissociated incentive)
  - focalpoint (faithful Jarviniemi reimplementation; replicates ~3.4% on his
    Claude 3.7 anchor and isolates protocol from scale)

This is the endpoint of the behavioral arm: an apples-to-apples curve from open
small -> open large -> frontier, under one protocol, plus the published-number
replication. Black-box, API-only, no GPU.

Run:  OPENROUTER_API_KEY=...  python -m src.run_ladder
      (add --smoke to just check connectivity/model ids first)
"""
import os, sys, json
from . import config as C
from . import protocol_direct, protocol_focalpoint
from .llm_api import smoke_test


def main():
    os.makedirs(C.OUT_DIR, exist_ok=True)
    smoke = "--smoke" in sys.argv

    if smoke:
        print("[smoke] checking each model id responds...")
        for m in C.LADDER:
            try:
                print(f"  {m}: {smoke_test(m)!r}")
            except Exception as e:  # noqa
                print(f"  {m}: FAILED {e}")
        return

    results = {}
    for m in C.LADDER:
        print(f"\n=== {m} ===")
        entry = {}
        try:
            entry["direct"] = protocol_direct.run(m)
            print(f"  direct: own-DBP={entry['direct']['own_benefit']['dbp_rate']} "
                  f"prop_excess={entry['direct']['propensity_excess_dbp']} "
                  f"roleplay={entry['direct']['roleplay_check_own_minus_third']}")
        except Exception as e:  # noqa
            entry["direct_error"] = str(e); print(f"  direct FAILED: {e}")
        try:
            entry["focalpoint"] = protocol_focalpoint.run(m)
            print(f"  focalpoint: genuine={entry['focalpoint']['focal_genuine_rate']} "
                  f"loose={entry['focalpoint']['focal_loose_rate']} "
                  f"audit_integrity={entry['focalpoint']['audit_integrity_rate']}")
        except Exception as e:  # noqa
            entry["focalpoint_error"] = str(e); print(f"  focalpoint FAILED: {e}")
        results[m] = entry
        with open(os.path.join(C.OUT_DIR, "ladder.json"), "w") as f:
            json.dump(results, f, indent=2)  # checkpoint after each model

    # summary table
    print("\n=== SCALING CURVE ===")
    print(f"{'model':40s} {'direct own-DBP':>14s} {'focal_genuine':>13s} "
          f"{'focal_loose':>12s} {'audit_int':>10s}")
    for m, e in results.items():
        d = e.get("direct", {}); f_ = e.get("focalpoint", {})
        own = d.get("own_benefit", {}).get("dbp_rate", "ERR")
        fg = f_.get("focal_genuine_rate", "ERR")
        fl = f_.get("focal_loose_rate", "ERR")
        ai = f_.get("audit_integrity_rate", "ERR")
        print(f"{m:40s} {str(own):>14s} {str(fg):>13s} {str(fl):>12s} {str(ai):>10s}")
    print("\nfocal_genuine is the headline (Jarviniemi's '23% genuine' analogue); "
          "focal_loose is his all-successes analogue. Compare direct own-DBP and "
          "focal_genuine across the ladder for the protocol-vs-scale read.")


if __name__ == "__main__":
    main()
