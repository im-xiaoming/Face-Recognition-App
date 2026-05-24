(function () {
  let currentStreamUrl = null;
  let uploadBusy = false;

  function el(id) {
    return document.getElementById(id);
  }

  function setStatus(message) {
    showStatus(message);
  }

  function resetProcessedView() {
    const image = el('processed-video');
    const placeholder = el('video-placeholder');
    if (image) {
      image.removeAttribute('src');
      image.style.display = 'none';
    }
    if (placeholder) {
      placeholder.style.display = 'grid';
    }
    currentStreamUrl = null;
  }

  function showProcessedStream(streamUrl) {
    const image = el('processed-video');
    const placeholder = el('video-placeholder');
    if (!image) return;

    currentStreamUrl = `${streamUrl}?t=${Date.now()}`;
    image.style.display = 'block';
    if (placeholder) {
      placeholder.style.display = 'none';
    }
    image.src = currentStreamUrl;
  }

  async function uploadVideo(file, uploadUrl) {
    if (uploadBusy) return;
    uploadBusy = true;

    const formData = new FormData();
    formData.append('video', file, file.name);

    try {
      resetProcessedView();
      setStatus('Đang đưa linh ảnh video lên hậu sơn...');

      const response = await fetch(uploadUrl, {
        method: 'POST',
        body: formData,
      });
      const result = await response.json();
      if (!response.ok || result.status !== 'ok') {
        throw new Error(result.message || 'Không tải được video.');
      }

      setStatus('Backend đang luyện hóa từng frame và phát lại video đã vẽ khung.');
      showProcessedStream(result.stream_url);
    } catch (err) {
      setStatus(`Linh Kính nhiễu loạn: ${err.message}`);
    } finally {
      uploadBusy = false;
    }
  }

  window.initVideoRecognition = function initVideoRecognition() {
    const input = el('video-file');
    const image = el('processed-video');
    if (!input || !image) return;

    input.addEventListener('change', (event) => {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      if (!file.type.startsWith('video/')) {
        setStatus('Vui lòng chọn đúng video.');
        return;
      }
      uploadVideo(file, input.dataset.videoUploadUrl);
    });

    image.addEventListener('load', () => {
      if (currentStreamUrl) {
        setStatus('Đang phát video đã xử lý từ backend. Khung xanh được vẽ trực tiếp lên frame.');
      }
    });

    image.addEventListener('error', () => {
      if (currentStreamUrl) {
        setStatus('Luồng video đã kết thúc hoặc bị gián đoạn.');
      }
    });
  };
}());
