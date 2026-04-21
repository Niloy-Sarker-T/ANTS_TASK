const uploadBtn = document.getElementById("uploadBtn");
const videoFile = document.getElementById("videoFile");
const message = document.getElementById("message");

const progressSection = document.getElementById("progressSection");
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");

const resultSection = document.getElementById("resultSection");
const outputVideo = document.getElementById("outputVideo");
const summary = document.getElementById("summary");
const csvLink = document.getElementById("csvLink");
const xlsxLink = document.getElementById("xlsxLink");

uploadBtn.addEventListener("click", async () => {
  if (!videoFile.files.length) {
    message.textContent = "Please select an MP4 file.";
    return;
  }

  const file = videoFile.files[0];
  const formData = new FormData();
  formData.append("file", file);

  message.textContent = "Uploading...";
  progressSection.style.display = "block";
  resultSection.style.display = "none";

  progressFill.style.width = "0%";
  progressText.textContent = "0%";

  try {
    const res = await fetch("/upload", {
      method: "POST",
      body: formData
    });

    const data = await res.json();

    if (!res.ok) {
      message.textContent = data.error || "Upload failed.";
      return;
    }

    const jobId = data.job_id;
    message.textContent = "Processing started...";

    const poll = setInterval(async () => {
      const statusRes = await fetch(`/status/${jobId}`);
      const statusData = await statusRes.json();

      if (statusData.error) {
        clearInterval(poll);
        message.textContent = statusData.error;
        return;
      }

      const progress = statusData.progress || 0;
      progressFill.style.width = progress + "%";
      progressText.textContent = progress + "%";

      if (statusData.status === "done") {
        clearInterval(poll);
        message.textContent = "Processing complete.";

        const resultRes = await fetch(`/result/${jobId}`);
        const resultData = await resultRes.json();

        outputVideo.src = resultData.video_url;

        csvLink.href = resultData.csv_url;
        xlsxLink.href = resultData.xlsx_url;

        summary.innerHTML = `
          <p><b>Total Unique Vehicles:</b> ${resultData.total_unique}</p>
          <p><b>Processing Time:</b> ${resultData.processing_duration}s</p>
          <pre>${JSON.stringify(resultData.vehicle_counts, null, 2)}</pre>
        `;

        resultSection.style.display = "block";
      }

      if (statusData.status === "error") {
        clearInterval(poll);
        message.textContent = "Processing failed: " + statusData.error;
      }
    }, 1500);

  } catch (err) {
    message.textContent = "Server error: " + err.message;
  }
});