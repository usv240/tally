/* Tally product screens. Vanilla JS against the API in tally/api.py. */

(function () {
  "use strict";

  var state = null, traceEvents = [], traceCursor = 0, busy = false;

  function api(path, opts) {
    return fetch(path, opts).then(function (r) {
      if (!r.ok) throw new Error(path + " returned " + r.status);
      return r.json();
    });
  }

  function setBusy(on, label) {
    busy = on;
    document.querySelectorAll("#steps .btn").forEach(function (b) { b.disabled = on; });
    var reset = document.getElementById("reset");
    if (reset) reset.disabled = on;
    if (on && label) {
      var s = document.getElementById("status");
      s.className = "status-line";
      s.textContent = label;
    }
  }

  function photoUrl(key) {
    if (!key) return null;
    var parts = String(key).replace(/\\/g, "/").split("/");
    return "/plates/" + parts[parts.length - 1];
  }

  /* Rendering ------------------------------------------------------------ */

  function renderStatus() {
    var s = document.getElementById("status");
    s.className = "status-line " + state.tone;
    s.textContent = state.headline;
    document.getElementById("clock").textContent = window.fmtDayTime(state.now);

    var budget = state.provider.question_budget, used = state.asked_today;
    document.getElementById("quiet-text").textContent =
      "Asked you " + used + (used === 1 ? " question" : " questions") + " today. Budget " + budget + ".";
    var pips = document.getElementById("quiet-pips");
    pips.innerHTML = "";
    for (var i = 0; i < budget; i++) {
      pips.appendChild(window.h("span", { class: "pip" + (i < used ? " used" : "") }));
    }
    var r = state.ratio || {};
    document.getElementById("ratio-text").textContent = r.explanation
      ? (r.now_ok === false ? "Over your limit: " : "") + r.explanation
      : "Ratio unknown";
  }

  function renderSteps() {
    var host = document.getElementById("steps");
    host.innerHTML = "";
    var next = state.steps.filter(function (s) { return !s.done; })[0];
    state.steps.forEach(function (s) {
      // A day happens in order. Playing the evening before lunch would ask the agents to close a
      // day that has not happened, so a step that is not next is disabled and says why.
      var isNext = next && next.id === s.id;
      var b = window.h("button", {
        class: "btn" + (isNext ? " primary" : ""),
        type: "button",
        title: s.done ? "Already played" : (isNext ? s.detail : "Play the steps before this first"),
        onclick: function () { runStep(s.id, s.detail); }
      }, [s.done ? "Done: " + s.title : s.title]);
      if (s.done || busy || !isNext) b.disabled = true;
      host.appendChild(b);
    });
    if (next && !playing) {
      host.appendChild(window.h("button", {
        class: "btn", type: "button", id: "play-all",
        title: "Run every remaining step, one after another",
        disabled: busy ? "" : null,
        onclick: playThrough
      }, ["Play the rest of the day"]));
    }

    var doneCount = state.steps.filter(function (s) { return s.done; }).length;
    var shared = document.getElementById("shared-note");
    if (shared) {
      if (doneCount > 0 && doneCount < state.steps.length) {
        shared.hidden = false;
        shared.innerHTML = "";
        shared.appendChild(window.h("span", { text:
          "Someone has already played " + doneCount + " of these steps. This demo is one shared "
          + "scenario, so everyone sees the same week. " }));
        shared.appendChild(window.h("button", { class: "btn small", type: "button",
          onclick: reset }, ["Start it again from the beginning"]));
      } else {
        shared.hidden = true;
      }
    }

    document.getElementById("step-detail").textContent = next
      ? next.detail : "The day is played out. Press Reset to run it again.";
  }

  function chip(item) {
    var low = item.confidence < 0.75;
    return window.h("span", { class: "chip" + (low ? " low" : "") }, [
      window.h("span", { text: item.name }),
      window.h("span", { class: "comp", text: item.component.replace("_", " ") }),
      window.h("span", { class: "conf", text: Math.round(item.confidence * 100) + "%" })
    ]);
  }

  function renderMeals() {
    var host = document.getElementById("meals");
    host.innerHTML = "";
    if (!state.meals.length) {
      host.appendChild(window.h("div", { class: "card" }, [
        window.h("h3", { text: "Nothing logged yet" }),
        window.h("p", { class: "muted", style: "margin:0",
          text: "Press the first step above. Rosa says who is here, and then photographs the plate." })
      ]));
      return;
    }
    state.meals.forEach(function (m) {
      var body = window.h("div", {}, [
        window.h("div", { class: "gap-head" }, [
          window.h("span", { class: "gap-window",
            text: m.type.charAt(0).toUpperCase() + m.type.slice(1) + ", " + window.fmtTime(m.at) }),
          window.levelBadge(m.reimbursable ? "covered" : "high",
            m.reimbursable ? "will be paid" : "not reimbursable")
        ]),
        window.h("div", { class: "chips" }, m.items.map(chip))
      ]);
      if (!m.reimbursable && m.smallest_fix) {
        body.appendChild(window.h("p", { style: "margin:0 0 var(--s3);font-weight:550" },
          [m.smallest_fix, window.infoBtn("smallest_fix", "the smallest fix")]));
      }
      body.appendChild(window.h("p", { class: "small muted", style: "margin:0 0 var(--s2)" },
        [m.explanation, window.infoBtn("meal_pattern", "the meal pattern")]));
      if (m.replaces) {
        body.appendChild(window.h("p", { class: "small muted", style: "margin:0 0 var(--s2)" },
          ["This photograph replaced an earlier one, so the meal is counted once.",
           window.infoBtn("superseded", "superseded meals")]));
      }
      (m.flags || []).forEach(function (f) {
        body.appendChild(window.h("p", { class: "small muted", style: "margin:0", text: f }));
      });
      (m.label_checks || []).forEach(function (c) {
        body.appendChild(window.h("p", { class: "small", style: "margin:var(--s2) 0 0" }, [
          window.levelBadge("elevated", "check the label"), " ",
          c === "yogurt_sugar" ? "Yoghurt must be under 23g of sugar per 6oz. A photograph cannot show that."
            : "Cereal must be under 6g of sugar per dry ounce. A photograph cannot show that.",
          window.infoBtn("label_check", "label checks")
        ]));
      });
      body.appendChild(window.h("p", { class: "small muted", style: "margin:var(--s3) 0 0" },
        ["Logged for " + m.children_served.length + " children. Rule version " + m.rule_version + ".",
         window.infoBtn("rule_version", "the rule version")]));

      var img = photoUrl(m.photo);
      var inner = img
        ? window.h("div", { class: "meal" }, [
            window.h("img", { src: img, alt: "The " + m.type + " plate", loading: "lazy" }), body])
        : body;
      host.appendChild(window.h("div", {
        class: "card meal-card " + (m.reimbursable ? "paid" : "unpaid") }, [inner]));
    });
    window.MountInfo();
  }

  function renderSaid() {
    var host = document.getElementById("said");
    host.innerHTML = "";
    if (!state.spoken.length) {
      host.appendChild(window.h("p", { class: "muted small", text: "Nothing said yet." }));
      return;
    }
    state.spoken.forEach(function (s) {
      host.appendChild(window.h("div", { class: "said-line " + (s.tone || "info") }, [
        window.h("span", { class: "t", text: window.fmtTime(s.at) }),
        window.h("span", { text: s.text })
      ]));
    });
  }

  function renderChildren() {
    var host = document.getElementById("children");
    host.innerHTML = "";
    state.children.forEach(function (c) {
      var tags = window.h("div", { class: "child-tags" }, [
        c.present ? window.levelBadge("covered", "here")
          : c.absent ? window.levelBadge("low", "absent") : window.levelBadge("neutral", "not in yet"),
        window.h("span", { class: "badge neutral", text: "age " + c.age_group })
      ]);
      if (c.subsidized) tags.appendChild(window.h("span", { class: "badge neutral", text: "subsidised" }));
      if (c.language === "es") tags.appendChild(window.h("span", { class: "badge neutral", text: "notes in Spanish" }));
      c.allergies.forEach(function (a) {
        tags.appendChild(window.h("span", { class: "badge critical" }, [
          window.h("span", { class: "shape", "aria-hidden": "true", text: window.SHAPES.critical }),
          window.h("span", { text: a + " allergy" })
        ]));
      });
      host.appendChild(window.h("div", { class: "card child-card" }, [
        window.h("span", { class: "name", text: c.name }), tags
      ]));
    });
  }

  function questionCard(q) {
    var card = window.h("div", { class: "question " + q.priority }, [
      window.h("div", { class: "q", text: q.text })
    ]);
    var opts = q.options && q.options.length ? q.options : ["Yes", "No", "Not sure"];
    var row = window.h("div", { class: "btn-row" });
    opts.forEach(function (o) {
      row.appendChild(window.h("button", { class: "btn small", type: "button",
        onclick: function () { answer(q.id, o); } }, [o]));
    });
    card.appendChild(row);
    card.appendChild(window.h("p", { class: "small muted", style: "margin:var(--s3) 0 0" }, [
      q.priority === "safety" ? "A safety question. It goes through immediately and never spends the budget."
        : q.priority === "meal" ? "Asked at the table, because the answer is only useful while the food is there."
        : "Held for the evening, so it does not interrupt her day.",
      window.infoBtn("question_budget", "the question budget")
    ]));
    return card;
  }

  function renderEvening() {
    var host = document.getElementById("evening");
    host.innerHTML = "";

    var open = state.questions.filter(function (q) { return !q.answered; });
    var qcard = window.h("div", { class: "card stack" }, [
      window.h("h3", {}, ["Questions", window.infoBtn("agent_gate", "the Provider Gate")])]);
    if (!open.length) {
      qcard.appendChild(window.h("p", { class: "muted", style: "margin:0",
        text: "Nothing needs her. That is the goal." }));
    } else {
      open.forEach(function (q) { qcard.appendChild(questionCard(q)); });
    }
    host.appendChild(qcard);

    var ncard = window.h("div", { class: "card stack" }, [
      window.h("h3", {}, ["Notes home", window.infoBtn("agent_notes", "Parent Notes")])]);
    if (!state.notes.length) {
      ncard.appendChild(window.h("p", { class: "muted", style: "margin:0",
        text: "Drafted in the evening, from what was actually logged." }));
    } else {
      state.notes.forEach(function (n) {
        ncard.appendChild(window.h("div", { class: "note-card" }, [
          window.h("strong", { text: n.name + (n.language === "es" ? " (Spanish)" : "") }),
          window.h("p", { class: "small", style: "margin:4px 0 0", text: n.text })
        ]));
      });
      ncard.appendChild(window.h("p", { class: "small muted", style: "margin:0",
        text: "Assembled from the record. Nothing here was invented." }));
    }
    host.appendChild(ncard);

    var ccard = window.h("div", { class: "card stack" }, [window.h("h3", { text: "Compliance" })]);
    state.compliance.forEach(function (c) {
      ccard.appendChild(window.h("p", { class: "small", style: "margin:0" }, [
        window.levelBadge(c.status === "overdue" ? "critical" : c.status === "due" ? "high" : "low",
          c.status),
        " " + c.label + ", due " + c.due
      ]));
    });
    host.appendChild(ccard);
    window.MountInfo();
  }

  function renderMonth() {
    var host = document.getElementById("month");
    host.innerHTML = "";
    var m = state.month || {};
    var card = window.h("div", { class: "card stack" }, [
      window.h("h3", {}, ["Claim for " + (m.month || ""),
        window.infoBtn("daily_maximum", "the daily maximum")]),
      window.h("span", { class: "money", text: "$" + (m.total || 0).toFixed(2) }),
      window.h("p", { class: "small muted", style: "margin:0" }, [
        (m.computed_in === "agentcore_code_interpreter"
          ? "Computed inside Amazon Bedrock AgentCore Code Interpreter, from the rates in force, "
            + "after the daily maximum is applied per child."
          : m.computed_in === "local_fallback"
            ? "Computed locally, because AgentCore did not answer"
              + (m.computed_reason ? " (" + m.computed_reason + ")" : "")
              + ". Same kernel either way."
            : "Computed as code from the rates in force, after the daily maximum is applied per child."),
        window.infoBtn("where_it_runs", "where it ran")])
    ]);
    var table = window.h("table", { class: "claim" }, [
      window.h("thead", {}, [window.h("tr", {}, [
        window.h("th", { text: "Meal" }), window.h("th", { class: "num", text: "Count" }),
        window.h("th", { class: "num", text: "Rate" }), window.h("th", { class: "num", text: "Amount" })])])
    ]);
    var tbody = window.h("tbody", {});
    (m.lines || []).forEach(function (l) {
      tbody.appendChild(window.h("tr", {}, [
        window.h("td", { text: l.meal_type }),
        window.h("td", { class: "num", text: String(l.count) }),
        window.h("td", { class: "num", text: "$" + l.rate.toFixed(2) }),
        window.h("td", { class: "num", text: "$" + l.amount.toFixed(2) })
      ]));
    });
    table.appendChild(tbody);
    card.appendChild(table);
    card.appendChild(window.h("div", { class: "btn-row" }, [
      window.h("a", { class: "btn", href: "sponsor.html" }, ["Review it as the sponsor would"])]));
    card.appendChild(window.h("p", { class: "small muted", style: "margin:0",
      text: "The sponsor sees every meal with the photograph it was judged from and the rulebook "
        + "version that judged it, which is what makes this claim defensible a year later." }));
    host.appendChild(card);

    if (m.not_reimbursable) {
      host.appendChild(window.h("div", { class: "card stack" }, [
        window.h("h3", {}, ["What the unpaid meals cost",
          window.infoBtn("lost_amount", "the lost amount")]),
        window.h("span", { class: "money lost", text: "$" + (m.lost_amount || 0).toFixed(2) }),
        window.h("p", { class: "small muted", style: "margin:0",
          text: m.not_reimbursable + " meal" + (m.not_reimbursable === 1 ? "" : "s")
                + " did not have every required component. This is what they would have paid." })
      ]));
    }

    host.appendChild(window.h("div", { class: "card" }, [
      window.h("h3", { text: "Send to the sponsor" }),
      window.h("p", { class: "muted small" },
        ["Nothing is sent until she reviews the month and presses send. The export includes every "
         + "photograph and the rule version each verdict was decided under."]),
      window.h("button", { class: "btn primary", type: "button", disabled: "",
        title: "Disabled in the demo, because nothing should be sent to a real sponsor" },
        ["Send to " + (state.provider.sponsor || "the sponsor")])
    ]));
    window.MountInfo();
  }

  var WORDS = {
    plate_read: "Plate read", meal_logged: "Meal logged", allergy_alert: "Allergy alert",
    question: "Question raised", question_answered: "Question answered", roll_taken: "Roll taken",
    substitution: "Substitution recorded", spoken: "Said out loud", day_closed: "Day closed",
    claim_built: "Claim built", notes_drafted: "Notes drafted",
    compliance_checked: "Compliance checked", subsidy_reconciled: "Subsidy reconciled",
    digest_built: "Digest built", evening_start: "Evening run started", evening_end: "Evening run finished"
  };

  function renderTrace() {
    var host = document.getElementById("trace");
    host.innerHTML = "";
    if (!traceEvents.length) {
      host.appendChild(window.h("p", { class: "muted small", text: "No events yet. Play a step." }));
      return;
    }
    traceEvents.forEach(function (e) {
      var rest = {};
      Object.keys(e).forEach(function (k) { if (k !== "kind" && k !== "at") rest[k] = e[k]; });
      host.appendChild(window.h("div", { class: "trace-row" }, [
        window.h("span", { class: "t", text: window.fmtTime(e.at) }),
        window.h("span", { class: "k", text: WORDS[e.kind] || e.kind }),
        window.h("span", { class: "d", text: JSON.stringify(rest) })
      ]));
    });
  }

  function renderAll() {
    renderStatus();
    renderSteps();
    renderMeals();
    renderSaid();
    var active = document.querySelector('[role="tab"][aria-selected="true"]').id;
    if (active === "tab-children") renderChildren();
    if (active === "tab-evening") renderEvening();
    if (active === "tab-month") renderMonth();
    if (active === "tab-trace") renderTrace();
  }


  /* Connection state -----------------------------------------------------
     Three things a person needs when something breaks: what happened, what the system did about
     it, and the one action available. */
  var connEl = null;
  function connection(message, kind, actionLabel, action) {
    if (connEl) { connEl.remove(); connEl = null; }
    if (!message) return;
    connEl = window.h("div", { class: "conn" + (kind === "gone" ? " gone" : ""),
      role: "status", "aria-live": "polite" }, [window.h("span", { text: message })]);
    if (actionLabel) {
      connEl.appendChild(window.h("button", { class: "btn small", type: "button",
        onclick: function () { connection(null); action(); } }, [actionLabel]));
    }
    document.body.appendChild(connEl);
  }
  window.addEventListener("offline", function () {
    connection("You are offline. Nothing is lost; the demo picks up where it left off.", "gone");
  });
  window.addEventListener("online", function () {
    connection("Back online.", "");
    setTimeout(function () { connection(null); }, 2500);
  });

  /* Actions --------------------------------------------------------------- */

  function pullTrace() {
    return api("/api/trace?since=" + traceCursor).then(function (t) {
      traceEvents = traceEvents.concat(t.events);
      traceCursor = t.next;
    });
  }

  function after(s) {
    state = s;
    return pullTrace().then(function () { setBusy(false); renderAll(); });
  }

  function fail(e) {
    setBusy(false);
    var offline = !navigator.onLine;
    var el = document.getElementById("status");
    el.className = "status-line alert";
    el.textContent = offline
      ? "You are offline, so that step did not run. Nothing was lost."
      : "That step did not finish: " + e.message + ". Nothing was saved.";
    connection(offline ? "You are offline." : "The service did not answer.",
      "gone", "Try again", function () { location.reload(); });
  }

  /* Playing it through -----------------------------------------------------
     Each step is a real agent run, so there is a pause between them. Someone watching, or
     recording, should not have to sit with a finger over the button for that pause. */
  var playing = false;

  function playThrough() {
    if (busy || playing) return;
    playing = true;
    (function nextOne() {
      var left = state.steps.filter(function (s) { return !s.done; });
      if (!left.length) { playing = false; renderAll(); return; }
      var s = left[0];
      setBusy(true, "Running: " + s.detail);
      api("/api/step", { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ step: s.id }) })
        .then(after)
        .then(function () { setTimeout(nextOne, 900); })
        .catch(function (e) { playing = false; fail(e); });
    })();
  }

  function runStep(id, detail) {
    if (busy) return;
    setBusy(true, "Running: " + detail);
    api("/api/step", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ step: id }) }).then(after).catch(fail);
  }

  function answer(qid, text) {
    if (busy) return;
    setBusy(true, "Recording your answer");
    api("/api/answer", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ question_id: qid, answer: text }) }).then(after).catch(fail);
  }

  function reset() {
    setBusy(true, "Resetting to Tuesday 07:38");
    api("/api/reset", { method: "POST" }).then(function (s) {
      traceEvents = []; traceCursor = 0;
      return after(s);
    }).catch(fail);
  }

  function selectTab(id) {
    document.querySelectorAll('[role="tab"]').forEach(function (t) {
      var on = t.id === id;
      t.setAttribute("aria-selected", String(on));
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
    if (id === "tab-children") renderChildren();
    if (id === "tab-evening") renderEvening();
    if (id === "tab-month") renderMonth();
    if (id === "tab-trace") renderTrace();
    if (history.replaceState) history.replaceState(null, "", "#" + id.replace("tab-", ""));
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('[role="tab"]').forEach(function (t) {
      t.addEventListener("click", function () { selectTab(t.id); });
    });
    document.getElementById("reset").addEventListener("click", reset);
    api("/api/state").then(function (s) { state = s; return pullTrace(); }).then(function () {
      renderAll();
      var hash = (location.hash || "").replace("#", "");
      if (hash && document.getElementById("tab-" + hash)) selectTab("tab-" + hash);
    }).catch(fail);
  });
})();
