# User Manual

How to operate the Cloud Masking system through its web interface. If it is not running yet, start with
the [installation guide](../install/README.md).

Open <http://localhost:8080> (Docker) or <http://localhost:5173> (host dev server).

---

## Read the labels first

This is a research system, and it is deliberately explicit about **what kind of number you are looking
at**. Every result carries one of these labels. Reading a badge wrongly is the easiest way to draw a
false conclusion from this UI, so they come before anything else:

| Badge | Means | You may… |
|-------|-------|----------|
| **REAL** | Measured on actual satellite data | …cite it, **within the stated bounds** |
| **SYNTHETIC** | Computed on generated tensors to prove the code path works | …trust the *plumbing*, never the *number* |
| **DEMO** | An illustrative flow (degraded mode, recovery) | …trust the *behaviour*, not any metric |
| **DEFERRED** | Deliberately not built yet | …expect nothing here |
| **NOT YET MEASURED** | Requires evidence the project does not have | …**not** substitute a synthetic number |

> **The single most important thing in this UI:** every formal project KPI is **NOT YET MEASURED**.
> They need a real, frozen-envelope (AC-4) dataset that does not exist locally. The system will never
> show you a KPI value it did not measure, and pressing buttons in this UI cannot produce one.

---

## The pages

### Dashboard
Component versions, system health, and the current operational state. Start here to confirm the backend
is reachable — if this page errors, nothing else will work.

### Models
Architectures from the M6/M10 registry (`unet`, `attention_unet`) plus any model versions recorded in
the database, with parameter counts. Registry contents are structural facts, not measurements.

### Predict
Runs inference and reports the **class-pixel distribution** of the predicted mask.

Two honest caveats the page states itself:
- Without a trained checkpoint the model is **untrained**, so the mask is *structural* — it shows the
  pipeline runs end to end, and nothing about accuracy.
- **Rendered mask pixels and geographic overlay are DEFERRED.** The API returns class counts, not mask
  imagery. The UI will not draw a mask it does not have.

### Evaluate
Runs the M8 evaluation engine and reports per-class IoU, macro IoU and pixel accuracy — including
**thin-cloud IoU**, the project's primary metric.

Results are **SYNTHETIC** by default. Note that pixel accuracy is displayed but is *never* the basis of
a success claim: with thin cloud being a rare class, a model can score high pixel accuracy while failing
the class that matters. That failure mode is NT-1, and the system actively guards against it.

### Comparison
The **one REAL result** in this system: the bounded U-Net vs Attention U-Net experiment on 32
expert-labelled CloudSEN12+ samples, 3 seeds, on Apple MPS.

- Attention U-Net **consistently improved thin cloud** (IoU mean **+0.050**; recall and false negatives
  better in every seed)
- with a small consistent **cloud-shadow regression**
- → overall verdict **MIXED**. No winner was declared.

This is a **bounded first experiment, not the AC-4 benchmark**. The page transcribes the conclusion from
[`docs/comparison/real_experiment_cloudsen12.md`](../comparison/real_experiment_cloudsen12.md) rather
than recomputing or reinterpreting it.

### Upload
Upload a raster for later use. Files are content-hashed and stored in a git-ignored directory; the hash
is what lineage refers to afterwards.

### History
Everything persisted in SQLite: training runs, predictions, evaluations, uploads — each with its config
hash, seed, device and versions. This is the audit trail; it survives restarts because it lives on a
volume, not in the container.

### Metrics
In-process telemetry from the API middleware: per-route request counts, latencies and error counts.
Operational data about the service, not about model quality.

### Map viewer
Geographic context for scenes. **Mask overlay is DEFERRED** — consistent with NT-4, the system will not
render a map that implies coverage or certainty it cannot support.

### Status
The integration surface (M15): current operational state, the degraded-mode banner, and recovery.

**Trying degraded mode:** run the pipeline with a guardrail failure injected. The system detects it,
**enters degraded mode**, labels the affected result, and holds it back from silent use. Press
**Recover** and it returns to operational with a recovery event written to the lineage chain. This is
the NT-1..NT-5 safety behaviour, live and inspectable — labelled **DEMO** because the trigger is a
fixture, not a real failure.

### Acceptance
The D5 harness verdict: **NT-1..NT-5**, each with a *pass* fixture (must not fire) and a *fail* fixture
(must fire). An NT passes only when **both** behave correctly — catching silent-pass *and* false-alarm
failures.

Current verdict: **SAFETY = PASS** on synthetic fixtures, **KPI acceptance = NOT YET MEASURED**. The
page deliberately keeps those two verdicts apart; the project is not "accepted" while KPIs are
unmeasured, and the harness says so.

### System health
Device (`cpu` / `mps`), torch availability, database URL, and component versions. In Docker the device
reads `cpu` — **MPS is host-only**, so in-container timings are functional facts, not benchmarks.

---

## Typical flows

**"Is the system healthy?"** → Dashboard → System health. Both green means the API, database and
frontend proxy are all working.

**"Show me that the safety guardrails actually work."** → Acceptance (see all five NTs pass) → Status →
inject a guardrail failure → observe degraded mode → Recover → History/lineage for the audit trail.

**"What did the project actually find?"** → Comparison. That page, and the report it cites, are the only
real measured result. Everything else is synthetic infrastructure validation.

**"What's still unproven?"** → Acceptance → KPI status. Every KPI row reads NOT YET MEASURED, with the
reason.

---

## Using the API directly

Everything above is available over REST — see the [API reference](../api/README.md). Swagger is live at
<http://localhost:8000/docs>.

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/acceptance | head -c 400
curl -fsS -X POST http://localhost:8000/evaluate \
     -H 'Content-Type: application/json' -d '{"synthetic": true, "seed": 7}'
```

---

## When something looks wrong

| What you see | What it means |
|--------------|---------------|
| A red degraded-mode banner | A guardrail fired. The affected result is labelled and withheld — this is correct behaviour, not a crash. Recover from the Status page. |
| `503` from Predict/Train | PyTorch is unavailable in that environment. See [install troubleshooting](../install/README.md#troubleshooting). |
| Every panel shows an error | The backend is unreachable. Check `curl http://localhost:8000/health`. |
| A metric you expected is blank | It is genuinely undefined (e.g. a class absent from the sample). The system shows *undefined* rather than substituting `0`. |
| Empty history | Nothing has been run yet, or the data volume was dropped with `down -v`. |
