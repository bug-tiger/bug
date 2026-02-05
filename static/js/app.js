document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('videoForm');
    const submitBtn = document.getElementById('submitBtn');
    const blogContent = document.getElementById('blogContent');
    const charCount = document.getElementById('charCount');

    const progressSection = document.getElementById('progressSection');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const progressSteps = document.querySelectorAll('.progress-steps .step');

    const resultSection = document.getElementById('resultSection');
    const downloadBtn = document.getElementById('downloadBtn');
    const viewScriptBtn = document.getElementById('viewScriptBtn');
    const scriptPreview = document.getElementById('scriptPreview');
    const scriptContent = document.getElementById('scriptContent');
    const newVideoBtn = document.getElementById('newVideoBtn');

    const errorSection = document.getElementById('errorSection');
    const errorText = document.getElementById('errorText');
    const retryBtn = document.getElementById('retryBtn');

    let currentVideoId = null;
    let pollInterval = null;

    // Character count
    blogContent.addEventListener('input', () => {
        const count = blogContent.value.length;
        charCount.textContent = `${count.toLocaleString()} 글자`;

        // 색상 변경 (권장: 1000-5000자)
        if (count < 500) {
            charCount.style.color = '#f59e0b';
        } else if (count > 10000) {
            charCount.style.color = '#ef4444';
        } else {
            charCount.style.color = '#10b981';
        }
    });

    // Form submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const data = {
            blog_content: document.getElementById('blogContent').value,
            title: document.getElementById('title').value,
            voice: document.getElementById('voice').value,
            background_color: document.getElementById('bgColor').value,
            text_color: document.getElementById('textColor').value,
            gemini_api_key: document.getElementById('geminiApiKey').value,
            elevenlabs_api_key: document.getElementById('elevenlabsApiKey').value,
            pexels_api_key: document.getElementById('pexelsApiKey').value,
            use_broll: document.getElementById('useBroll').checked
        };

        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="ri-loader-4-line spin"></i> 처리 중...';

            hideAllSections();
            progressSection.classList.remove('hidden');
            progressFill.style.width = '5%';
            progressText.textContent = '요청 전송 중...';
            resetProgressSteps();

            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.video_id) {
                currentVideoId = result.video_id;
                startPolling();
            } else {
                throw new Error(result.detail || '영상 생성 요청 실패');
            }
        } catch (error) {
            showError(error.message);
        }
    });

    // Poll for progress
    function startPolling() {
        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/progress/${currentVideoId}`);
                const progress = await response.json();

                progressFill.style.width = `${progress.progress}%`;
                progressText.textContent = progress.step;

                // Update progress steps
                updateProgressSteps(progress.progress);

                if (progress.status === 'completed') {
                    clearInterval(pollInterval);
                    showResult();
                } else if (progress.status === 'error') {
                    clearInterval(pollInterval);
                    showError(progress.step);
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 1000);
    }

    // Update progress steps visualization
    function updateProgressSteps(progress) {
        progressSteps.forEach(step => {
            const stepName = step.dataset.step;
            let threshold = 0;

            switch (stepName) {
                case 'script': threshold = 10; break;
                case 'image': threshold = 25; break;
                case 'audio': threshold = 40; break;
                case 'video': threshold = 70; break;
            }

            if (progress >= threshold) {
                step.classList.add('active');
            }
            if (progress >= threshold + 20) {
                step.classList.add('completed');
            }
        });
    }

    // Reset progress steps
    function resetProgressSteps() {
        progressSteps.forEach(step => {
            step.classList.remove('active', 'completed');
        });
    }

    // Show result
    function showResult() {
        hideAllSections();
        resultSection.classList.remove('hidden');
        downloadBtn.href = `/api/download/${currentVideoId}`;
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="ri-movie-2-line"></i> 영상 생성하기';
    }

    // Show error
    function showError(message) {
        hideAllSections();
        errorSection.classList.remove('hidden');
        errorText.textContent = message;
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="ri-movie-2-line"></i> 영상 생성하기';
    }

    // Hide all sections
    function hideAllSections() {
        progressSection.classList.add('hidden');
        resultSection.classList.add('hidden');
        errorSection.classList.add('hidden');
    }

    // View script
    viewScriptBtn.addEventListener('click', async () => {
        try {
            const response = await fetch(`/api/script/${currentVideoId}`);
            const data = await response.json();

            if (data.script) {
                scriptContent.textContent = data.script;
                scriptPreview.classList.toggle('hidden');
                viewScriptBtn.innerHTML = scriptPreview.classList.contains('hidden')
                    ? '<i class="ri-file-text-line"></i> 스크립트 보기'
                    : '<i class="ri-eye-off-line"></i> 스크립트 숨기기';
            }
        } catch (error) {
            console.error('Script fetch error:', error);
        }
    });

    // New video
    newVideoBtn.addEventListener('click', () => {
        hideAllSections();
        form.reset();
        charCount.textContent = '0 글자';
        charCount.style.color = '';
        currentVideoId = null;
        scriptPreview.classList.add('hidden');
        resetProgressSteps();
    });

    // Retry
    retryBtn.addEventListener('click', () => {
        hideAllSections();
    });

    // API key localStorage persistence
    const apiKeyFields = ['geminiApiKey', 'elevenlabsApiKey', 'pexelsApiKey'];

    apiKeyFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        const savedValue = localStorage.getItem(fieldId);

        if (savedValue) {
            field.value = savedValue;
        }

        field.addEventListener('change', () => {
            if (field.value) {
                localStorage.setItem(fieldId, field.value);
            } else {
                localStorage.removeItem(fieldId);
            }
        });
    });
});
