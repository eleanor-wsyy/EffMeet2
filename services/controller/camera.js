/* User-controlled local camera. No stream or image is uploaded automatically. */
(() => {
  const video = $('camera-video'), photo = $('camera-photo');
  let stream = null, pending = false, uploading = false, shotBusy = false;
  let generation = 0, photoBlob = null, photoURL = null, galleryURLs = [], listVersion = 0;
  const status = (text, error = false) => {
    $('camera-status').textContent = text;
    $('camera-status').className = error ? 'error' : '';
  };
  function buttons() {
    $('camera-open').disabled = pending || !!stream || uploading;
    $('camera-shot').disabled = !stream || !video.videoWidth || uploading || shotBusy;
    $('camera-close').disabled = !stream && !pending;
    $('camera-upload').disabled = !photoBlob || uploading || shotBusy;
    $('camera-discard').disabled = !photoBlob || uploading || shotBusy;
    $('create').disabled = uploading;
  }
  function closeCamera() {
    generation++;
    if (stream) stream.getTracks().forEach(track => track.stop());
    stream = null; pending = false; video.srcObject = null; video.hidden = true;
    buttons();
  }
  function discard() {
    photoBlob = null;
    if (photoURL) URL.revokeObjectURL(photoURL);
    photoURL = null; photo.removeAttribute('src'); photo.hidden = true;
    buttons();
  }
  function clearGallery() {
    listVersion++;
    galleryURLs.forEach(url => URL.revokeObjectURL(url)); galleryURLs = [];
    $('camera-gallery').replaceChildren();
  }
  video.addEventListener('loadeddata', buttons);
  $('camera-open').onclick = async () => {
    if (!mid) return status('请先新建会议。', true);
    if (!navigator.mediaDevices?.getUserMedia) return status('当前浏览器不支持摄像头，请用 Edge 或 Chrome 打开 http://127.0.0.1:8768。', true);
    const attempt = ++generation;
    pending = true; buttons(); status('请在浏览器提示中允许摄像头权限。');
    try {
      const acquired = await navigator.mediaDevices.getUserMedia({audio: false, video: {width: {ideal: 1280}, height: {ideal: 720}}});
      if (attempt !== generation) { acquired.getTracks().forEach(track => track.stop()); return; }
      stream = acquired; video.srcObject = acquired; video.hidden = false;
      acquired.getVideoTracks().forEach(track => track.addEventListener('ended', () => {
        if (stream === acquired) { closeCamera(); status('摄像头连接已结束，可以重新开启。'); }
      }));
      await video.play();
      if (attempt === generation) status('摄像头已开启，仅本地预览。对准材料后点击“拍照”。');
    } catch (error) {
      if (attempt !== generation) return;
      closeCamera();
      const errors = {NotAllowedError:'摄像头权限被拒绝，请在地址栏的网站权限中允许后重试。', NotFoundError:'未发现摄像头，请检查设备连接。', NotReadableError:'摄像头可能被其他应用占用，请关闭相机或视频会议后重试。'};
      status(errors[error.name] || '摄像头开启失败，请检查设备或换用 Edge / Chrome。', true);
    } finally {
      if (attempt === generation) pending = false;
      buttons();
    }
  };
  $('camera-close').onclick = () => { closeCamera(); status('摄像头已关闭。已拍照片仍可确认上传或放弃。'); };
  $('camera-discard').onclick = () => { discard(); status('已放弃照片，没有上传。'); };
  $('camera-shot').onclick = async () => {
    if (!stream || !video.videoWidth || shotBusy) return;
    const attempt = generation, meeting = mid;
    shotBusy = true; buttons();
    try {
      const canvas = document.createElement('canvas');
      const scale = Math.min(1, 1600 / Math.max(video.videoWidth, video.videoHeight));
      canvas.width = Math.round(video.videoWidth * scale); canvas.height = Math.round(video.videoHeight * scale);
      canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', .85));
      if (attempt !== generation || meeting !== mid) return;
      if (!blob || blob.size > 1900000) throw Error('照片生成失败或过大，请调整拍摄分辨率后重试。');
      discard(); photoBlob = blob; photoURL = URL.createObjectURL(blob);
      photo.src = photoURL; photo.hidden = false;
      status('照片已拍摄，尚未上传。请检查清晰度；可再次拍照替换，或确认上传。');
    } catch (error) { status(error.message, true); }
    finally { shotBusy = false; buttons(); }
  };
  async function gallery() {
    if (!mid) return status('请先新建会议。', true);
    clearGallery();
    const meeting = mid, version = listVersion;
    const items = await api(`/api/v1/meetings/${meeting}/captures`);
    if (meeting !== mid || version !== listVersion) return;
    $('camera-gallery').append(elem('p', `本会议共有 ${items.length} 张图片，显示最近 20 张。`));
    for (const item of items.slice(-20).reverse()) {
      const r = await fetch(`/api/v1/meetings/${meeting}/captures/${item.capture_id}`, {headers: {Authorization: 'Bearer ' + tokens.operator}});
      if (!r.ok) throw Error('图片读取失败，请刷新重试。');
      const blob = await r.blob();
      if (meeting !== mid || version !== listVersion) return;
      const url = URL.createObjectURL(blob); galleryURLs.push(url);
      const card = elem('article', item.filename), img = document.createElement('img');
      img.src = url; img.alt = '已保存的会议图片'; img.style.cssText = 'display:block;max-width:100%;max-height:360px';
      card.append(img, elem('small', '图片编号：' + item.capture_id)); $('camera-gallery').append(card);
    }
  }
  $('camera-list').onclick = () => gallery().catch(error => status(error.message, true));
  $('camera-upload').onclick = async () => {
    if (!mid || !photoBlob || uploading) return;
    const meeting = mid; uploading = true; buttons(); status('正在保存到本机会议…');
    let saved = false;
    try {
      const form = new FormData(); form.append('file', photoBlob, `camera-${Date.now()}.jpg`);
      const r = await fetch(`/api/v1/meetings/${meeting}/captures?source=browser_camera`, {method:'POST', headers:{Authorization:'Bearer '+tokens.operator}, body:form});
      const result = await r.json();
      if (!r.ok) throw Error(result.error?.message || '上传失败');
      saved = true; discard();
      status('照片已保存到本机会议。未进行视觉模型分析。');
      await gallery();
    } catch (error) { status(saved ? '照片已保存，但列表读取失败，请点击“刷新会议图片”。' : '未收到上传成功确认，请先刷新会议图片检查是否已保存；照片仍保留。' + error.message, true); }
    finally { uploading = false; buttons(); }
  };
  window.addEventListener('meetingchanged', () => { closeCamera(); discard(); clearGallery(); status('已切换到新会议，摄像头已关闭。'); });
  window.addEventListener('pagehide', () => { closeCamera(); discard(); clearGallery(); });
  buttons();
})();
