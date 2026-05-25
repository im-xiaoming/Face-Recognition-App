(function () {
  let recognitionBusy = false;
  let stableRecognition = {
    userId: null,
    count: 0,
  };

  function captureCameraFrame(video) {
    if (!video.videoWidth || !video.videoHeight) return Promise.resolve(null);

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.9);
    });
  }

  function syncOverlaySize(video, overlay) {
    if (!overlay) return;
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (w && h && (overlay.width !== w || overlay.height !== h)) {
      overlay.width = w;
      overlay.height = h;
    }
  }

  function clearOverlay(overlay) {
    if (!overlay) return;
    const ctx = overlay.getContext('2d');
    ctx.clearRect(0, 0, overlay.width, overlay.height);
  }

  function drawBoundingBox(overlay, result) {
    if (!overlay || !result || !result.bbox || !result.frame_size) {
      clearOverlay(overlay);
      return;
    }

    const cssW = overlay.clientWidth;
    const cssH = overlay.clientHeight;
    if (!cssW || !cssH) return;
    if (overlay.width !== cssW || overlay.height !== cssH) {
      overlay.width = cssW;
      overlay.height = cssH;
    }

    const ctx = overlay.getContext('2d');
    ctx.clearRect(0, 0, overlay.width, overlay.height);

    const fw = result.frame_size.width;
    const fh = result.frame_size.height;
    const scale = Math.min(cssW / fw, cssH / fh);
    const dispW = fw * scale;
    const dispH = fh * scale;
    const offsetX = (cssW - dispW) / 2;
    const offsetY = (cssH - dispH) / 2;

    let color = '#22c55e';
    let label = '';
    if (result.status === 'recognized' && result.user) {
      color = '#22c55e';
      const pct = Math.round((result.score || 0) * 100);
      label = `${result.user.name} (${pct}%)`;
    } else if (result.status === 'unknown') {
      color = '#ef4444';
      label = 'Vô danh';
    } else if (result.status === 'reject') {
      color = '#f59e0b';
      label = result.message || 'Linh ảnh chưa đạt';
    }

    const { x, y, w, h } = result.bbox;
    const mirroredX = fw - (x + w);
    const dx = offsetX + mirroredX * scale;
    const dy = offsetY + y * scale;
    const dw = w * scale;
    const dh = h * scale;

    ctx.lineWidth = Math.max(2, cssW * 0.004);
    ctx.strokeStyle = color;
    ctx.strokeRect(dx, dy, dw, dh);

    if (label) {
      const fontSize = Math.min(Math.max(15, cssW * 0.026), 24);
      ctx.font = `${fontSize}px "TP Han Zi", sans-serif`;
      const padding = fontSize * 0.3;
      const textWidth = ctx.measureText(label).width;
      const boxH = fontSize + padding * 2;
      const labelY = dy - boxH > 0 ? dy - boxH : dy + dh;
      ctx.fillStyle = color;
      ctx.fillRect(dx, labelY, textWidth + padding * 2, boxH);
      ctx.fillStyle = '#ffffff';
      ctx.textBaseline = 'top';
      ctx.fillText(label, dx + padding, labelY + padding);
    }
  }

  function updateStableRecognition(result, overlay) {
    const requiredFrames = 2;

    drawBoundingBox(overlay, result);

    if (result.status !== 'recognized' || !result.user) {
      stableRecognition = { userId: null, count: 0 };
      const message = result.status === 'reject'
        ? result.message
        : 'Chưa nhận ra đạo hữu';
      showStatus(message || 'Chưa nhận ra đạo hữu');
      return;
    }

    if (stableRecognition.userId === result.user.id) {
      stableRecognition.count += 1;
    } else {
      stableRecognition = { userId: result.user.id, count: 1 };
    }

    if (stableRecognition.count >= requiredFrames) {
      showStatus(`Đã nhận diện đạo hữu: ${result.user.name} (${Math.round(result.score * 100)}%)`);
    } else {
      showStatus('Đang đối chiếu linh tức...');
    }
  }

  window.startBackendRecognition = function startBackendRecognition() {
    const video = document.getElementById('camera');
    const overlay = document.getElementById('overlay');
    if (!video) return;

    const apiUrl = video.dataset.recognitionUrl || '/recognition/api/';
    stableRecognition = { userId: null, count: 0 };
    showStatus('Thiên nhãn đang dò linh diện...');
    clearOverlay(overlay);

    recognitionInterval = setInterval(async () => {
      if (recognitionBusy || !videoStream) return;

      recognitionBusy = true;
      try {
        syncOverlaySize(video, overlay);
        const blob = await captureCameraFrame(video);
        if (!blob) {
          showStatus('Đang khai mở pháp kính...');
          return;
        }

        const formData = new FormData();
        formData.append('image', blob, 'frame.jpg');

        const response = await fetch(apiUrl, {
          method: 'POST',
          body: formData,
        });
        const result = await response.json();
        updateStableRecognition(result, overlay);
      } catch (err) {
        stableRecognition = { userId: null, count: 0 };
        clearOverlay(overlay);
        showStatus(`Thiên nhãn nhiễu loạn: ${err.message}`);
      } finally {
        recognitionBusy = false;
      }
    }, 1000);
  };
}());
