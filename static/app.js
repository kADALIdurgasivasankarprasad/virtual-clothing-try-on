// ===== STATE =====
const state = {
    personFile: null,
    clothFile: null,
    clothType: "upper",
    connected: false,
    processing: false,
};

// ===== DOM REFS =====
const $ = (sel) => document.querySelector(sel);

const colabUrlInput = $("#colab-url-input");
const connectBtn = $("#connect-btn");
const connectionStatus = $("#connection-status");
const statusText = $(".status-text");

const personDropZone = $("#person-drop-zone");
const clothDropZone = $("#cloth-drop-zone");
const personInput = $("#person-input");
const clothInput = $("#cloth-input");
const personPreview = $("#person-preview");
const clothPreview = $("#cloth-preview");
const personPrompt = $("#person-prompt");
const clothPrompt = $("#cloth-prompt");
const personClear = $("#person-clear");
const clothClear = $("#cloth-clear");

const typeButtons = document.querySelectorAll(".type-btn");
const stepItems = document.querySelectorAll(".step-item");

const tryOnBtn = $("#try-on-btn");
const btnText = $(".btn-text");
const spinner = $("#spinner");
const statusMessage = $("#status-message");

const resultPlaceholder = $("#result-placeholder");
const resultDisplay = $("#result-display");
const resultPerson = $("#result-person");
const resultImage = $("#result-image");
const elapsedTime = $("#elapsed-time");
const downloadBtn = $("#download-btn");

// ===== STEP TRACKER =====

function updateSteps() {
    stepItems.forEach((item) => item.classList.remove("active"));

    if (!state.personFile && !state.clothFile) {
        stepItems[0].classList.add("active");
    } else if (state.personFile && !state.clothFile) {
        stepItems[0].classList.add("active");
        stepItems[1].classList.add("active");
    } else if (state.personFile && state.clothFile) {
        stepItems[0].classList.add("active");
        stepItems[1].classList.add("active");
        stepItems[2].classList.add("active");
    }
}

// ===== CONNECTION =====

async function loadColabUrl() {
    try {
        const resp = await fetch("/api/get-colab-url");
        const data = await resp.json();
        if (data.colab_url) {
            colabUrlInput.value = data.colab_url;
            checkHealth();
        }
    } catch (e) {
        // Server not ready yet
    }
}

function extractUrl(text) {
    const match = text.match(/(https?:\/\/[^\s"']+)/);
    return match ? match[1] : text.trim();
}

connectBtn.addEventListener("click", async () => {
    const url = extractUrl(colabUrlInput.value);
    if (!url) return;
    colabUrlInput.value = url;
    try {
        await fetch("/api/set-colab-url", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });
        checkHealth();
    } catch (e) {
        setConnectionStatus("disconnected", "Local server unreachable");
    }
});

colabUrlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") connectBtn.click();
});

async function checkHealth() {
    if (state.processing) return;
    setConnectionStatus("checking", "Checking...");
    try {
        const resp = await fetch("/api/health");
        const data = await resp.json();
        if (data.status === "ok") {
            setConnectionStatus("connected", `Connected — ${data.gpu}`);
            state.connected = true;
        } else {
            setConnectionStatus("disconnected", data.detail || "Not connected");
            state.connected = false;
        }
    } catch (e) {
        setConnectionStatus("disconnected", "Server unreachable");
        state.connected = false;
    }
    updateTryOnButton();
}

function setConnectionStatus(cls, text) {
    connectionStatus.className = `status-pill ${cls}`;
    statusText.textContent = text;
}

// Poll health every 30 seconds
setInterval(() => {
    if (colabUrlInput.value.trim()) checkHealth();
}, 30000);

// ===== DRAG & DROP =====

