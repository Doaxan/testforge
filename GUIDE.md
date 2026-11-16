# EduForge — гайд: что куда

Практическая инструкция по дашборду и флоу. Скриншоты — в `docs/screenshots/`.

## Запуск

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m playwright install chromium   # для PNG-генераторов
.venv/Scripts/python -m server.main
```

Дашборд: http://127.0.0.1:8895 (порт меняется через `EDUFORGE_PORT`).
Если задан `EDUFORGE_TOKEN` — впиши его в «Настройки», иначе `/api/verify` и `/api/generate` вернут 401.

## Разделы дашборда

| Раздел | Что делает | Скриншот |
|--------|-----------|----------|
| **Запуск** | Главный флоу: вставляешь ссылку SheerID → выбираешь программу/школу/документ → «Запустить». Движок сам генерит документ и проходит шаги API. | `01_run.png` |
| **Очередь** | Все задачи со статусами (queued → generating → submitting → submitted/failed), автообновление 4 с. Клик по задаче не нужен — детали в таблице. | `04_queue.png` |
| **Документы** | Ручная генерация документа без верификации: тип + имя + школа → «Сгенерировать» → превью + «Скачать». | `02_docs.png` |
| **Transcript Studio** | Отдельный модуль транскриптов: 288 школ, 8 макетов, 20 стран. Редактор слева, бумага справа, экспорт PDF. | `05_studio.png`, `06_studio_preview.png` |
| **Программы** | Таблица живых programId (проверены запросом) + список мёртвых. | `03_programs.png` |
| **Настройки** | Admin-токен (хранится в localStorage браузера). | — |

Переключатель RU/EN — внизу сайдбара.

## Главный флоу: откуда взять verificationId

Комбайн НЕ создаёт заявку с нуля — он подхватывает уже открытую заявку SheerID.

1. На сайте вендора (Spotify / YouTube / Perplexity / ChatGPT Teachers и т.д.) запускаешь студенческую верификацию.
2. Вендор открывает виджет SheerID — в адресной строке iframe появляется `verificationId=<24 hex>`.
3. Копируешь либо весь URL, либо сам 24-значный id.
4. Дашборд → **Запуск** → вставляешь → выбираешь программу (должна совпадать с оффером вендора), школу и тип документа → «Запустить».
5. Следишь за статусом в **Очереди**. Финальный статус заявки можно опросить через `GET /api/status/{vid}`.

> Без реального `verificationId` флоу падает на первом шаге с `noVerification` — это нормально, заявка должна быть открыта вендором.

## Что выбирает движок

- **Программа** — `programId` оффера. Живые: `student`, `student_alt`, `student_br`, `teachers`, `veterans`, `generic` (см. «Программы»). Выбирай ту, что соответствует вендору.
- **Школа** — организация в SheerID (сейчас 4 кампуса Penn State). От неё зависят `organization.id/idExtended/name` в заявке и домен email.
- **Документ** — что загрузить:
  - `student_id` — студенческий билет (Pillow, быстро);
  - `transcript` — быстрый транскрипт (Pillow);
  - `teacher_badge` — бейдж учителя (Pillow);
  - `teacher_pdf` / `teacher_png` — сертификат учителя (xhtml2pdf / Playwright);
  - `psu_card` — карта PSU LionPATH (Playwright);
  - для детального транскрипта используй **Transcript Studio** и загружай файл вручную через API.
- **Личность** — имя/фамилия/email/дата рождения. Пусто = сгенерировать автоматически.
- **Прокси** — опционально. Резидентный лучше датацентрового (SheerID режет DC).
- **SSO** — «Пропускать SSO» удаляет шаг SSO (`DELETE /step/sso`), чтобы уйти на загрузку документа.

## Transcript Studio

- **Target school** — выбор школы (поиск по названию).
- **Random transcript** — случайные курсы/оценки; **Auto dates** — даты; **Random ID** — номер студента; **Shuffle school** — другая школа.
- **Layout style** — 8 макетов (classic / banner / split / ivy / uk / ects / asia / latam).
- Вкладка **Preview** — бумага; **Export PDF** — выгрузка.
- Режим `?paper=1` — чистая бумага без редактора (для скриншота/печати).

## API (если без дашборда)

```bash
# сгенерировать документ
curl -X POST http://127.0.0.1:8895/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"doc_type":"student_id","school_id":"2565"}' --output doc.png

# запустить верификацию
curl -X POST http://127.0.0.1:8895/api/verify \
  -H 'Content-Type: application/json' \
  -d '{"vid":"<24hex>","program":"student","doc_type":"student_id"}'

# статус задачи / живой статус заявки
curl http://127.0.0.1:8895/api/task/<task_id>
curl http://127.0.0.1:8895/api/status/<vid>
```

## Гейты вендоров (честно)

Полный перечень офферов (что абузить, что надо, tier-1/2/3, закрытые) — в [docs/OFFERS.md](docs/OFFERS.md).

- **Kiro Students (AWS)** — лучший вход без карты: год бесплатно, 1000 кредитов/мес, Pro-модели. Нужен университетский email из 132 вузов-партнёров + разовая SheerID. `kiro.dev/students` → Verify → снять verificationId → в комбайн.
- **ChatGPT for Teachers** требует школьный email-домен ДО SheerID — без реального K12-домена заявка не откроется, комбайн не поможет.
- **Google AI Pro student** SheerID не требует вообще — там блокер карта/PayPal, не верификация.
- **GitHub Student Pack** — своя проверка GitHub, НЕ SheerID; комбайн даёт только генератор документа.
- **Cursor** закрыл студенческую программу 25.06.2026 из-за фрода.
- Часть programId из старых форков мертва (404) — список в «Программы» → «Мёртвые».

## Структура кода

```
server/main.py          FastAPI-приложение и роуты
server/config.py        программы, школы, эндпоинты, маппинг статусов
server/engine/client.py SheerID API-флоу
server/engine/antidetect.py  TLS-имперсонация, NewRelic, UA, прокси
server/gendocs.py       диспетчер генераторов + синтетическая личность
server/generators/      docgen / teacher / psu / names
server/storage.py       SQLite-очередь
web/index.html          дашборд RU/EN
web/transcript/         Transcript Studio (288 школ)
```