"""Local preview and Telegram relay. Run: python3 server.py"""
import datetime as dt
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.request

ROOT = Path(__file__).resolve().parent
# Read a local .env without external dependencies. Existing environment wins.
def load_env():
    env_file = ROOT / '.env'
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'PORT'):
            os.environ.setdefault(key, value)


load_env()
PORT = int(os.environ.get('PORT', '8017'))


def credentials():
    return os.environ.get('TELEGRAM_BOT_TOKEN', ''), os.environ.get('TELEGRAM_CHAT_ID', '')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split('?')[0] not in ('/', '/index.html'):
            self.respond(404, {'ok': False})
            return
        body = (ROOT / 'index.html').read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != '/api/invite':
            self.respond(404, {'ok': False})
            return
        if self.headers.get('Origin') not in (f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}'):
            self.respond(403, {'ok': False, 'message': 'Открой приглашение через локальный сервер.'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 2048 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError()
            data = json.loads(self.rfile.read(size))
            date = dt.date.fromisoformat(data['date'])
            time = dt.time.fromisoformat(data['time'])
            instant = dt.datetime.fromisoformat(data['instant'].replace('Z', '+00:00'))
            if instant.tzinfo is None or instant <= dt.datetime.now(dt.timezone.utc) or instant > dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=14):
                raise ValueError()
            timezone = str(data.get('timezone', ''))[:80].replace('\n', ' ')
        except (ValueError, KeyError, TypeError):
            self.respond(400, {'ok': False, 'message': 'Выбери будущее время в ближайшие 14 дней ♡'})
            return
        token, chat_id = credentials()
        if not token or not chat_id:
            self.respond(503, {'ok': False, 'message': 'Отправка не настроена. Укажи TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID на сервере.'})
            return
        text = f'Она согласилась на прогулку ❤️\nДата: {date:%d.%m.%Y}\nВремя: {time:%H:%M}\nЧасовой пояс посетителя: {timezone}'
        request = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=json.dumps({'chat_id': chat_id, 'text': text}, ensure_ascii=False).encode(),
            headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                result = json.load(response)
            if result.get('ok') is not True:
                raise ValueError()
        except Exception:
            self.respond(502, {'ok': False, 'message': 'Не удалось подтвердить отправку. Проверь сообщения в Telegram перед повторной попыткой.'})
            return
        self.respond(200, {'ok': True})


if __name__ == '__main__':
    print(f'Приглашение: http://127.0.0.1:{PORT}/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