function setupDropZone(dropZone, fileInput, previewImg, promptEl, clearBtn, fileKey) {
    dropZone.addEventListener("click", (e) => {
        if (e.target === clearBtn || clearBtn.contains(e.target)) return;
        fileInput.click();
    });

    dropZone.addEventListener("dragenter", (e) => {
        e.preventDefault();
        dropZone.classList.add("drag-over");
    });
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("drag-over");
    });
    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("drag-over");
    });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith("image/")) {
            handleFile(file, previewImg, promptEl, clearBtn, fileKey);
        }
    });

    fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        if (file) handleFile(file, previewImg, promptEl, clearBtn, fileKey);
    });

    clearBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        state[fileKey] = null;
        previewImg.src = "";
        previewImg.classList.add("hidden");
        promptEl.classList.remove("hidden");
        clearBtn.classList.add("hidden");
        fileInput.value = "";
        updateTryOnButton();
        updateSteps();
    });
}

function handleFile(file, previewImg, promptEl, clearBtn, fileKey) {
    state[fileKey] = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        previewImg.classList.remove("hidden");
        promptEl.classList.add("hidden");
        clearBtn.classList.remove("hidden");
    };
    reader.readAsDataURL(file);
    updateTryOnButton();
    updateSteps();
}

setupDropZone(personDropZone, personInput, personPreview, personPrompt, personClear, "personFile");
setupDropZone(clothDropZone, clothInput, clothPreview, clothPrompt, clothClear, "clothFile");

// ===== CLOTH TYPE =====

typeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
        typeButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.clothType = btn.dataset.type;
    });
});

// ===== BUTTON STATE =====

function updateTryOnButton() {
    tryOnBtn.disabled = !(state.personFile && state.clothFile && state.connected);
}

// ===== TRY ON =====

tryOnBtn.addEventListener("click", async () => {
    if (tryOnBtn.disabled) return;

    // Loading state
    state.processing = true;
    tryOnBtn.disabled = true;
    tryOnBtn.classList.add("loading");
    btnText.textContent = "Processing...";
    spinner.classList.remove("hidden");
    statusMessage.textContent = "Sending images to GPU server...";
    statusMessage.style.color = "";
    resultPlaceholder.classList.remove("hidden");
    resultDisplay.classList.add("hidden");

    const formData = new FormData();
    formData.append("person_image", state.personFile);
    formData.append("cloth_image", state.clothFile);
    formData.append("cloth_type", state.clothType);
    formData.append("num_inference_steps", "30");
    formData.append("guidance_scale", "4.0");
    formData.append("seed", "42");

    try {
        const startTime = Date.now();
        statusMessage.textContent = "Running inference on GPU... This may take 60–90 seconds.";

        const resp = await fetch("/api/try-on", {
            method: "POST",
            body: formData,
        });
        const data = await resp.json();

        if (resp.ok && data.status === "success") {
            const clientElapsed = ((Date.now() - startTime) / 1000).toFixed(1);

            resultPerson.src = URL.createObjectURL(state.personFile);
            resultImage.src = `data:image/png;base64,${data.result_image}`;
            resultPlaceholder.classList.add("hidden");
            resultDisplay.classList.remove("hidden");
            elapsedTime.textContent = `GPU: ${data.elapsed_seconds}s  |  Total: ${clientElapsed}s`;
            statusMessage.textContent = "Done!";
            statusMessage.style.color = "var(--success)";

            // Scroll result into view
            document.getElementById("result-section").scrollIntoView({ behavior: "smooth", block: "center" });
        } else {
            statusMessage.textContent = `Error: ${data.detail || "Unknown error"}`;
            statusMessage.style.color = "var(--error)";
        }
    } catch (e) {
        statusMessage.textContent = `Network error: ${e.message}`;
        statusMessage.style.color = "var(--error)";
    } finally {
        state.processing = false;
        tryOnBtn.classList.remove("loading");
        tryOnBtn.disabled = false;
        btnText.textContent = "Generate Try-On";
        spinner.classList.add("hidden");
        updateTryOnButton();
        setTimeout(() => {
            statusMessage.style.color = "";
        }, 5000);
    }
});

// ===== DOWNLOAD =====

downloadBtn.addEventListener("click", () => {
    const link = document.createElement("a");
    link.href = resultImage.src;
    link.download = `tryon_result_${Date.now()}.png`;
    link.click();
});

// ===== INIT =====
loadColabUrl();
updateSteps();
