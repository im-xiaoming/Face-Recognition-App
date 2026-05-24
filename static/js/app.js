/**
 * Thiên Nhãn Linh Kính - Main JavaScript
 * Chứa các hàm dùng chung cho camera và xử lý ảnh
 */

let videoStream = null;
let recognitionInterval = null;
let transitionInProgress = false;

function shouldAnimateNavigation(event, link) {
  if (!link || transitionInProgress) return false;
  if (event.defaultPrevented || event.button !== 0) return false;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
  if (link.target && link.target !== '_self') return false;
  if (link.hasAttribute('download')) return false;

  const href = link.getAttribute('href');
  if (!href || href.startsWith('#')) return false;

  const nextUrl = new URL(href, window.location.href);
  if (nextUrl.origin !== window.location.origin) return false;
  if (nextUrl.href === window.location.href) return false;

  return true;
}

function runPageTransition(nextHref) {
  transitionInProgress = true;
  document.body.classList.remove('page-enter');
  document.body.classList.add('is-leaving');

  if (videoStream) {
    videoStream.getTracks().forEach(track => track.stop());
    videoStream = null;
  }
  if (recognitionInterval) {
    clearInterval(recognitionInterval);
    recognitionInterval = null;
  }

  window.setTimeout(() => {
    window.location.href = nextHref;
  }, 430);
}

/**
 * Khởi tạo camera và hiển thị lên video element
 * @param {string} elementId - ID của thẻ video
 */
async function initCamera(elementId) {
  const video = document.getElementById(elementId);

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
    const insecure = location.protocol !== 'https:' && !isLocal;
    const msg = insecure
      ? 'Pháp kính cần HTTPS trên iPhone/Safari. Hãy mở trang qua HTTPS (ngrok/cloudflared/runserver_plus).'
      : 'Trình duyệt này chưa mở được pháp kính.';
    showStatus(msg);
    throw new Error(msg);
  }

  try {
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: 640, height: 480 }
    });
    video.srcObject = videoStream;
    video.setAttribute('playsinline', '');
    video.setAttribute('muted', '');
    video.muted = true;
    try { await video.play(); } catch (_) { /* iOS may need user gesture */ }
  } catch (err) {
    const reason = err && err.name === 'NotAllowedError'
      ? 'Bạn đã từ chối quyền pháp kính. Vào Cài đặt → Safari → Camera để cấp lại.'
      : `Không thể khai mở pháp kính: ${err.message || err.name}`;
    showStatus(reason);
    throw err;
  }
}

/**
 * Dừng camera và giải phóng tài nguyên
 */
function stopCamera() {
  if (videoStream) {
    videoStream.getTracks().forEach(track => track.stop());
    videoStream = null;
  }
  if (recognitionInterval) {
    clearInterval(recognitionInterval);
    recognitionInterval = null;
  }
  showStatus('Đã khép pháp kính');
}

/**
 * Chụp ảnh từ camera để đăng ký khuôn mặt
 */
function capturePhoto() {
  const video = document.getElementById('camera');
  const canvas = document.createElement('canvas');
  
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  
  const imageData = canvas.toDataURL('image/jpeg');
  
  // Demo: Lưu ảnh vào localStorage
  const faces = JSON.parse(localStorage.getItem('faces') || '[]');
  faces.push({ id: Date.now(), image: imageData });
  localStorage.setItem('faces', JSON.stringify(faces));
  
  showStatus('Đã ghi danh linh diện thành công!');
  stopCamera();
}

/** Lưu trữ tạm các ảnh đã upload */
let uploadedImages = [];

/**
 * Xem trước nhiều ảnh được upload
 * @param {Event} event - Event từ input file
 */
