/**
 * Luân Hồi Truy Diện Kính - Main JavaScript
 * Chứa các hàm dùng chung cho camera và xử lý ảnh
 */

let videoStream = null;
let recognitionInterval = null;
let transitionInProgress = false;
const TEXT_MODE_STORAGE_KEY = 'face_app_text_mode';
const AUTO_LOGOUT_DELAY_MS = 30 * 1000;
const AUTO_LOGOUT_AT_KEY = 'face_app_auto_logout_at';
let autoLogoutTimer = null;

const NORMAL_TEXT_REPLACEMENTS = [
  ['Chính diện nhìn vào pháp kính', 'Nhìn thẳng vào camera'],
  ['Nhìn thẳng vào pháp kính', 'Nhìn thẳng vào camera'],
  ['Xoay sang tả diện', 'Xoay mặt sang trái'],
  ['Xoay sang hữu diện', 'Xoay mặt sang phải'],
  ['Chưa thấy linh diện', 'Chưa thấy khuôn mặt'],
  ['Chỉ giữ một đạo hữu trong khung', 'Chỉ để một người trong khung'],
  ['Tiến lại gần pháp trận hơn', 'Tiến lại gần khung hơn'],
  ['Tăng linh quang sáng hơn', 'Tăng ánh sáng'],
  ['Đưa linh diện vào trong pháp trận', 'Đưa khuôn mặt vào trong khung'],
  ['Tĩnh tâm giữ yên...', 'Giữ yên...'],
  ['Đang phong ấn linh ảnh...', 'Đang lưu ảnh...'],
  ['Không tải được linh trận nhận diện', 'Không tải được mô hình nhận diện'],
  ['Đang đưa linh ảnh video lên hậu sơn...', 'Đang tải video lên server...'],
  ['Backend đang luyện hóa từng frame và phát lại video đã vẽ khung.', 'Backend đang xử lý từng khung hình và phát lại video đã vẽ khung.'],
  ['Đang phát video đã xử lý từ backend. Khung xanh được vẽ trực tiếp lên frame.', 'Đang phát video đã xử lý từ backend. Khung xanh được vẽ trực tiếp lên từng khung hình.'],
  ['Đang đối chiếu linh tức...', 'Đang đối chiếu dữ liệu...'],
  ['Đang khai mở pháp kính...', 'Đang mở camera...'],
  ['Đã khép pháp kính', 'Đã tắt camera'],
  ['Đã ghi danh linh diện thành công!', 'Đã đăng ký khuôn mặt thành công!'],
  ['Vui lòng chọn ảnh linh diện trước', 'Vui lòng chọn ảnh khuôn mặt trước'],
  ['Chưa có đạo hữu nào lưu danh', 'Chưa có người dùng nào được đăng ký'],
  ['Thiên nhãn đang dò linh diện...', 'Đang nhận diện khuôn mặt...'],
  ['Thiên nhãn nhiễu loạn', 'Lỗi nhận diện'],
  ['Linh Kính nhiễu loạn', 'Lỗi xử lý'],
  ['Luân Hồi Truy Diện Kính', 'Ứng dụng nhận diện khuôn mặt'],
  ['Linh Kính', 'Hệ thống'],
  ['Thiên nhãn', 'Hệ thống'],
  ['thiên nhãn', 'hệ thống'],
  ['pháp kính', 'camera'],
  ['Pháp kính', 'Camera'],
  ['linh kính', 'hệ thống'],
  ['linh trận nhận diện', 'mô hình nhận diện'],
  ['linh ảnh video', 'video'],
  ['linh ảnh', 'ảnh'],
  ['Linh ảnh', 'Ảnh'],
  ['linh diện', 'khuôn mặt'],
  ['Linh diện', 'Khuôn mặt'],
  ['đạo hữu', 'người dùng'],
  ['Đạo hữu', 'Người dùng'],
  ['Đạo Hữu', 'Người Dùng'],
  ['đạo danh', 'tên'],
  ['Đạo danh', 'Họ tên'],
  ['cảnh giới', 'cấp độ'],
  ['Cảnh giới', 'Cấp độ'],
  ['Niên sinh', 'Ngày sinh'],
  ['Mã số', 'Mã người dùng'],
  ['pháp trận', 'khung'],
  ['Pháp trận', 'Khung'],
  ['pháp môn', 'cách'],
  ['pháp bảo', 'hệ thống'],
  ['linh quang', 'ánh sáng'],
  ['linh tức', 'dữ liệu'],
  ['lưu danh', 'đăng ký'],
  ['ghi danh', 'đăng ký'],
  ['khai mở', 'mở'],
  ['khép', 'tắt'],
  ['nhiễu loạn', 'lỗi'],
  ['luyện hóa', 'xử lý'],
  ['hậu sơn', 'server'],
  ['phong ấn', 'lưu'],
  ['Tả Diện', 'Quay trái'],
  ['Hữu Diện', 'Quay phải'],
  ['Chính Diện', 'Nhìn thẳng'],
  ['tả diện', 'bên trái'],
  ['hữu diện', 'bên phải'],
];

