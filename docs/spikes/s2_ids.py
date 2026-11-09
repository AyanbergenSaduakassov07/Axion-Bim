"""Spike 2: run IDS with ifctester and inspect result structure."""
import sys, json, time
import ifcopenshell
from ifctester import ids, reporter

f = ifcopenshell.open(sys.argv[1])
specs = ids.open(sys.argv[2], validate=True)
t = time.perf_counter(); specs.validate(f); print("validate_s", round(time.perf_counter() - t, 3))
for s in specs.specifications:
    print("SPEC", s.name, "status", s.status, "applicable", len(s.applicable_entities), "failed_entities", len(getattr(s, "failed_entities", [])))
    for r in s.requirements:
        print("  REQ", type(r).__name__, "status", r.status, "failures", len(r.failures))
        for fl in r.failures[:2]:
            print("    FAIL", type(fl).__name__ if not isinstance(fl, dict) else fl.keys(), fl if isinstance(fl, dict) else vars(fl) if hasattr(fl, "__dict__") else fl)
rep = reporter.Json(specs); rep.report()
d = rep.to_string() if hasattr(rep, "to_string") else json.dumps(rep.results, default=str)
j = json.loads(d)
print("JSON top keys", list(j.keys()))
s0 = j["specifications"][1]
print("spec keys", list(s0.keys()))
print("req keys", list(s0["requirements"][0].keys()))
print(json.dumps(s0["requirements"][0], default=str)[:900])
