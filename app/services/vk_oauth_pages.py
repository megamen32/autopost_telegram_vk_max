from __future__ import annotations

from html import escape

from fastapi.responses import HTMLResponse


def build_vk_auth_success_page(
    *,
    title: str,
    message: str,
    message_type: str,
    instance_id: str,
) -> HTMLResponse:
    return HTMLResponse(
        f"""
<!doctype html><html><head><meta charset='utf-8'><title>VK connected</title></head>
<body style="font-family:system-ui,sans-serif;padding:24px;background:#0f172a;color:#e2e8f0">
<h2>{escape(title)}</h2>
<p>{escape(message)}</p>
<script>
if (window.opener) {{ try {{ window.opener.postMessage({{type:'{message_type}', instance_id:'{escape(instance_id)}'}}, '*'); window.close?.(); }} catch (e) {{}} }}
</script>
</body></html>
"""
    )


def build_vk_implicit_callback_page() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html><html><head><meta charset='utf-8'><title>VK OAuth</title></head>
<body style="font-family:system-ui,sans-serif;padding:24px;background:#0f172a;color:#e2e8f0">
<div id="status">Обработка авторизации...</div>
<script>
(function() {
    const statusEl = document.getElementById('status');
    const fragment = window.location.hash.substring(1);
    const query = window.location.search.substring(1);
    const raw = fragment || query;

    if (!raw) {
        statusEl.innerHTML = '<h3>Ошибка</h3><p>Нет данных авторизации в URL</p>';
        return;
    }

    const params = {};
    raw.split('&').forEach(part => {
        const idx = part.indexOf('=');
        const key = idx >= 0 ? part.slice(0, idx) : part;
        const value = idx >= 0 ? part.slice(idx + 1) : '';
        params[key] = decodeURIComponent(value || '');
    });

    if (params.error) {
        statusEl.innerHTML = `<h3>Ошибка авторизации</h3><p>${params.error_description || params.error}</p>`;
        return;
    }

    const tokens = {};
    for (const [key, value] of Object.entries(params)) {
        if (key.startsWith('access_token_') && value) {
            const groupId = key.substring('access_token_'.length);
            tokens[groupId] = value;
        }
    }

    const finish = async () => {
        if (Object.keys(tokens).length > 0) {
            const response = await fetch('/api/auth/vk/groups-finalize', {
                method: 'POST',
                headers: {'content-type': 'application/json'},
                body: JSON.stringify({state: params.state || '', tokens})
            });
            if (!response.ok) {
                throw new Error(await response.text());
            }
            return {
                response: await response.json(),
                messageType: 'vk-groups-auth-success',
                title: 'Группы авторизованы',
                body: `Токены получены для групп: ${Object.keys(tokens).join(', ')}`
            };
        }
        throw new Error('В ответе OAuth не найден group access token. Для пользовательского VK ID входа теперь используется code flow.');
    };

    finish().then((result) => {
        statusEl.innerHTML = `<h3>${result.title}</h3><p>${result.body}</p>`;
        if (window.opener) {
            try {
                window.opener.postMessage({
                    type: result.messageType,
                    instance_id: result.response.instance_id || null,
                    state: params.state || '',
                    tokens: Object.keys(tokens).length > 0 ? tokens : undefined
                }, '*');
                window.close?.();
            } catch (e) {
                console.error(e);
            }
        }
    }).catch((error) => {
        statusEl.innerHTML = `<h3>Ошибка</h3><p>${String(error.message || error)}</p>`;
    });
})();
</script>
</body></html>
"""
    )
