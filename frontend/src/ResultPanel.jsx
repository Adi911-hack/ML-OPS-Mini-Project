
import { useState } from "react";

const routeLabels = {
  "pay-as-computed": "Compensation Recommended",
  "request-further-evidence": "Further Evidence Required",
  decline: "Claim Declined",
  escalate: "Human Review Required",
  escalation: "Human Review Required"
};

const knownRoutes = Object.keys(routeLabels);

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
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Request failed (HTTP ${response.status})`
    );
  }

  return data;
}

function ResultPanel({ runId, status, result, error }) {
  const [satisfactory, setSatisfactory] = useState("");
  const [reason, setReason] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [sending, setSending] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState(false);

  const isStub = result?.stub === true;
  const isCompleted = status === "completed";
  const route = result?.route;
  const validRoute = knownRoutes.includes(route);
  const isEscalated =
    result?.escalated === true ||
    route === "escalate" ||
    route === "escalation";

  const citations = Array.isArray(result?.citations)
    ? result.citations
    : [];

  const recommendation =
    result?.recommendation || result?.message;

  async function submitFeedback(e) {
    e.preventDefault();

    if (sending || feedbackSent) return;

    setSending(true);
    setFeedbackStatus("");

    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          run_id: runId,
          satisfactory: satisfactory === "yes",
          reason: reason.trim()
        })
      });

      await readResponse(response);

      setFeedbackStatus("Feedback submitted successfully.");
      setFeedbackSent(true);
    } catch (err) {
      setFeedbackStatus(err.message || "Feedback submission failed");
    } finally {
      setSending(false);
    }
  }

  function showCitation(citation, index) {
    if (typeof citation === "string") {
      return (
        <div className="citation-item" key={index}>
          <p>{citation}</p>
        </div>
      );
    }

    if (!citation || typeof citation !== "object") {
      return null;
    }

    const clause =
      citation.clause_id ||
      citation.clause ||
      `Citation ${index + 1}`;

    const passage =
      citation.text ||
      citation.passage ||
      citation.excerpt ||
      "Citation text unavailable";

    return (
      <div className="citation-item" key={index}>
        <strong>{clause}</strong>
        <p>{passage}</p>
        {citation.source && (
          <small>Source: {citation.source}</small>
        )}
      </div>
    );
  }

  return (
    <section className="result-section">
      <h2>Claim Assessment</h2>

      {runId && (
        <p className="run-id">
          <strong>Run ID:</strong> {runId}
        </p>
      )}

      {status && (
        <div className={`status-badge status-${status}`}>
          {status.toUpperCase()}
        </div>
      )}

      {(status === "queued" || status === "running") && (
        <p>Your claim is being processed. Please keep this page open.</p>
      )}

      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}

      {isCompleted && isStub && (
        <div className="notice-box">
          <h3>Awaiting AI Integration</h3>
          <p>
            The backend successfully completed the request using
            a test worker. No compensation decision has been made.
          </p>
          {result?.message && <p>{result.message}</p>}
        </div>
      )}

      {isCompleted && !isStub && (
        <div className="decision-panel">
          <h3>Entitlement Recommendation</h3>

          <div className="recommendation-value">
            {validRoute
              ? routeLabels[route]
              : "Recommendation Unavailable"}
          </div>

          {validRoute && recommendation && (
            <p className="recommendation-text">
              {recommendation}
            </p>
          )}

          {validRoute && result?.compensation_amount != null && (
            <p>
              <strong>Computed Amount:</strong>{" "}
              {String(result.compensation_amount)}
            </p>
          )}

          {isEscalated && (
            <div className="notice-box">
              <strong>Human Review Required</strong>
              <p>
                This case requires review by an authorised
                customer relations officer.
              </p>
            </div>
          )}

          {citations.length > 0 && (
            <div className="citation-section">
              <h3>Supporting Citations</h3>
              {citations.map(showCitation)}
            </div>
          )}

          {!validRoute && (
            <div className="notice-box">
              The backend returned no recognised entitlement
              route. No compensation recommendation is displayed.
            </div>
          )}

          {validRoute && citations.length === 0 && (
            <div className="notice-box">
              No supporting citations were provided.
              The recommendation has not been verified
              by this interface.
            </div>
          )}
        </div>
      )}

      {isCompleted && (
        <div className="feedback-panel">
          <h3>Passenger Feedback</h3>
          <p>Was this assessment helpful?</p>

          <form onSubmit={submitFeedback}>
            <div className="feedback-options">
              <label>
                <input
                  type="radio"
                  name={`feedback-${runId}`}
                  value="yes"
                  checked={satisfactory === "yes"}
                  onChange={(e) => setSatisfactory(e.target.value)}
                  disabled={feedbackSent}
                  required
                />
                Yes
              </label>

              <label>
                <input
                  type="radio"
                  name={`feedback-${runId}`}
                  value="no"
                  checked={satisfactory === "no"}
                  onChange={(e) => setSatisfactory(e.target.value)}
                  disabled={feedbackSent}
                />
                No
              </label>
            </div>

            <label>
              Reason for your feedback
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                minLength="3"
                maxLength="1000"
                rows="3"
                disabled={feedbackSent}
                required
              />
            </label>

            <button
              type="submit"
              disabled={
                sending ||
                feedbackSent ||
                !satisfactory ||
                reason.trim().length < 3
              }
            >
              {sending
                ? "Submitting..."
                : feedbackSent
                  ? "Feedback Submitted"
                  : "Submit Feedback"}
            </button>
          </form>

          {feedbackStatus && (
            <p role="status" className="feedback-message">
              {feedbackStatus}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

export default ResultPanel;
