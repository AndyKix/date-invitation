module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ ok: false });
  }
  try {
    const origin = new URL(req.headers.origin);
    if (origin.protocol !== 'https:' || origin.host !== req.headers.host) throw new Error();
  } catch {
    return res.status(403).json({ ok: false, message: 'Открой приглашение по ссылке сайта.' });
  }
  const { date, time, instant, timezone } = req.body || {};
  const chosen = new Date(instant);
  if (typeof date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
      typeof time !== 'string' || !/^([01]\d|2[0-3]):[0-5]\d$/.test(time) ||
      typeof instant !== 'string' || !Number.isFinite(chosen.getTime()) || chosen <= new Date() || chosen.getTime() > Date.now() + 14 * 24 * 60 * 60 * 1000 ||
      typeof timezone !== 'string' || timezone.length > 80 || /[\r\n]/.test(timezone)) {
    return res.status(400).json({ ok: false, message: 'Выбери будущее время в ближайшие 14 дней ♡' });
  }
  try {
    const parts = new Intl.DateTimeFormat('en-GB', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(chosen);
    const fields = Object.fromEntries(parts.map(p => [p.type, p.value]));
    if (`${fields.year}-${fields.month}-${fields.day}` !== date || `${fields.hour}:${fields.minute}` !== time) throw new Error();
  } catch {
    return res.status(400).json({ ok: false, message: 'Проверь выбранные дату и время ♡' });
  }
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) return res.status(503).json({ ok: false, message: 'Отправка временно недоступна.' });
  try {
    const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text: `Она согласилась на прогулку ❤️\nДата: ${date.split('-').reverse().join('.')}\nВремя: ${time}\nЧасовой пояс посетителя: ${timezone}` }),
      signal: AbortSignal.timeout(15000)
    });
    const result = await response.json();
    if (!response.ok || result.ok !== true) throw new Error();
    return res.status(200).json({ ok: true });
  } catch {
    return res.status(502).json({ ok: false, message: 'Не удалось подтвердить отправку. Проверь сообщения в Telegram перед повторной попыткой.' });
  }
};
