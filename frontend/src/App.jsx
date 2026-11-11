import { useEffect, useRef, useState } from "react";
import ResultPanel from "./ResultPanel";
import "./App.css";

const initialForm = {
  passenger_name: "",
  booking_reference: "",
  airline: "",
  flight_number: "",
  origin: "",
  destination: "",
  scheduled_departure: "",
  description: "",
  reported_disruption: "cancellation",
  notice_minutes: "",
  block_time_minutes: "",
  alternate_flight_offered: "",
  alternate_flight_accepted: "",
  alternate_departure: "",
  contact_details_provided: ""
};

const steps = ["Flight details", "Disruption", "Review & submit"];

async function readResponse(response) {
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(`Invalid server response (HTTP ${response.status})`);
    }
  }
  if (!response.ok) {
    if (Array.isArray(data.errors)) {
      throw new Error(data.errors.map((item) => {
        const field = item.field || (Array.isArray(item.loc) ? item.loc.join(".") : "Claim");
        return `${field}: ${item.message || item.msg || "Invalid input"}`;
      }).join(" | "));
    }
    throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (HTTP ${response.status})`);
  }
  return data;
}

function Arrow({ diagonal = false }) {
  return <span aria-hidden="true" className="button-arrow">{diagonal ? "↗" : "→"}</span>;
}

function Field({ label, children, hint, wide = false }) {
  return (
    <label className={`field ${wide ? "field-wide" : ""}`}>
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

function App() {
  const [form, setForm] = useState(initialForm);
  const [step, setStep] = useState(0);
  const [stepError, setStepError] = useState("");
  const [runId, setRunId] = useState("");
  const [status, setStatus] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const formRef = useRef(null);
  const resultRef = useRef(null);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setStepError("");
  }

  function nextStep() {
    const requiredFields = step === 0
      ? ["passenger_name", "booking_reference", "airline", "flight_number", "origin", "destination", "scheduled_departure"]
      : ["description"];
    const missing = requiredFields.find((name) => !String(form[name]).trim());
    if (missing) {
      setStepError("Please complete the required fields before continuing.");
      formRef.current?.querySelector(`[name="${missing}"]`)?.focus();
      return;
    }
    if (step === 0) {
      if (!/^[A-Z0-9]{6}$/.test(form.booking_reference.trim().toUpperCase())) {
        setStepError("Booking reference must contain exactly 6 letters or numbers.");
        return;
      }
      if (!/^[A-Z0-9]{2}[0-9]{1,4}$/.test(form.flight_number.trim().toUpperCase())) {
        setStepError("Enter a valid flight number, such as 6E123.");
        return;
      }
      if (![form.origin, form.destination].every((value) => /^[A-Z]{3}$/.test(value.trim().toUpperCase()))) {
        setStepError("Use a 3-letter airport code for both airports, such as BLR or DEL.");
        return;
      }
      if (form.origin.trim().toUpperCase() === form.destination.trim().toUpperCase()) {
        setStepError("Origin and destination must be different airports.");
        return;
      }
      if (!Number.isFinite(new Date(form.scheduled_departure).getTime())) {
        setStepError("Enter a valid scheduled departure date and time.");
        return;
      }
    }
    if (step === 1 && form.description.trim().length < 10) {
      setStepError("Please describe the disruption in at least 10 characters.");
      return;
    }
    setStepError("");
    setStep((current) => Math.min(current + 1, 2));
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function prepareClaim() {
    const claim = { ...form };
    ["booking_reference", "flight_number", "origin", "destination"].forEach((name) => {
      claim[name] = form[name].trim().toUpperCase();
    });
    claim.scheduled_departure = new Date(form.scheduled_departure).toISOString();
    claim.alternate_departure = form.alternate_departure ? new Date(form.alternate_departure).toISOString() : null;
    ["notice_minutes", "block_time_minutes"].forEach((name) => {
      claim[name] = form[name] === "" ? null : Number(form[name]);
    });
    ["alternate_flight_offered", "alternate_flight_accepted", "contact_details_provided"].forEach((name) => {
      claim[name] = form[name] === "" ? null : form[name] === "true";
    });
    return claim;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (step < 2 || loading) return;
    setLoading(true);
    setError("");
    setResult(null);
    setRunId("");
    setStatus("");
    try {
      const claim = prepareClaim();
      const response = await fetch("/api/claims", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(claim)
      });
      const data = await readResponse(response);
      if (!data.run_id) throw new Error("The backend did not return a Run ID");
      setRunId(data.run_id);
      setStatus(data.status || "queued");
      window.setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 150);
    } catch (err) {
      setError(err.message || "Could not submit the claim");
      window.setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 150);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!runId || status === "completed" || status === "failed") return;
    let active = true;
    let polling = false;
    async function checkStatus() {
      if (polling) return;
      polling = true;
      try {
        const response = await fetch(`/api/runs/${encodeURIComponent(runId)}`);
        const data = await readResponse(response);
        if (!active) return;
        setStatus(data.status);
        if (data.status === "completed") {
          setResult(data.result);
          setError("");
        }
        if (data.status === "failed") setError(data.error || "Claim processing failed");
      } catch (err) {
        if (active) setError(err.message || "Could not retrieve claim status");
      } finally {
        polling = false;
      }
    }
    checkStatus();
    const interval = window.setInterval(checkStatus, 2000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [runId, status]);

  function resetForm() {
    setForm({ ...initialForm });
    setStep(0);
    setStepError("");
    setRunId("");
    setStatus("");
    setResult(null);
    setError("");
    setLoading(false);
  }

  return (
    <div className="site-shell" id="top">
      <header className="site-header">
        <div className="nav-inner">
          <a href="#top" className="brand" aria-label="Air Passenger Claim Triage home">
            <span className="brand-mark">✈</span>
            <span className="brand-name">Air Passenger<br />Claim Triage</span>
          </a>
          <span className="nav-divider" aria-hidden="true" />
          <span className="nav-caption">CLAIM ANALYSIS <span>·</span> ELIGIBILITY <span>·</span> NEXT STEPS</span>
          <nav className="nav-links" aria-label="Main navigation">
            <a href="#how-it-works">How it works</a>
            <a href="#claim">File a claim</a>
            <a className="nav-cta" href="#claim">Get started <Arrow /></a>
          </nav>
        </div>
      </header>

      <main>
        <section className="hero" aria-labelledby="hero-heading">
          <div className="hero-art" role="img" aria-label="Airplane wing flying above clouds at sunrise" />
          <div className="hero-inner">
            <div className="eyebrow"><span className="eyebrow-line" /> AIR PASSENGER CLAIM TRIAGE</div>
            <h1 id="hero-heading">Turn flight disruption into<br /><em>a clearer way forward.</em></h1>
            <p className="hero-description">A thoughtful, easier way to submit your flight disruption details, track their review, and understand your next steps.</p>
            <div className="hero-actions">
              <a className="primary-button" href="#claim">Check your claim <Arrow /></a>
              <a className="outline-button" href="#how-it-works"><span className="play-icon">▶</span> See how it works</a>
            </div>
            <div className="hero-notes">
              <span><b>✧</b> Clear, guided submission</span>
              <span><b>◇</b> Evidence-aware review</span>
              <span><b>↗</b> Next steps, explained</span>
            </div>
          </div>
        </section>

        <section className="workspace" id="claim" aria-label="Claim submission and assessment">
          <div className="form-card" ref={formRef}>
            <div className="card-topline"><span className="micro-label">01 / START YOUR CLAIM</span><span className="card-corner">✦</span></div>
            <div className="card-heading-row">
              <div>
                <h2>Check your flight claim</h2>
                <p>Tell us what happened. We'll guide you through the details.</p>
              </div>
            </div>
            <div className="stepper" aria-label="Claim submission progress">
              {steps.map((name, index) => (
                <div key={name} className={`step-item ${step === index ? "active" : ""} ${step > index ? "done" : ""}`} aria-current={step === index ? "step" : undefined}>
                  <span className="step-dot">{step > index ? "✓" : index + 1}</span>
                  <span>{name}</span>
                </div>
              ))}
            </div>

            <form onSubmit={handleSubmit} noValidate>
              <div className="step-body" key={step}>
                {step === 0 && (
                  <>
                    <div className="section-heading"><span>YOUR JOURNEY</span><span>Required fields are marked *</span></div>
                    <div className="form-grid">
                      <Field label="Passenger name *"><input name="passenger_name" autoComplete="name" value={form.passenger_name} onChange={handleChange} placeholder="Full name" required /></Field>
                      <Field label="Booking reference *"><input name="booking_reference" value={form.booking_reference} onChange={handleChange} maxLength={6} placeholder="ABC123" required /></Field>
                      <Field label="Airline *"><input name="airline" value={form.airline} onChange={handleChange} placeholder="e.g. IndiGo" required /></Field>
                      <Field label="Flight number *"><input name="flight_number" value={form.flight_number} onChange={handleChange} placeholder="e.g. 6E123" required /></Field>
                      <Field label="Departure airport *"><input name="origin" value={form.origin} onChange={handleChange} maxLength={3} placeholder="BLR" required /></Field>
                      <Field label="Arrival airport *"><input name="destination" value={form.destination} onChange={handleChange} maxLength={3} placeholder="DEL" required /></Field>
                      <Field wide label="Scheduled departure *"><input type="datetime-local" name="scheduled_departure" value={form.scheduled_departure} onChange={handleChange} required /></Field>
                    </div>
                  </>
                )}
                {step === 1 && (
                  <>
                    <div className="section-heading"><span>ABOUT THE DISRUPTION</span><span>Step 2 of 3</span></div>
                    <div className="field"><span className="field-label">What happened? *</span>
                      <div className="disruption-options">
                        {[["cancellation", "Cancellation"], ["delay", "Flight delay"], ["denied_boarding", "Denied boarding"], ["downgrading", "Downgrading"]].map(([value, label]) => (
                          <label key={value} className={`choice-tile ${form.reported_disruption === value ? "selected" : ""}`}><input type="radio" name="reported_disruption" value={value} checked={form.reported_disruption === value} onChange={handleChange} />{label}</label>
                        ))}
                      </div>
                    </div>
                    <div className="form-grid">
                      <Field label="Advance notice (minutes)" hint="Leave blank if unknown"><input type="number" min="0" max="525600" name="notice_minutes" value={form.notice_minutes} onChange={handleChange} placeholder="e.g. 120" /></Field>
                      <Field label="Flight block time (minutes)" hint="Leave blank if unknown"><input type="number" min="1" max="1440" name="block_time_minutes" value={form.block_time_minutes} onChange={handleChange} placeholder="e.g. 150" /></Field>
                      <Field wide label="Describe your experience *" hint="Include what the airline told you and how your journey was affected."><textarea name="description" rows={5} minLength={10} maxLength={2000} value={form.description} onChange={handleChange} placeholder="My flight was delayed and..." required /></Field>
                    </div>
                  </>
                )}
                {step === 2 && (
                  <>
                    <div className="section-heading"><span>FINAL DETAILS</span><span>Step 3 of 3</span></div>
                    <div className="form-grid">
                      <Field label="Alternate flight offered?"><select name="alternate_flight_offered" value={form.alternate_flight_offered} onChange={handleChange}><option value="">Not sure</option><option value="true">Yes</option><option value="false">No</option></select></Field>
                      <Field label="Alternate flight accepted?"><select name="alternate_flight_accepted" value={form.alternate_flight_accepted} onChange={handleChange}><option value="">Not sure</option><option value="true">Yes</option><option value="false">No</option></select></Field>
                      <Field label="Alternate flight departure"><input type="datetime-local" name="alternate_departure" value={form.alternate_departure} onChange={handleChange} /></Field>
                      <Field label="Contact details provided to airline?"><select name="contact_details_provided" value={form.contact_details_provided} onChange={handleChange}><option value="">Not sure</option><option value="true">Yes</option><option value="false">No</option></select></Field>
                    </div>
                    <div className="review-box">
                      <div className="review-top"><span>CLAIM SUMMARY</span><span>✈</span></div>
                      <div className="review-route"><strong>{form.origin.toUpperCase() || "—"}</strong><span className="route-line">✈</span><strong>{form.destination.toUpperCase() || "—"}</strong></div>
                      <div className="review-details"><span>{form.airline || "Airline"} · {form.flight_number.toUpperCase() || "Flight"}</span><span>{form.passenger_name || "Passenger"}</span></div>
                      <p>We'll submit these details to the claim triage service. A result will appear here when processing finishes.</p>
                    </div>
                  </>
                )}
              </div>

              {stepError && <p className="form-alert" role="alert">{stepError}</p>}
              <div className="form-footer">
                <div className="form-footnote"><span className="shield-mark">◇</span><span>Review your details before submitting.<br /><small>No eligibility decision is made by the form itself.</small></span></div>
                <div className="form-buttons">
                  {step > 0 && <button className="text-button" type="button" onClick={() => { setStep((current) => current - 1); setStepError(""); }}>Back</button>}
                  {step < 2 ? <button className="primary-button" type="button" onClick={nextStep}>Continue <Arrow /></button> : <button className="primary-button" type="submit" disabled={loading}>{loading ? "Submitting…" : "Assess my claim"} {!loading && <Arrow />}</button>}
                </div>
              </div>
              {(runId || error) && <button type="button" className="start-over" onClick={resetForm}>Start a new claim ↗</button>}
            </form>
          </div>

          <div className="right-column" ref={resultRef}>
            {(runId || error) ? (
              <ResultPanel key={runId || "error"} runId={runId} status={status} result={result} error={error} />
            ) : (
              <section className="assessment-card" aria-labelledby="assessment-heading">
                <div className="card-topline"><span className="micro-label">02 / YOUR ASSESSMENT</span><span className="outline-seal">✧</span></div>
                <h2 id="assessment-heading">A clearer view of<br />what comes next.</h2>
                <p className="assessment-lead">Once you submit your claim, its status and assessment will appear here.</p>
                <div className="empty-result">
                  <div className="empty-emblem"><span>✈</span></div>
                  <strong>Ready when you are</strong>
                  <p>Complete the form to begin your claim review.</p>
                </div>
                <div className="preview-list"><div><span>01</span> Submit your flight details <b>↗</b></div><div><span>02</span> Follow processing status <b>↗</b></div><div><span>03</span> Review the result and next steps <b>↗</b></div></div>
                <div className="result-disclaimer">Assessments depend on the information and evidence returned by the service.</div>
              </section>
            )}
            <section className="helper-card" id="how-it-works">
              <span className="micro-label">THE PROCESS</span>
              <h3>Simple by design.</h3>
              <div className="process-steps"><div><span>01</span><b>Tell your story</b><p>Share your flight and disruption details.</p></div><div><span>02</span><b>We organize the review</b><p>Your claim is submitted to the triage system.</p></div><div><span>03</span><b>See what's next</b><p>Review the returned outcome and any supporting evidence.</p></div></div>
            </section>
          </div>
        </section>

        <section className="values-strip" aria-label="Platform principles"><div><span>◇</span><div><strong>Clarity first</strong><p>A guided experience at every step</p></div></div><div><span>✧</span><div><strong>Evidence matters</strong><p>Supporting citations when available</p></div></div><div><span>↗</span><div><strong>Next steps</strong><p>Understand the outcome of your submission</p></div></div></section>
      </main>

      <footer className="site-footer"><span className="footer-brand">✈ &nbsp; Air Passenger Claim Triage</span><span>ML System Design &amp; AgentOps · Mini Project 04</span><a href="#top">Back to top ↑</a></footer>
    </div>
  );
}

export default App;
