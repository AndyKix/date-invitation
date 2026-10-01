"""Read recent private-chat IDs without saving a token or sending messages."""
import getpass
import json
import urllib.request


def main():
    token = getpass.getpass('Токен нового бота (ввод скрыт): ').strip()
    if not token:
        print('Токен не указан.')
        return
    try:
        request = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/getUpdates',
            data=json.dumps({'limit': 100, 'timeout': 0}).encode(),
            headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)
        if payload.get('ok') is not True:
            raise ValueError()
    except Exception:
        # Do not print exception URLs: they contain the token.
        print('Не удалось получить сообщения. Проверь токен, сеть и отсутствие webhook у бота.')
        return
    chats = {str(chat['id']) for update in payload.get('result', [])
             if (chat := update.get('message', {}).get('chat', {})).get('type') == 'private'}
    if not chats:
        print('Личные чаты не найдены. Нажми Старт у нового бота, отправь сообщение и повтори.')
        return
    print('ID личных чатов из последних сообщений:')
    for chat_id in sorted(chats):
        print(chat_id)
    print('Укажи ID своего чата в TELEGRAM_CHAT_ID. Если чатов несколько, используй отдельного нового бота.')


if __name__ == '__main__':
    main()