function getSavedTextMode() {
  return canSwitchTextMode() && localStorage.getItem(TEXT_MODE_STORAGE_KEY) === 'normal';
}

function canSwitchTextMode() {
  return document.body && document.body.dataset.canSwitchText === 'true';
}

function isAuthenticatedSession() {
  return document.body && document.body.dataset.isAuthenticated === 'true';
}

function getCsrfToken() {
  const tokenMeta = document.querySelector('meta[name="csrf-token"]');
  if (tokenMeta && tokenMeta.content && tokenMeta.content !== 'NOTPROVIDED') {
    return tokenMeta.content;
  }

  const tokenCookie = document.cookie
    .split('; ')
    .find((part) => part.startsWith('csrftoken='));
  return tokenCookie ? decodeURIComponent(tokenCookie.split('=')[1]) : '';
}

function localizeText(message) {
  if (!getSavedTextMode() || typeof message !== 'string') return message;

  let output = message;
  NORMAL_TEXT_REPLACEMENTS.forEach(([from, to]) => {
    output = output.split(from).join(to);
  });
  return output;
}

function getOwnText(element) {
  const textNode = Array.from(element.childNodes).find((node) =>
    node.nodeType === Node.TEXT_NODE && node.nodeValue.trim()
  );
  return textNode ? textNode.nodeValue.trim() : element.textContent.trim();
}

function setOwnText(element, text) {
  const textNode = Array.from(element.childNodes).find((node) =>
    node.nodeType === Node.TEXT_NODE && node.nodeValue.trim()
  );

  if (!textNode) {
    element.textContent = text;
    return;
  }

  const current = textNode.nodeValue;
  const leading = current.match(/^\s*/)[0];
  const trailing = current.match(/\s*$/)[0];
  textNode.nodeValue = `${leading}${text}${trailing}`;
}

