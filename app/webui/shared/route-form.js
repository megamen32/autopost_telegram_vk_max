import { escapeHtml } from './formatters.js';

export const ROUTE_POLICY_DEFAULTS = {
  allow_text: true,
  allow_images: true,
  allow_video: true,
  allow_audio: true,
  allow_documents: false,
  allow_reposts: false,
  max_images: null,
  max_video_size_mb: null,
  max_audio_size_mb: null,
  drop_unsupported_media: true,
};

export function renderRouteDetail(route, { sourceOptions, targetOptions, helpButton }) {
  const enabled = route.policy_enabled !== false;
  const policy = route.content_policy || {};

  return `
    <div class="card route-detail">
      <div class="inline" style="justify-content:space-between; align-items:flex-start;">
        <div>
          <h3 style="margin:0">${escapeHtml(route.id)}</h3>
          <div class="muted">source: ${escapeHtml(route.source_platform)} · target: ${escapeHtml(route.target_platform)}</div>
        </div>
        <div class="inline">
          <span class="pill">${route.enabled ? 'enabled' : 'disabled'}</span>
          <button class="btn danger route-delete-inline" type="button" data-id="${escapeHtml(route.id)}">delete</button>
        </div>
      </div>

      <form class="route-policy-form" data-route-id="${escapeHtml(route.id)}">
        <div class="row">
          <label>
            <span class="label">Откуда</span>
            <select name="source_adapter_id" required>${sourceOptions}</select>
          </label>
          <label>
            <span class="label-row">
              <span class="label">Источник: chat id / username / ссылка</span>
              ${helpButton('route.source_chat')}
            </span>
            <input name="source_chat_id" required value="${escapeHtml(route.source_chat_id || '')}">
            <span class="help">Можно указать числовой chat id, @username или ссылку вида https://t.me/username</span>
          </label>
          <label>
            <span class="label">Куда</span>
            <select name="target_adapter_id" required>${targetOptions}</select>
          </label>
          <label>
            <span class="label-row">
              <span class="label">Назначение: chat id / username / ссылка</span>
              ${helpButton('route.target_chat')}
            </span>
            <input name="target_chat_id" required value="${escapeHtml(route.target_chat_id || '')}">
            <span class="help">Можно указать числовой chat id, @username или ссылку вида https://t.me/username</span>
          </label>
        </div>

        <div class="row4" style="margin-top:12px">
          <label>
            <span class="label-row">
              <span class="label">Маршрут</span>
              ${helpButton('route.enabled')}
            </span>
            <select name="policy_enabled">
              <option value="true" ${enabled ? 'selected' : ''}>включён</option>
              <option value="false" ${!enabled ? 'selected' : ''}>выключен</option>
            </select>
            <span class="help">Если выключено, этот маршрут не создаёт jobs.</span>
          </label>
          <label>
            <span class="label">Repost mode</span>
            <select name="repost_mode">
              <option value="ignore" ${route.repost_mode === 'ignore' ? 'selected' : ''}>ignore</option>
              <option value="flatten" ${route.repost_mode === 'flatten' ? 'selected' : ''}>flatten</option>
              <option value="preserve_reference" ${route.repost_mode === 'preserve_reference' ? 'selected' : ''}>preserve_reference</option>
            </select>
          </label>
          <label>
            <span class="label">Max images</span>
            <input name="max_images" value="${escapeHtml(policy.max_images ?? '')}">
          </label>
          <label>
            <span class="label">Text template</span>
            <textarea name="copy_text_template" placeholder="{text}">${escapeHtml(route.copy_text_template || '')}</textarea>
          </label>
        </div>

        <div class="row4" style="margin-top:12px">
          <label><input class="checkbox" type="checkbox" name="allow_text" ${policy.allow_text !== false ? 'checked' : ''}> Текст</label>
          <label><input class="checkbox" type="checkbox" name="allow_images" ${policy.allow_images !== false ? 'checked' : ''}> Картинки</label>
          <label><input class="checkbox" type="checkbox" name="allow_video" ${policy.allow_video !== false ? 'checked' : ''}> Видео</label>
          <label><input class="checkbox" type="checkbox" name="allow_audio" ${policy.allow_audio !== false ? 'checked' : ''}> Аудио</label>
          <label><input class="checkbox" type="checkbox" name="allow_documents" ${policy.allow_documents ? 'checked' : ''}> Документы</label>
          <label><input class="checkbox" type="checkbox" name="allow_reposts" ${policy.allow_reposts ? 'checked' : ''}> Репосты</label>
          <label><input class="checkbox" type="checkbox" name="drop_unsupported_media" ${policy.drop_unsupported_media !== false ? 'checked' : ''}> Отбрасывать неподдерживаемые медиа</label>
        </div>

        <div class="grid" style="margin-top:12px">
          <div class="card" data-route-extension="source">
            <div class="muted">Source adapter route extension.</div>
          </div>
          <div class="card" data-route-extension="target">
            <div class="muted">Target adapter route extension.</div>
          </div>
        </div>

        <div class="inline" style="margin-top:12px">
          <button class="btn" type="submit">Сохранить</button>
          <span class="muted">ID маршрута будет сохранён как есть.</span>
        </div>
      </form>
    </div>
  `;
}

export function collectRouteFormData(form, route, sourceInstance, targetInstance) {
  return {
    id: route?.id || null,
    source_adapter_id: form.source_adapter_id.value,
    source_platform: sourceInstance?.platform || route?.source_platform || null,
    source_chat_id: form.source_chat_id.value.trim(),
    source_chat_canonical: route?.source_chat_canonical || null,
    target_adapter_id: form.target_adapter_id.value,
    target_platform: targetInstance?.platform || route?.target_platform || null,
    target_chat_id: form.target_chat_id.value.trim(),
    target_chat_canonical: route?.target_chat_canonical || null,
    policy_enabled: form.policy_enabled.value === 'true',
    enabled: form.policy_enabled.value === 'true',
    has_policy: form.policy_enabled.value === 'true',
    content_policy: {
      allow_text: form.allow_text.checked,
      allow_images: form.allow_images.checked,
      allow_video: form.allow_video.checked,
      allow_audio: form.allow_audio.checked,
      allow_documents: form.allow_documents.checked,
      allow_reposts: form.allow_reposts.checked,
      max_images: form.max_images.value === '' ? null : Number(form.max_images.value),
      max_video_size_mb: route?.content_policy?.max_video_size_mb ?? null,
      max_audio_size_mb: route?.content_policy?.max_audio_size_mb ?? null,
      drop_unsupported_media: form.drop_unsupported_media.checked,
    },
    repost_mode: form.repost_mode.value,
    copy_text_template: form.copy_text_template.value.trim() || null,
  };
}

export function validateRouteForm(form) {
  const errors = [];
  if (!form.source_adapter_id.value) errors.push({ field: 'source_adapter_id', message: 'Source adapter is required' });
  if (!form.target_adapter_id.value) errors.push({ field: 'target_adapter_id', message: 'Target adapter is required' });
  if (!form.source_chat_id.value.trim()) errors.push({ field: 'source_chat_id', message: 'Source chat is required' });
  if (!form.target_chat_id.value.trim()) errors.push({ field: 'target_chat_id', message: 'Target chat is required' });
  return { valid: errors.length === 0, errors };
}
