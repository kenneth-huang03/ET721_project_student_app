document.addEventListener("DOMContentLoaded", function () {
    autoDismissFlashes();
    wireDeleteConfirmations();
    wireFileInputFeedback();
    autoFocusFirstInput();
    preventDoubleSubmit();
});

function autoDismissFlashes() {
    document.querySelectorAll(".flash-msg").forEach(function (element) {
        element.style.transition = "opacity 0.4s ease";
        element.addEventListener("click", function () { dismissFlash(element); });
        setTimeout(function () { dismissFlash(element); }, 5000);
    });
}

function dismissFlash(element) {
    if (element.dataset.dismissing) return;
    element.dataset.dismissing = "1";
    element.style.opacity = "0";
    setTimeout(function () { element.remove(); }, 450);
}

function wireDeleteConfirmations() {
    const prompts = [
        [".post-del", "Delete this post?"],
        [".file-del", "Delete this file? This cannot be undone."],
        [".todo-del", "Delete this task?"],
    ];

    prompts.forEach(function (pair) {
        document.querySelectorAll(pair[0]).forEach(function (button) {
            button.addEventListener("click", function (event) {
                if (!confirm(pair[1])) event.preventDefault();
            });
        });
    });
}

function wireFileInputFeedback() {
    const fileInput = document.getElementById("file");
    if (!fileInput) return;

    const label = document.createElement("p");
    label.className = "file-selected";
    fileInput.insertAdjacentElement("afterend", label);

    fileInput.addEventListener("change", function () {
        const file = fileInput.files[0];
        label.textContent = file
            ? "Selected: " + file.name + " (" + formatBytes(file.size) + ")"
            : "";
    });
}

function autoFocusFirstInput() {
    const target = document.querySelector("input[type='text'], input[type='password'], textarea");
    if (target) target.focus();
}

function preventDoubleSubmit() {
    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function () {
            const submitButton = form.querySelector("button[type='submit']");
            if (!submitButton) return;

            setTimeout(function () {
                submitButton.disabled = true;
                if (!form.classList.contains("inline-form")) {
                    submitButton.textContent = "Working…";
                }
            }, 0);
        });
    });
}

function formatBytes(bytes) {
    if (bytes < 1024) {
        return bytes + " B";
    }
    if (bytes < 1024 * 1024) {
        return (bytes / 1024).toFixed(1) + " KB";
    }
    if (bytes < 1024 * 1024 * 1024) {
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
}