function previewImage(event) {
  const files = event.target.files;
  const btn = document.getElementById('register-btn');

  if (!files.length) {
    if (btn) btn.disabled = true;
    return;
  }

  const count = files.length;
  const valid = count >= 2 && count <= 5;
  if (btn) btn.style.display = valid ? 'flex' : 'none';

  const statusEl = document.getElementById('status');
  if (statusEl) {
    if (count < 2) {
      statusEl.textContent = `Vui lòng chọn ít nhất 2 ảnh linh diện (đang chọn ${count})`;
      statusEl.style.display = 'block';
    } else if (count > 5) {
      statusEl.textContent = `Tối đa 5 ảnh linh diện (đang chọn ${count})`;
      statusEl.style.display = 'block';
    } else {
      statusEl.style.display = 'none';
    }
  }

  const icon = document.getElementById('upload-icon');
  const text = document.getElementById('upload-text');
  const preview = document.getElementById('preview');
  
  // Ẩn icon và text mặc định
  icon.style.display = 'none';
  text.style.display = 'none';
  preview.style.display = 'none';
  
  // Tạo container chứa preview nếu chưa có
  let previewContainer = document.getElementById('preview-container');
  if (!previewContainer) {
    previewContainer = document.createElement('div');
    previewContainer.id = 'preview-container';
    previewContainer.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;justify-content:center;';
    preview.parentNode.appendChild(previewContainer);
  }
  previewContainer.innerHTML = '';
  uploadedImages = [];
  
  // Đọc từng file và tạo preview
  Array.from(files).forEach(file => {
    const reader = new FileReader();
    reader.onload = function(e) {
      uploadedImages.push(e.target.result);
      
      const img = document.createElement('img');
      img.src = e.target.result;
      img.style.cssText = 'width:80px;height:80px;object-fit:cover;border-radius:8px;';
      previewContainer.appendChild(img);
    };
    reader.readAsDataURL(file);
  });
}

/**
 * Đăng ký khuôn mặt từ các ảnh đã upload
 */
function registerUploadedPhoto() {
  if (!uploadedImages.length) {
    showStatus('Vui lòng chọn ảnh linh diện trước');
    return;
  }
  
  // Demo: Lưu tất cả ảnh vào localStorage
  const faces = JSON.parse(localStorage.getItem('faces') || '[]');
  uploadedImages.forEach(img => {
    faces.push({ id: Date.now() + Math.random(), image: img });
  });
  localStorage.setItem('faces', JSON.stringify(faces));
  
  showStatus('Đã ghi danh ' + uploadedImages.length + ' ảnh linh diện!');
  uploadedImages = [];
}

/**
 * Bắt đầu quá trình nhận diện khuôn mặt
 * Demo: Giả lập việc quét mỗi 2 giây
 */
function startRecognition() {
  const faces = JSON.parse(localStorage.getItem('faces') || '[]');
  
  if (faces.length === 0) {
    showStatus('Chưa có đạo hữu nào lưu danh');
    return;
  }
  
  let scanCount = 0;
  
  recognitionInterval = setInterval(() => {
    scanCount++;
    
    // Demo: Random kết quả nhận diện
    if (scanCount % 3 === 0 && faces.length > 0) {
      showStatus('Đã nhận diện đạo hữu #' + faces[0].id);
    } else {
      showStatus('Thiên nhãn đang dò linh diện...');
    }
  }, 1000);
}

/**
 * Hiển thị thông báo trạng thái
 * @param {string} message - Nội dung thông báo
 */
function showStatus(message) {
  const status = document.getElementById('status');
  if (status) {
    status.textContent = message;
    status.style.display = 'block';
  }
}

/**
 * Bật/tắt menu dropdown
 */
function toggleMenu() {
  const menu = document.getElementById('menu');
  menu.classList.toggle('show');
}

// Đóng menu khi click ra ngoài
document.addEventListener('click', function(e) {
  const menu = document.getElementById('menu');
  const btn = document.querySelector('.menu-btn');
  if (menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) {
    menu.classList.remove('show');
  }
});

document.addEventListener('DOMContentLoaded', function() {
  document.body.classList.add('page-enter');
});

window.addEventListener('pageshow', function() {
  transitionInProgress = false;
  document.body.classList.remove('is-leaving');
  document.body.classList.add('page-enter');
});

document.addEventListener('click', function(event) {
  const link = event.target.closest('a[href]');
  if (!shouldAnimateNavigation(event, link)) return;

  event.preventDefault();
  runPageTransition(link.href);
});
