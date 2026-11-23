const form = document.querySelector("#search-form");
const queryInput = document.querySelector("#query");
const limitSelect = document.querySelector("#limit");
const searchButton = document.querySelector("#search-button");
const resultsList = document.querySelector("#results-list");
const resultSummary = document.querySelector("#result-summary");
const searchMessage = document.querySelector("#search-message");
const apiStatus = document.querySelector("#api-status");
const apiStatusText = document.querySelector("#api-status-text");

function setMessage(message, type = "") {
  searchMessage.replaceChildren();
  searchMessage.className = `search-message${type ? ` is-${type}` : ""}`;
  searchMessage.textContent = message;
  searchMessage.hidden = false;
}

function clearMessage() {
  searchMessage.hidden = true;
  searchMessage.className = "search-message";
  searchMessage.replaceChildren();
}

function appendTextElement(parent, tagName, className, value) {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = value;
  parent.append(element);
  return element;
}

function renderResults(results) {
  const fragment = document.createDocumentFragment();

  for (const result of results) {
    const item = document.createElement("li");
    item.className = "result-card";

    appendTextElement(item, "span", "rank", String(result.rank));

    const content = document.createElement("div");
    content.className = "result-content";
    appendTextElement(content, "h3", "result-title", result.judul_perda);

    const metadata = document.createElement("div");
    metadata.className = "result-meta";
    appendTextElement(metadata, "span", "", `Nomor ${result.nomor_perda}`);
    appendTextElement(metadata, "span", "", `Tahun ${result.tahun_perda}`);
    content.append(metadata);

    if (result.document_url) {
      const documentLink = appendTextElement(
        content,
        "a",
        "document-link",
        "Buka dokumen PDF"
      );
      documentLink.href = result.document_url;
      documentLink.target = "_blank";
      documentLink.rel = "noopener noreferrer";
      documentLink.setAttribute("aria-label", `Buka PDF ${result.judul_perda} di tab baru`);
    } else {
      appendTextElement(content, "span", "document-unavailable", "PDF belum tersedia");
    }

    item.append(content);

    const percent = Math.max(0, Math.min(100, result.similarity * 100));
    const score = document.createElement("div");
    score.className = "score";
    const value = appendTextElement(score, "span", "score-value", `${percent.toFixed(1)}%`);
    appendTextElement(value, "span", "score-label", "cocok");
    const bar = document.createElement("span");
    bar.className = "score-bar";
    bar.setAttribute("aria-hidden", "true");
    const fill = document.createElement("span");
    fill.className = "score-fill";
    fill.style.width = `${percent}%`;
    bar.append(fill);
    score.append(bar);
    item.append(score);
    fragment.append(item);
  }

  resultsList.replaceChildren(fragment);
}

async function checkApi() {
  try {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const health = await response.json();
    apiStatus.classList.remove("is-offline");
    apiStatus.classList.add("is-online");
    apiStatusText.textContent = `API aktif, ${health.document_count} dokumen`;
  } catch {
    apiStatus.classList.remove("is-online");
    apiStatus.classList.add("is-offline");
    apiStatusText.textContent = "API tidak dapat dihubungi";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();

  if (!query) {
    queryInput.setCustomValidity("Masukkan kata kunci pencarian.");
    queryInput.reportValidity();
    queryInput.setCustomValidity("");
    queryInput.focus();
    return;
  }

  searchButton.disabled = true;
  searchButton.querySelector("span").textContent = "Mencari...";
  resultsList.replaceChildren();
  resultSummary.textContent = "Memproses kata kunci dan menghitung kemiripan.";
  setMessage("", "loading");
  const spinner = document.createElement("span");
  spinner.className = "spinner";
  spinner.setAttribute("aria-hidden", "true");
  searchMessage.append(spinner, document.createTextNode("Mencari dokumen yang relevan..."));

  try {
    const response = await fetch("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        limit: Number(limitSelect.value),
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      const details = Array.isArray(payload.detail)
        ? payload.detail.map((error) => error.msg).join(" ")
        : payload.detail;
      throw new Error(details || `Pencarian gagal (HTTP ${response.status}).`);
    }

    clearMessage();
    renderResults(payload.results);
    resultSummary.textContent = `${payload.total} dokumen ditampilkan untuk “${payload.query}”`;

    if (payload.total === 0) {
      setMessage("Belum ada dokumen yang cocok. Coba kata kunci lain atau gunakan istilah yang lebih umum.");
    }
  } catch (error) {
    resultsList.replaceChildren();
    resultSummary.textContent = "Pencarian belum berhasil.";
    setMessage(error instanceof Error ? error.message : "Terjadi kesalahan saat menghubungi API.", "error");
  } finally {
    searchButton.disabled = false;
    searchButton.querySelector("span").textContent = "Cari Perda";
  }
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.dataset.query;
    form.requestSubmit();
  });
});

checkApi();
