
import { useEffect, useState } from "react";
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

function App() {
  const [form, setForm] = useState(initialForm);
  const [runId, setRunId] = useState("");
  const [status, setStatus] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  }

  function prepareClaim() {
    const claim = { ...form };

    ["booking_reference", "flight_number", "origin", "destination"].forEach((field) => {
      claim[field] = claim[field].trim().toUpperCase();
    });

    claim.scheduled_departure = new Date(form.scheduled_departure).toISOString();

    if (form.alternate_departure) {
      claim.alternate_departure = new Date(form.alternate_departure).toISOString();
    } else {
      claim.alternate_departure = null;
    }

    ["notice_minutes", "block_time_minutes"].forEach((field) => {
      claim[field] = form[field] === "" ? null : Number(form[field]);
    });

    [
      "alternate_flight_offered",
      "alternate_flight_accepted",
      "contact_details_provided"
    ].forEach((field) => {
      claim[field] = form[field] === "" ? null : form[field] === "true";
    });

    return claim;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    setRunId("");
    setStatus("");

    try {
      const claim = prepareClaim();

      const response = await fetch("/api/claims", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(claim)
      });

      const data = await response.json();

      if (!response.ok) {
        if (data.errors) {
          throw new Error(
            data.errors.map((item) => {
              const field = Array.isArray(item.loc) ? item.loc.join(".") : "Claim";
              return `${field}: ${item.msg}`;
            }).join(" | ")
          );
        }

        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Claim submission failed"
        );
      }

      setRunId(data.run_id);
      setStatus(data.status);
    } catch (err) {
      setError(err.message || "Could not connect to the backend");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!runId || status === "completed" || status === "failed") {
      return;
    }

    let active = true;

    async function checkStatus() {
      try {
        const response = await fetch(`/api/runs/${encodeURIComponent(runId)}`);

        if (!response.ok) {
          throw new Error("Could not retrieve claim status");
        }

        const data = await response.json();

        if (!active) return;

        setStatus(data.status);

        if (data.status === "completed") {
          setResult(data.result);
        }

        if (data.status === "failed") {
          setError(data.error || "Claim processing failed");
        }
      } catch (err) {
        if (active) {
          setError(err.message);
        }
      }
    }

    checkStatus();

    const interval = setInterval(checkStatus, 2000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [runId, status]);

  function resetForm() {
    setForm(initialForm);
    setRunId("");
    setStatus("");
    setResult(null);
    setError("");
  }

  return (
    <div className="app">
      <header>
        <h1>Air Passenger Claim Triage</h1>
        <p>AI-assisted airline compensation claim assessment</p>
      </header>

      <main>
        <div className="intro">
          <h2>Submit a Passenger Claim</h2>
          <p>Enter your flight information and disruption details.</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid">
            <label>
              Passenger Name
              <input
                name="passenger_name"
                value={form.passenger_name}
                onChange={handleChange}
                required
              />
            </label>

            <label>
              Booking Reference
              <input
                name="booking_reference"
                value={form.booking_reference}
                onChange={handleChange}
                maxLength="6"
                placeholder="ABC123"
                required
              />
            </label>

            <label>
              Airline
              <input
                name="airline"
                value={form.airline}
                onChange={handleChange}
                placeholder="IndiGo"
                required
              />
            </label>

            <label>
              Flight Number
              <input
                name="flight_number"
                value={form.flight_number}
                onChange={handleChange}
                placeholder="6E123"
                required
              />
            </label>

            <label>
              Origin Airport
              <input
                name="origin"
                value={form.origin}
                onChange={handleChange}
                maxLength="3"
                placeholder="BLR"
                required
              />
            </label>

            <label>
              Destination Airport
              <input
                name="destination"
                value={form.destination}
                onChange={handleChange}
                maxLength="3"
                placeholder="DEL"
                required
              />
            </label>

            <label>
              Scheduled Departure
              <input
                type="datetime-local"
                name="scheduled_departure"
                value={form.scheduled_departure}
                onChange={handleChange}
                required
              />
            </label>

            <label>
              Disruption Type
              <select
                name="reported_disruption"
                value={form.reported_disruption}
                onChange={handleChange}
              >
                <option value="cancellation">Cancellation</option>
                <option value="delay">Delay</option>
                <option value="denied_boarding">Denied Boarding</option>
                <option value="downgrading">Downgrading</option>
              </select>
            </label>

            <label>
              Notice Given (Minutes)
              <input
                type="number"
                min="0"
                max="525600"
                name="notice_minutes"
                value={form.notice_minutes}
                onChange={handleChange}
              />
            </label>

            <label>
              Flight Block Time (Minutes)
              <input
                type="number"
                min="1"
                max="1440"
                name="block_time_minutes"
                value={form.block_time_minutes}
                onChange={handleChange}
              />
            </label>

            <label>
              Alternate Flight Offered?
              <select
                name="alternate_flight_offered"
                value={form.alternate_flight_offered}
                onChange={handleChange}
              >
                <option value="">Unknown</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>

            <label>
              Alternate Flight Accepted?
              <select
                name="alternate_flight_accepted"
                value={form.alternate_flight_accepted}
                onChange={handleChange}
              >
                <option value="">Unknown</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>

            <label>
              Alternate Flight Departure
              <input
                type="datetime-local"
                name="alternate_departure"
                value={form.alternate_departure}
                onChange={handleChange}
              />
            </label>

            <label>
              Contact Details Provided?
              <select
                name="contact_details_provided"
                value={form.contact_details_provided}
                onChange={handleChange}
              >
                <option value="">Unknown</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>
          </div>

          <label className="description">
            Describe Your Claim
            <textarea
              name="description"
              rows="5"
              value={form.description}
              onChange={handleChange}
              placeholder="Explain what happened to your flight..."
              minLength="10"
              required
            />
          </label>

          <button type="submit" disabled={loading}>
            {loading ? "Submitting..." : "Submit Claim"}
          </button>

          <button type="button" onClick={resetForm} style={{ marginLeft: 10 }}>
            Clear Form
          </button>
        </form>

        {(runId || error) && (
          <section className="result-section">
            <h2>Claim Processing Status</h2>

            {runId && <p><strong>Run ID:</strong> {runId}</p>}

            {status && (
              <p>
                <strong>Status:</strong> {status.toUpperCase()}
              </p>
            )}

            {(status === "queued" || status === "running") && (
              <p>Your claim is being processed...</p>
            )}

            {error && <p className="error-message">{error}</p>}

            {status === "completed" && (
              <div>
                <h3>Backend Response</h3>
                <pre>{JSON.stringify(result, null, 2)}</pre>
                <p>
                  The current backend may still use a stub agent.
                  A completed run does not necessarily mean that
                  compensation has been approved.
                </p>
              </div>
            )}
          </section>
        )}
      </main>

      <footer>ML System Design & AgentOps — Mini Project 04</footer>
    </div>
  );
}

export default App;
