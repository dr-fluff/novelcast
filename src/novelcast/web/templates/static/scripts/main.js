document.addEventListener("DOMContentLoaded", function () {
  const subscribeForm = document.getElementById("subscribe-form");
  const modal = document.getElementById("chapter-modal");
  const modalText = document.getElementById("modal-text");
  const chapterCountSpan = document.getElementById("chapter-count");
  const acceptBtn = document.getElementById("accept-btn");
  const cancelBtn = document.getElementById("cancel-btn");
  const chaptersInput = document.getElementById("chapters");

  let currentUrl = "";

  if (!subscribeForm || !modal) {
    return;
  }

  modal.style.display = "none";

  window.addEventListener("pageshow", function (event) {
    modal.style.display = "none";
  });

  subscribeForm.addEventListener("submit", function (event) {
    event.preventDefault();

    const urlInput = subscribeForm.querySelector("input[name=url]");
    currentUrl = urlInput?.value.trim();

    if (!currentUrl) {
      alert("Please enter a novel URL before subscribing.");
      return;
    }

    // Fetch chapter count
    fetch(`/get_chapters?url=${encodeURIComponent(currentUrl)}`)
      .then(response => response.json())
      .then(data => {
        const chapters = data.chapters || 0;
        if (chapters > 0) {
          chapterCountSpan.textContent = chapters;
          modal.style.display = "block";
        } else {
          alert("No chapters found on this page. Please check the URL.");
        }
      })
      .catch(error => {
        console.error("Error fetching chapters:", error);
        alert("Failed to fetch chapter count. Please try again.");
      });
  });

  acceptBtn.addEventListener("click", async function () {
    const chapters = parseInt(chapterCountSpan.textContent, 10);
    if (chaptersInput) {
      chaptersInput.value = String(chapters);
    }
    modal.style.display = "none";
    const loading = document.createElement("div");
    loading.id = "loading-overlay";
    loading.innerHTML = `
      <div class="loading-content">
        <h2>Downloading Chapters...</h2>
        <div class="progress-bar">
          <div class="progress-fill" id="progress-fill"></div>
        </div>
        <p id="progress-text">Preparing download...</p>
      </div>
    `;
    document.body.appendChild(loading);

    // Progress animation up to 90%
    let progress = 0;
    const progressFill = document.getElementById("progress-fill");
    const progressText = document.getElementById("progress-text");
    const interval = setInterval(() => {
      progress += Math.random() * 10;
      if (progress > 90) progress = 90;
      progressFill.style.width = progress + "%";
      progressText.textContent = `Downloading... ${Math.round(progress)}%`;
    }, 200);

    // Submit form via fetch
    const formData = new FormData(subscribeForm);
    try {
      const response = await fetch('/subscribe', {
        method: 'POST',
        body: formData
      });
      if (response.redirected) {
        // Complete progress
        clearInterval(interval);
        progressFill.style.width = "100%";
        progressText.textContent = "Download complete! Redirecting...";
        // Small delay to show completion
        setTimeout(() => {
          window.location.href = response.url;
        }, 500);
      } else {
        // Get error message from response
        const errorData = await response.json();
        throw new Error(errorData.error || 'Download failed');
      }
    } catch (e) {
      clearInterval(interval);
      alert('Error: ' + e.message);
      document.body.removeChild(loading);
      modal.style.display = "none";
    }
  });

  cancelBtn.addEventListener("click", function () {
    modal.style.display = "none";
  });

  // Close modal when clicking outside
  window.addEventListener("click", function (event) {
    if (event.target === modal) {
      modal.style.display = "none";
    }
  });

  // Handle thumbnail image errors
  document.addEventListener("DOMContentLoaded", function () {
    const thumbImages = document.querySelectorAll(".fiction-thumb img");
    thumbImages.forEach(img => {
      img.addEventListener("error", function () {
        this.src = "/static/images/cover-placeholder.svg";
      });
    });
  });
});
