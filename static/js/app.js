document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('videoForm');
    const submitBtn = document.getElementById('submitBtn');
    const blogContent = document.getElementById('blogContent');
    const charCount = document.getElementById('charCount');

    const progressSection = document.getElementById('progressSection');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

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
        charCount.textContent = `${blogContent.value.length} 글자`;
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
            openai_api_key: document.getElementById('apiKey').value
        };

        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="ri-loader-4-line spin"></i> 처리 중...';

            hideAllSections();
            progressSection.classList.remove('hidden');
            progressFill.style.width = '5%';
            progressText.textContent = '요청 전송 중...';

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
        currentVideoId = null;
        scriptPreview.classList.add('hidden');
    });

    // Retry
    retryBtn.addEventListener('click', () => {
        hideAllSections();
    });
});
