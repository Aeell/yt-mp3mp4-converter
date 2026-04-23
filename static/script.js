(function() {
    const form = document.getElementById('convertForm');
    const urlInput = document.getElementById('videoUrl');
    const convertBtn = document.getElementById('convertBtn');
    const formatBtns = document.querySelectorAll('.format-btn');
    const qualitySelect = document.getElementById('quality');
    const mp3Quality = document.getElementById('mp3Quality');
    const mp4Quality = document.getElementById('mp4Quality');
    const videoInfo = document.getElementById('videoInfo');
    const videoTitle = document.getElementById('videoTitle');
    const videoDuration = document.getElementById('videoDuration');
    const videoType = document.getElementById('videoType');
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressStatus = document.getElementById('progressStatus');
    const progressPercent = document.getElementById('progressPercent');
    const progressText = document.getElementById('progressText');
    const resultDiv = document.getElementById('result');
    const successMessage = document.getElementById('successMessage');
    const downloadLink = document.getElementById('downloadLink');
    const errorDiv = document.getElementById('error');
    const navMp4 = document.getElementById('navMp4');
    const navPlaylist = document.getElementById('navPlaylist');

    let currentFormat = 'mp3';
    let pollInterval = null;
    let currentVideoInfo = null;

    formatBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            formatBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFormat = btn.dataset.format;

            if (currentFormat === 'mp3') {
                mp3Quality.style.display = 'block';
                mp4Quality.style.display = 'none';
                qualitySelect.value = '320kbps';
            } else {
                mp3Quality.style.display = 'none';
                mp4Quality.style.display = 'block';
                qualitySelect.value = '1080p';
            }
        });
    });

    navMp4.addEventListener('click', (e) => {
        e.preventDefault();
        formatBtns.forEach(b => b.classList.remove('active'));
        document.querySelector('[data-format="mp4"]').classList.add('active');
        currentFormat = 'mp4';
        mp3Quality.style.display = 'none';
        mp4Quality.style.display = 'block';
        qualitySelect.value = '1080p';
    });

    navPlaylist.addEventListener('click', (e) => {
        e.preventDefault();
    });

    urlInput.addEventListener('blur', async () => {
        const url = urlInput.value.trim();
        if (!url || (!url.includes('youtube.com') && !url.includes('youtu.be'))) {
            videoInfo.style.display = 'none';
            return;
        }
        
        try {
            const response = await fetch('/api/info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            
            const data = await response.json();
            
            if (response.ok && data.title) {
                currentVideoInfo = data;
                videoTitle.textContent = data.title;
                
                const mins = Math.floor(data.duration / 60);
                const secs = data.duration % 60;
                videoDuration.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
                
                videoType.textContent = data.is_playlist 
                    ? `Playlist (${data.playlist_count} videos)` 
                    : 'Single Video';
                
                videoInfo.style.display = 'block';
            } else {
                videoInfo.style.display = 'none';
            }
        } catch (err) {
            videoInfo.style.display = 'none';
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const url = urlInput.value.trim();
        if (!url) return;

        hideError();
        hideResult();
        showProgress();

        const quality = qualitySelect.value;
        const format = currentFormat;

        convertBtn.disabled = true;
        convertBtn.textContent = 'Converting...';

        try {
            const response = await fetch('/api/convert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, format, quality })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Conversion failed');
            }

            if (data.video_title) {
                successMessage.textContent = `Converted: ${data.video_title}`;
            }

            pollStatus(data.task_id);

        } catch (err) {
            showError(err.message);
            hideProgress();
            convertBtn.disabled = false;
            convertBtn.textContent = 'Convert';
        }
    });

    function pollStatus(taskId) {
        let lastProgress = 0;
        
        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${taskId}`);
                
                if (response.status === 404) {
                    clearInterval(pollInterval);
                    showError('Task not found. Please try again.');
                    hideProgress();
                    convertBtn.disabled = false;
                    convertBtn.textContent = 'Convert';
                    return;
                }
                
                const data = await response.json();

                if (data.progress !== lastProgress) {
                    lastProgress = data.progress;
                    updateProgress(data.progress, data.status, data.video_title);
                }

                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    showDownload(taskId, data.video_title);
                    convertBtn.disabled = false;
                    convertBtn.textContent = 'Convert';
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    showError(data.error || 'Conversion failed');
                    hideProgress();
                    convertBtn.disabled = false;
                    convertBtn.textContent = 'Convert';
                }

            } catch (err) {
                clearInterval(pollInterval);
                showError('Failed to check status');
                hideProgress();
                convertBtn.disabled = false;
                convertBtn.textContent = 'Convert';
            }
        }, 1000);
    }

    function updateProgress(progress, status, title) {
        progressFill.style.width = progress + '%';
        progressPercent.textContent = progress + '%';
        
        if (status === 'starting') {
            progressStatus.textContent = 'Preparing...';
            progressText.textContent = title || '';
        } else if (status === 'processing') {
            progressStatus.textContent = 'Converting...';
            if (title) {
                progressText.textContent = title;
            }
        }
    }

    function showProgress() {
        progressContainer.style.display = 'block';
        progressFill.style.width = '0%';
        progressPercent.textContent = '0%';
        progressStatus.textContent = 'Starting...';
        progressText.textContent = '';
    }

    function hideProgress() {
        progressContainer.style.display = 'none';
    }

    function showDownload(taskId, title) {
        hideProgress();
        if (title) {
            successMessage.textContent = `✓ ${title}`;
        } else {
            successMessage.textContent = 'Conversion complete!';
        }
        downloadLink.href = `/api/download/${taskId}`;
        resultDiv.style.display = 'block';
    }

    function hideResult() {
        resultDiv.style.display = 'none';
    }

    function showError(message) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }

    function hideError() {
        errorDiv.style.display = 'none';
    }
})();