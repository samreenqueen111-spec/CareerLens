/**
 * CareerLens AI - Analyzer Workspace Controller (analyzer.js - Stage 3)
 * Manages drag & drop file uploads, real-time client & server-side validation,
 * automatic PDF/DOCX text extraction, detected section badges, extracted text preview,
 * and REAL Job Description Analysis (skills, preferred, soft skills, education, experience, keywords).
 */

document.addEventListener("DOMContentLoaded", () => {
  // Stage 1 & 2 File Elements
  const dropzone = document.getElementById("resume-dropzone");
  const fileInput = document.getElementById("resume-file-input");
  const selectedFilePill = document.getElementById("selected-file-pill");
  const fileNameDisplay = document.getElementById("selected-file-name");
  const fileSizeDisplay = document.getElementById("selected-file-size");
  const removeFileBtn = document.getElementById("remove-file-btn");
  const validationErrorBox = document.getElementById("file-validation-msg");

  // Stage 2 Parsed Resume Elements
  const parsedContainer = document.getElementById("parsed-resume-container");
  const parseSuccessMsg = document.getElementById("parse-success-msg");
  const parsedFileTypeBadge = document.getElementById("parsed-filetype-badge");
  const parsedCharCount = document.getElementById("parsed-char-count");
  const parsedWordCount = document.getElementById("parsed-word-count");
  const parsedContactSummary = document.getElementById("parsed-contact-summary");
  const detectedSectionsCounter = document.getElementById("detected-sections-counter");
  const detectedSectionsList = document.getElementById("detected-sections-list");
  const extractedTextView = document.getElementById("extracted-text-view");
  const extractedTextWrapper = document.getElementById("extracted-text-wrapper");
  const copyExtractedTextBtn = document.getElementById("copy-extracted-text-btn");
  const toggleFullTextBtn = document.getElementById("toggle-full-text-btn");

  // Stage 3 Job Description Elements
  const jobTitleInput = document.getElementById("job-title-input");
  const companyInput = document.getElementById("company-input");
  const jdTextarea = document.getElementById("job-description-input");
  const wordCountDisplay = document.getElementById("jd-word-count");
  const analyzeJdBtn = document.getElementById("analyze-jd-btn");
  const jdValidationMsg = document.getElementById("jd-validation-msg");
  const analyzedJdContainer = document.getElementById("analyzed-jd-container");
  const jdAnalysisMsg = document.getElementById("jd-analysis-msg");
  const jdSkillsCountBadge = document.getElementById("jd-skills-count-badge");
  const jdExperienceVal = document.getElementById("jd-experience-val");
  const jdEducationVal = document.getElementById("jd-education-val");
  const jdRequiredSkillsBlock = document.getElementById("jd-required-skills-block");
  const jdRequiredSkillsList = document.getElementById("jd-required-skills-list");
  const jdRequiredCounter = document.getElementById("jd-required-counter");
  const jdPreferredSkillsBlock = document.getElementById("jd-preferred-skills-block");
  const jdPreferredSkillsList = document.getElementById("jd-preferred-skills-list");
  const jdPreferredCounter = document.getElementById("jd-preferred-counter");
  const jdSoftSkillsBlock = document.getElementById("jd-soft-skills-block");
  const jdSoftSkillsList = document.getElementById("jd-soft-skills-list");
  const jdSoftCounter = document.getElementById("jd-soft-counter");
  const jdKeywordsBlock = document.getElementById("jd-keywords-block");
  const jdKeywordsList = document.getElementById("jd-keywords-list");
  const jdKeywordsCounter = document.getElementById("jd-keywords-counter");

  // Submit & Loading Pipeline Elements
  const analyzeBtn = document.getElementById("analyze-submit-btn");
  const loadingModal = document.getElementById("loading-pipeline-modal");
  const pipelineSteps = document.querySelectorAll(".pipeline-step-item");

  const analyzerForm = document.getElementById("analyzer-form");
  let currentFile = null;
  let parsedResumeData = null;
  let currentJdAnalysis = null;
  let hasActiveSessionResume = selectedFilePill ? selectedFilePill.classList.contains("is-active") : false;
  const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
  const ALLOWED_EXTS = ["pdf", "docx"];

  // Check if an active resume is already cached in session
  async function checkActiveResume() {
    if (hasActiveSessionResume) return;
    try {
      const resp = await fetch("/api/active-resume");
      const data = await resp.json();
      if (data && data.has_resume) {
        hasActiveSessionResume = true;
        if (fileNameDisplay) fileNameDisplay.textContent = data.filename;
        if (fileSizeDisplay) fileSizeDisplay.textContent = `${data.file_size_kb} KB • Active resume`;
        if (selectedFilePill) selectedFilePill.classList.add("is-active");
        if (dropzone) {
          dropzone.classList.add("has-file");
          dropzone.style.display = "none";
        }
      }
    } catch (e) {
      console.warn("Could not retrieve active session resume:", e);
    }
  }
  checkActiveResume();

  const ALL_STANDARD_SECTIONS = [
    "Contact Information",
    "Summary/Profile",
    "Education",
    "Skills",
    "Experience",
    "Projects",
    "Certifications",
    "Achievements"
  ];

  // ==========================================
  // File Validation & Dropzone Handling
  // ==========================================
  async function validateAndSelectFile(file) {
    if (!file) return;

    // 1. Extension Check
    const ext = file.name.split(".").pop().toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      showValidationError(`Unsupported file format (.${ext}). Only PDF (.pdf) and Word documents (.docx) are accepted.`);
      return;
    }

    // 2. Empty Check
    if (file.size === 0) {
      showValidationError("The selected file is empty (0 bytes). Please upload a valid resume.");
      return;
    }

    // 3. Size Check
    if (file.size > MAX_FILE_SIZE) {
      const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
      showValidationError(`File is too large (${sizeMb} MB). Maximum allowed size is 5 MB.`);
      return;
    }

    currentFile = file;
    hasActiveSessionResume = true;
    clearValidationError();

    // Update UI Pill
    fileNameDisplay.textContent = file.name;
    const formattedSize = file.size > 1024 * 1024
      ? `${(file.size / (1024 * 1024)).toFixed(2)} MB`
      : `${Math.round(file.size / 1024)} KB`;
    fileSizeDisplay.textContent = formattedSize;

    selectedFilePill.classList.add("is-active");
    dropzone.classList.add("has-file");
    dropzone.style.display = "none";

    // 4. Server-Side Real Text Extraction (Stage 2)
    await parseUploadedFile(file);
  }

  async function parseUploadedFile(file) {
    if (!parsedContainer) return;

    if (window.CareerLens) {
      window.CareerLens.showToast(`Parsing ${file.name}...`, "info", 2000);
    }

    const formData = new FormData();
    formData.append("resume", file);

    try {
      const resp = await fetch("/api/parse-resume", {
        method: "POST",
        body: formData
      });

      const data = await resp.json();

      if (!resp.ok || !data.success) {
        throw new Error(data.error || "Failed to extract text from document.");
      }

      parsedResumeData = data;
      renderParsedResumeDetails(data);

      if (window.CareerLens) {
        window.CareerLens.showToast(`Successfully extracted ${data.word_count} words!`, "success", 3000);
      }
    } catch (err) {
      console.error("Parsing error:", err);
      showValidationError(err.message || "Failed to process resume file.");
      if (parsedContainer) parsedContainer.classList.remove("is-active");
    }
  }

  function renderParsedResumeDetails(data) {
    if (!parsedContainer) return;

    if (parseSuccessMsg) {
      parseSuccessMsg.textContent = `Resume parsed successfully! Identified ${data.sections_count} of ${data.total_expected_sections} common sections.`;
    }

    if (parsedFileTypeBadge) {
      parsedFileTypeBadge.textContent = data.file_type || (data.extension ? data.extension.toUpperCase() : "Document");
    }

    if (parsedCharCount) parsedCharCount.textContent = `${data.char_count.toLocaleString()} chars`;
    if (parsedWordCount) parsedWordCount.textContent = `${data.word_count.toLocaleString()} words`;

    if (parsedContactSummary && data.contact_details) {
      const emails = data.contact_details.emails || [];
      const phones = data.contact_details.phones || [];
      const parts = [];
      if (emails.length > 0) parts.push(emails[0]);
      if (phones.length > 0) parts.push(phones[0]);
      parsedContactSummary.textContent = parts.length > 0 ? parts.join(" • ") : "";
    }

    if (detectedSectionsCounter) {
      detectedSectionsCounter.textContent = `${data.sections_count} / ${data.total_expected_sections}`;
    }

    if (detectedSectionsList) {
      detectedSectionsList.innerHTML = "";
      const foundSections = data.sections || [];

      ALL_STANDARD_SECTIONS.forEach((sectionName) => {
        const isFound = foundSections.includes(sectionName);
        const pill = document.createElement("span");
        pill.className = `section-pill ${isFound ? "is-found" : "is-missing"}`;
        pill.innerHTML = isFound
          ? `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg> <span>${sectionName}</span>`
          : `<span style="opacity:0.6;">―</span> <span>${sectionName}</span>`;
        detectedSectionsList.appendChild(pill);
      });
    }

    if (extractedTextView) {
      extractedTextView.textContent = data.full_text || data.preview_text || "No text extracted.";
    }

    parsedContainer.classList.add("is-active");
  }

  async function clearFile() {
    currentFile = null;
    parsedResumeData = null;
    hasActiveSessionResume = false;
    if (fileInput) fileInput.value = "";
    selectedFilePill.classList.remove("is-active");
    dropzone.classList.remove("has-file");
    dropzone.style.display = "block";
    if (parsedContainer) parsedContainer.classList.remove("is-active");
    if (extractedTextView) extractedTextView.textContent = "";
    clearValidationError();
    try {
      await fetch("/api/active-resume", { method: "DELETE" });
    } catch (e) {
      // non-critical
    }
  }

  function showValidationError(message) {
    if (validationErrorBox) {
      validationErrorBox.textContent = message;
      validationErrorBox.style.display = "flex";
    }
    if (window.CareerLens) {
      window.CareerLens.showToast(message, "error");
    }
  }

  function clearValidationError() {
    if (validationErrorBox) {
      validationErrorBox.textContent = "";
      validationErrorBox.style.display = "none";
    }
  }

  // Click on dropzone opens native file picker
  if (dropzone && fileInput) {
    dropzone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        validateAndSelectFile(e.target.files[0]);
      }
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("is-dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("is-dragover");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
        validateAndSelectFile(e.dataTransfer.files[0]);
      }
    });
  }

  if (removeFileBtn) {
    removeFileBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      clearFile();
    });
  }

  // Copy Extracted Resume Text
  if (copyExtractedTextBtn && extractedTextView) {
    copyExtractedTextBtn.addEventListener("click", () => {
      const text = extractedTextView.textContent;
      if (!text) return;
      navigator.clipboard.writeText(text).then(() => {
        if (window.CareerLens) {
          window.CareerLens.showToast("Extracted resume text copied to clipboard!", "success");
        }
      });
    });
  }

  // Toggle Full Resume Text Expansion
  if (toggleFullTextBtn && extractedTextWrapper) {
    toggleFullTextBtn.addEventListener("click", () => {
      const isExpanded = extractedTextWrapper.classList.toggle("is-expanded");
      toggleFullTextBtn.textContent = isExpanded ? "Collapse" : "Expand";
    });
  }

  // =========================================================================
  // Stage 3: Real Job Description Analysis Engine
  // =========================================================================
  async function analyzeCurrentJobDescription() {
    if (!jdTextarea) return;

    const jdText = jdTextarea.value.trim();
    const jobTitle = jobTitleInput ? jobTitleInput.value.trim() : "";

    // Client-side quick check
    if (!jdText) {
      showJdError("Job description is empty. Please enter or paste the job posting text.");
      if (analyzedJdContainer) analyzedJdContainer.classList.remove("is-active");
      return;
    }

    if (jdText.length < 30) {
      showJdError("Job description text is too short (minimum 30 characters required).");
      if (analyzedJdContainer) analyzedJdContainer.classList.remove("is-active");
      return;
    }

    clearJdError();

    if (analyzeJdBtn) {
      analyzeJdBtn.disabled = true;
      analyzeJdBtn.innerHTML = `<span>Analyzing...</span>`;
    }

    try {
      const resp = await fetch("/api/analyze-jd", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: jdText,
          job_title: jobTitle
        })
      });

      const data = await resp.json();

      if (!resp.ok || !data.success) {
        throw new Error(data.error || "Failed to analyze job description.");
      }

      currentJdAnalysis = data;
      renderAnalyzedJdDetails(data);

      if (window.CareerLens) {
        window.CareerLens.showToast(`Extracted ${data.total_skills_count} skills from Job Description!`, "success", 2500);
      }
    } catch (err) {
      console.error("JD Analysis error:", err);
      showJdError(err.message || "Failed to analyze job description text.");
      if (analyzedJdContainer) analyzedJdContainer.classList.remove("is-active");
    } finally {
      if (analyzeJdBtn) {
        analyzeJdBtn.disabled = false;
        analyzeJdBtn.innerHTML = `
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <span>Extract Skills</span>
        `;
      }
    }
  }

  function renderAnalyzedJdDetails(data) {
    if (!analyzedJdContainer) return;

    // Header message & badge
    if (jdAnalysisMsg) {
      jdAnalysisMsg.textContent = `Job Description analyzed! Identified ${data.total_skills_count} key competencies.`;
    }
    if (jdSkillsCountBadge) {
      jdSkillsCountBadge.textContent = `${data.total_skills_count} Skills Found`;
    }

    // Experience requirement
    if (jdExperienceVal) {
      const exp = data.experience || {};
      let expText = exp.summary || "Not explicitly specified";
      if (exp.level && exp.is_specified) {
        expText = `${expText} (${exp.level})`;
      }
      jdExperienceVal.textContent = expText;
    }

    // Education requirement
    if (jdEducationVal) {
      const edu = data.education || {};
      jdEducationVal.textContent = edu.summary || "Degree or equivalent practical experience";
    }

    // Required Technical Skills
    if (jdRequiredSkillsList && jdRequiredCounter) {
      jdRequiredSkillsList.innerHTML = "";
      const reqSkills = data.required_skills || [];
      jdRequiredCounter.textContent = reqSkills.length;

      if (reqSkills.length > 0) {
        reqSkills.forEach((skill) => {
          const pill = document.createElement("span");
          pill.className = "jd-tag-pill tag-required";
          pill.innerHTML = `✓ <span>${skill}</span>`;
          jdRequiredSkillsList.appendChild(pill);
        });
        if (jdRequiredSkillsBlock) jdRequiredSkillsBlock.style.display = "block";
      } else {
        jdRequiredSkillsList.innerHTML = `<span style="font-size: var(--text-xs); color: var(--text-muted);">No specific required tools isolated.</span>`;
      }
    }

    // Preferred / Nice-to-Have Skills
    if (jdPreferredSkillsList && jdPreferredCounter) {
      jdPreferredSkillsList.innerHTML = "";
      const prefSkills = data.preferred_skills || [];
      jdPreferredCounter.textContent = prefSkills.length;

      if (prefSkills.length > 0) {
        prefSkills.forEach((skill) => {
          const pill = document.createElement("span");
          pill.className = "jd-tag-pill tag-preferred";
          pill.innerHTML = `+ <span>${skill}</span>`;
          jdPreferredSkillsList.appendChild(pill);
        });
        if (jdPreferredSkillsBlock) jdPreferredSkillsBlock.style.display = "block";
      } else {
        if (jdPreferredSkillsBlock) jdPreferredSkillsBlock.style.display = "none";
      }
    }

    // Soft Skills
    if (jdSoftSkillsList && jdSoftCounter) {
      jdSoftSkillsList.innerHTML = "";
      const softSkills = data.soft_skills || [];
      jdSoftCounter.textContent = softSkills.length;

      if (softSkills.length > 0) {
        softSkills.forEach((skill) => {
          const pill = document.createElement("span");
          pill.className = "jd-tag-pill tag-soft";
          pill.innerHTML = `★ <span>${skill}</span>`;
          jdSoftSkillsList.appendChild(pill);
        });
        if (jdSoftSkillsBlock) jdSoftSkillsBlock.style.display = "block";
      } else {
        if (jdSoftSkillsBlock) jdSoftSkillsBlock.style.display = "none";
      }
    }

    // Important Keywords
    if (jdKeywordsList && jdKeywordsCounter) {
      jdKeywordsList.innerHTML = "";
      const keywords = data.important_keywords || [];
      jdKeywordsCounter.textContent = `${keywords.length} keywords`;

      keywords.forEach((kw) => {
        const pill = document.createElement("span");
        pill.className = "jd-tag-pill tag-keyword";
        pill.innerHTML = `<span>${kw.keyword}</span> <span class="jd-keyword-freq">${kw.frequency}x</span>`;
        jdKeywordsList.appendChild(pill);
      });
    }

    analyzedJdContainer.classList.add("is-active");
  }

  function showJdError(message) {
    if (jdValidationMsg) {
      jdValidationMsg.textContent = message;
      jdValidationMsg.style.display = "flex";
    }
  }

  function clearJdError() {
    if (jdValidationMsg) {
      jdValidationMsg.textContent = "";
      jdValidationMsg.style.display = "none";
    }
  }

  // Bind Analyze JD Button
  if (analyzeJdBtn) {
    analyzeJdBtn.addEventListener("click", analyzeCurrentJobDescription);
  }

  // Word count & input updates
  if (jdTextarea && wordCountDisplay) {
    const updateStats = () => {
      const text = jdTextarea.value.trim();
      const words = text ? text.split(/\s+/).length : 0;
      const chars = text.length;
      wordCountDisplay.textContent = `${words} words • ${chars} chars`;
    };

    jdTextarea.addEventListener("input", updateStats);
    updateStats();
  }

  // Quick-Fill Sample Role Buttons
  document.querySelectorAll(".quick-fill-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const roleKey = btn.getAttribute("data-role");
      try {
        btn.textContent = "Loading...";
        const resp = await fetch(`/api/sample-jd/${roleKey}`);
        const result = await resp.json();
        if (result.success && result.data) {
          if (jobTitleInput) jobTitleInput.value = result.data.title;
          if (companyInput) companyInput.value = result.data.company;
          if (jdTextarea) {
            jdTextarea.value = result.data.description;
            jdTextarea.dispatchEvent(new Event("input"));
          }
          if (window.CareerLens) {
            window.CareerLens.showToast(`Loaded sample role: ${result.data.title}`, "info");
          }
          // Automatically run Stage 3 text analysis on sample JD
          await analyzeCurrentJobDescription();
        }
      } catch (err) {
        console.error("Failed to load sample JD:", err);
      } finally {
        const originalText = {
          fullstack: "Full Stack",
          frontend: "Frontend",
          devops: "DevOps"
        }[roleKey] || "Sample Role";
        btn.textContent = originalText;
      }
    });
  });

  // Automatically analyze initial job description on page load
  if (jdTextarea && jdTextarea.value.trim().length >= 30) {
    setTimeout(analyzeCurrentJobDescription, 350);
  }

  // ==========================================
  // Form Submission & Multi-Step Pipeline
  // ==========================================
  async function handleFormSubmission(e) {
    if (e) e.preventDefault();

    // Check resume: either a newly selected file or an active resume from session
    if (!currentFile && !hasActiveSessionResume) {
      showValidationError("Please upload your resume (.pdf or .docx) to proceed.");
      if (dropzone) dropzone.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    // Check JD
    const jdText = jdTextarea ? jdTextarea.value.trim() : "";
    if (!jdText || jdText.length < 30) {
      showJdError("Please enter or paste a job description (at least 30 characters).");
      if (jdTextarea) jdTextarea.focus();
      return;
    }

    clearValidationError();
    clearJdError();

    // Assemble current Job Title, Company, and Job Description
    const formData = new FormData();
    if (currentFile) {
      formData.append("resume", currentFile);
    }
    const currentTitle = jobTitleInput ? jobTitleInput.value.trim() : "";
    const currentCompany = companyInput ? companyInput.value.trim() : "";
    formData.append("job_title", currentTitle);
    formData.append("company", currentCompany);
    formData.append("job_description", jdText);

    // Trigger Pipeline Loading UI
    if (loadingModal) {
      loadingModal.classList.add("is-active");
    }
    if (analyzeBtn) {
      analyzeBtn.disabled = true;
    }

    // Realistic Step Transitions
    const stepDelays = [400, 600, 700, 500, 400];
    const runStepAnimation = async () => {
      for (let i = 0; i < pipelineSteps.length; i++) {
        pipelineSteps[i].classList.add("is-active");
        await new Promise((res) => setTimeout(res, stepDelays[i] || 400));
        pipelineSteps[i].classList.remove("is-active");
        pipelineSteps[i].classList.add("is-done");
        const indicator = pipelineSteps[i].querySelector(".step-indicator");
        if (indicator) indicator.textContent = "✓";
      }
    };

    try {
      const [apiResponse] = await Promise.all([
        fetch("/api/analyze", {
          method: "POST",
          body: formData
        }),
        runStepAnimation()
      ]);

      const data = await apiResponse.json();

      if (data.success && data.redirect_url) {
        // Append unique cache-busting timestamp so browser never serves stale cached results
        const sep = data.redirect_url.includes("?") ? "&" : "?";
        window.location.href = `${data.redirect_url}${sep}_t=${Date.now()}`;
      } else {
        throw new Error(data.error || "Could not analyze resume. Please try again.");
      }
    } catch (err) {
      console.error("Submission error:", err);
      if (loadingModal) loadingModal.classList.remove("is-active");
      if (analyzeBtn) analyzeBtn.disabled = false;
      showValidationError(err.message || "An unexpected error occurred. Please try again.");
    }
  }

  if (analyzerForm) {
    analyzerForm.addEventListener("submit", handleFormSubmission);
  }
  if (analyzeBtn) {
    analyzeBtn.addEventListener("click", handleFormSubmission);
  }
});