function applyTextMode(normalMode, persist = true) {
  if (!canSwitchTextMode()) {
    normalMode = false;
    localStorage.removeItem(TEXT_MODE_STORAGE_KEY);
  }

  if (persist) {
    localStorage.setItem(TEXT_MODE_STORAGE_KEY, normalMode ? 'normal' : 'themed');
  }

  document.body.classList.toggle('normal-language', normalMode);

  document.querySelectorAll('[data-normal-text]').forEach((element) => {
    if (!element.dataset.themedText) {
      element.dataset.themedText = getOwnText(element);
    }
    setOwnText(element, normalMode ? element.dataset.normalText : element.dataset.themedText);
  });

  document.querySelectorAll('[data-localize-text], option').forEach((element) => {
    if (!element.dataset.themedText) {
      element.dataset.themedText = getOwnText(element);
    }
    setOwnText(element, normalMode ? localizeText(element.dataset.themedText) : element.dataset.themedText);
  });

  document.querySelectorAll('[data-normal-title]').forEach((element) => {
    if (!element.dataset.themedTitle) {
      element.dataset.themedTitle = element.getAttribute('title') || '';
    }
    element.setAttribute('title', normalMode ? element.dataset.normalTitle : element.dataset.themedTitle);
  });

  const toggle = document.getElementById('text-mode-toggle');
  if (toggle) {
    toggle.textContent = normalMode ? 'Phong cách Hán Việt' : 'Chữ thường';
    toggle.setAttribute('aria-pressed', String(normalMode));
    toggle.disabled = !canSwitchTextMode();
    if (!canSwitchTextMode()) {
      toggle.setAttribute('title', 'Chỉ admin mới đổi được chế độ chữ');
    } else {
      toggle.removeAttribute('title');
    }
  }
}

function resetTextModeToDefault() {
  localStorage.removeItem(TEXT_MODE_STORAGE_KEY);
  applyTextMode(false, false);
}

function applyLoggedOutState() {
  if (!document.body) return;

  document.body.dataset.isAuthenticated = 'false';
  document.body.dataset.canSwitchText = 'false';
  sessionStorage.removeItem(AUTO_LOGOUT_AT_KEY);
  resetTextModeToDefault();
}

async function logoutWithoutReload() {
  if (!isAuthenticatedSession()) return;

  const url = document.body.dataset.autoLogoutUrl;
  if (!url) {
    applyLoggedOutState();
    return;
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
    });

    if (response.ok) {
      applyLoggedOutState();
    }
  } catch (error) {
    console.warn('Auto logout failed', error);
  }
}

function startAutoLogoutTimer() {
  if (autoLogoutTimer) {
    clearTimeout(autoLogoutTimer);
    autoLogoutTimer = null;
  }

  if (!isAuthenticatedSession()) return;

  let logoutAt = Number(sessionStorage.getItem(AUTO_LOGOUT_AT_KEY));
  if (!logoutAt) {
    logoutAt = Date.now() + AUTO_LOGOUT_DELAY_MS;
    sessionStorage.setItem(AUTO_LOGOUT_AT_KEY, String(logoutAt));
  }

  const remainingMs = logoutAt - Date.now();
  if (remainingMs <= 0) {
    logoutWithoutReload();
    return;
  }

  autoLogoutTimer = window.setTimeout(logoutWithoutReload, remainingMs);
}

window.localizeText = localizeText;

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
      statusEl.textContent = localizeText(`Vui lòng chọn ít nhất 2 ảnh linh diện (đang chọn ${count})`);
      statusEl.style.display = 'block';
    } else if (count > 5) {
      statusEl.textContent = localizeText(`Tối đa 5 ảnh linh diện (đang chọn ${count})`);
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
    status.textContent = localizeText(message);
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
  applyTextMode(getSavedTextMode(), false);
  startAutoLogoutTimer();
  document.body.classList.add('page-enter');

  const toggle = document.getElementById('text-mode-toggle');
  if (toggle) {
    toggle.addEventListener('click', function() {
      if (!canSwitchTextMode()) return;
      applyTextMode(!getSavedTextMode());
    });
  }
});

window.addEventListener('pageshow', function() {
  transitionInProgress = false;
  document.body.classList.remove('is-leaving');
  document.body.classList.add('page-enter');
  startAutoLogoutTimer();
});

window.addEventListener('focus', startAutoLogoutTimer);

document.addEventListener('visibilitychange', function() {
  if (!document.hidden) {
    startAutoLogoutTimer();
  }
});

document.addEventListener('click', function(event) {
  const link = event.target.closest('a[href]');
  if (!shouldAnimateNavigation(event, link)) return;

  event.preventDefault();
  runPageTransition(link.href);
});
